#!/bin/bash

# Usage: ./node-control.sh start <node-id> | stop <node-id>
# Example: ./node-control.sh start db-node-2

CONFIG_FILE="yaml/config-local.yaml"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: $CONFIG_FILE not found"
    exit 1
fi

get_node_info() {
    local node_id=$1
    local field=$2
    python3 -c "
import yaml
with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)
for node in config['cluster']['seed_nodes']:
    if node['id'] == '$node_id':
        print(node['$field'])
        break
"
}

ACTION=$1
NODE_ID=$2

if [[ -z "$ACTION" || -z "$NODE_ID" ]]; then
    echo "Usage: $0 start|stop <node-id>"
    exit 1
fi

HOST=$(get_node_info "$NODE_ID" "host")
PORT=$(get_node_info "$NODE_ID" "db_port")

if [[ "$ACTION" == "start" ]]; then
    echo "Starting $NODE_ID on $HOST:$PORT ..."
    CONFIG_FILE=$CONFIG_FILE SEED_NODE_ID=$NODE_ID python distributed/node.py > ${NODE_ID}.log 2>&1 &
    PID=$!
    echo "$NODE_ID started with PID $PID"
    echo $PID > ${NODE_ID}.pid
    exit 0
fi

if [[ "$ACTION" == "stop" ]]; then
    if [[ -f "${NODE_ID}.pid" ]]; then
        PID=$(cat ${NODE_ID}.pid)
        echo "Stopping $NODE_ID (PID $PID) ..."
        kill $PID 2>/dev/null || true
        rm -f ${NODE_ID}.pid
        echo "$NODE_ID stopped."
    else
        # Fallback: kill by port
        PID=$(lsof -ti :$PORT)
        if [[ ! -z "$PID" ]]; then
            echo "Stopping $NODE_ID by port (PID $PID) ..."
            kill $PID 2>/dev/null || true
            echo "$NODE_ID stopped."
        else
            echo "No running process found for $NODE_ID on port $PORT."
        fi
    fi
    exit 0
fi

echo "Unknown action: $ACTION"
exit 1 