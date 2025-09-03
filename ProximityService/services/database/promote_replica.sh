#!/bin/bash
set -e

REPLICA_CONTAINER=$1
if [ -z "$REPLICA_CONTAINER" ]; then
    echo "Usage: $0 <replica_container_name>"
    exit 1
fi

echo "Promoting replica $REPLICA_CONTAINER to primary..."

# Stop the replica
docker-compose stop $REPLICA_CONTAINER

# Execute promotion command inside the container
docker-compose exec $REPLICA_CONTAINER pg_promote -D /var/lib/postgresql/data || \
docker exec $REPLICA_CONTAINER pg_promote -D /var/lib/postgresql/data || \
docker exec $REPLICA_CONTAINER pg_ctl promote -D /var/lib/postgresql/data

# Remove standby.signal to make it a primary
docker exec $REPLICA_CONTAINER rm -f /var/lib/postgresql/data/standby.signal

# Start the promoted primary
docker-compose start $REPLICA_CONTAINER

echo "Replica $REPLICA_CONTAINER promoted to primary successfully!"