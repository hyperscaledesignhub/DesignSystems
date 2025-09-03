#!/bin/bash
set -e

echo "Setting up PostgreSQL replica server..."

# Wait for primary to be ready
until pg_isready -h $POSTGRES_PRIMARY_HOST -p $POSTGRES_PRIMARY_PORT -U postgres; do
  echo "Waiting for primary database to be ready..."
  sleep 2
done

# Remove existing data directory if it exists
if [ -d "$PGDATA" ] && [ "$(ls -A $PGDATA)" ]; then
    echo "Removing existing data directory..."
    rm -rf $PGDATA/*
fi

# Create base backup from primary
echo "Creating base backup from primary..."
PGPASSWORD=$POSTGRES_REPLICATION_PASSWORD pg_basebackup -h $POSTGRES_PRIMARY_HOST -p $POSTGRES_PRIMARY_PORT -D $PGDATA -U $POSTGRES_REPLICATION_USER -v -P -W

# Create standby.signal to indicate this is a standby server
touch $PGDATA/standby.signal

# Configure recovery settings
cat >> $PGDATA/postgresql.conf <<EOF
primary_conninfo = 'host=$POSTGRES_PRIMARY_HOST port=$POSTGRES_PRIMARY_PORT user=$POSTGRES_REPLICATION_USER password=$POSTGRES_REPLICATION_PASSWORD'
hot_standby = on
EOF

echo "Replica setup completed successfully!"