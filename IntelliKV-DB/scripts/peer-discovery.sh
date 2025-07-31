#!/bin/bash

# Post-Startup Peer Discovery Script
# Triggers peer discovery across all pods in the distributed database cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if all pods are ready
wait_for_pods_ready() {
    print_info "Waiting for all pods to be ready..."
    
    for i in {1..60}; do
        # Get pod status more reliably
        ready_count=0
        total_count=0
        
        while IFS= read -r line; do
            if [[ $line =~ [0-9]+/[0-9]+ ]]; then
                total_count=$((total_count + 1))
                if [[ $line =~ 1/1 ]]; then
                    ready_count=$((ready_count + 1))
                fi
            fi
        done < <(kubectl get pods -n distributed-db -l app=distributed-database --no-headers 2>/dev/null || echo "")
        
        if [ "$ready_count" -eq "$total_count" ] && [ "$total_count" -gt 0 ]; then
            print_success "All $total_count pods are ready!"
            return 0
        fi
        
        print_info "Waiting for pods to be ready... ($ready_count/$total_count ready) - attempt $i/60"
        sleep 5
    done
    
    print_error "Timeout waiting for pods to be ready"
    return 1
}

# Function to get pod names
get_pod_names() {
    kubectl get pods -n distributed-db -l app=distributed-database -o jsonpath='{.items[*].metadata.name}'
}

# Function to trigger peer discovery on a pod
trigger_peer_discovery() {
    local pod_name=$1
    local target_pod=$2
    
    print_info "Triggering peer discovery on $pod_name to join $target_pod..."
    
    # Get the target pod's address
    local target_address=""
    case $target_pod in
        "distributed-database-0")
            target_address="distributed-database-0.db-headless-service.distributed-db.svc.cluster.local:8080"
            ;;
        "distributed-database-1")
            target_address="distributed-database-1.db-headless-service.distributed-db.svc.cluster.local:8080"
            ;;
        "distributed-database-2")
            target_address="distributed-database-2.db-headless-service.distributed-db.svc.cluster.local:8080"
            ;;
        *)
            print_error "Unknown target pod: $target_pod"
            return 1
            ;;
    esac
    
    # Send join request
    kubectl exec -n distributed-db "$pod_name" -- curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"address\": \"$target_address\"}" \
        "http://localhost:8080/join" || true
    
    print_info "Join request sent from $pod_name to $target_address"
}

# Function to check peer count for a pod
check_peer_count() {
    local pod_name=$1
    local peer_count=$(kubectl exec -n distributed-db "$pod_name" -- curl -s http://localhost:8080/peers | jq length 2>/dev/null || echo "0")
    echo "$peer_count"
}

# Function to display current peer status
show_peer_status() {
    print_header "Current Peer Status"
    
    local pods=($(get_pod_names))
    
    for pod in "${pods[@]}"; do
        local peer_count=$(check_peer_count "$pod")
        local peers=$(kubectl exec -n distributed-db "$pod" -- curl -s http://localhost:8080/peers 2>/dev/null || echo "[]")
        print_info "$pod: $peer_count peers - $peers"
    done
}

# Function to perform peer discovery
perform_peer_discovery() {
    print_header "Performing Peer Discovery"
    
    local pods=("distributed-database-0" "distributed-database-1" "distributed-database-2")
    
    # Show initial status
    print_info "Initial peer status:"
    show_peer_status
    
    # Trigger peer discovery - each pod joins all other pods
    for pod in "${pods[@]}"; do
        for target in "${pods[@]}"; do
            if [ "$pod" != "$target" ]; then
                trigger_peer_discovery "$pod" "$target"
                sleep 2  # Small delay between requests
            fi
        done
    done
    
    # Wait for peer discovery to propagate
    print_info "Waiting for peer discovery to propagate..."
    sleep 10
    
    # Show final status
    print_info "Final peer status:"
    show_peer_status
}

# Function to verify cluster connectivity
verify_cluster_connectivity() {
    print_header "Verifying Cluster Connectivity"
    
    local pods=("distributed-database-0" "distributed-database-1" "distributed-database-2")
    local all_connected=true
    
    for pod in "${pods[@]}"; do
        local peer_count=$(check_peer_count "$pod")
        if [ "$peer_count" -lt 2 ]; then
            print_error "$pod has only $peer_count peers (expected >= 2)"
            all_connected=false
        else
            print_success "$pod has $peer_count peers"
        fi
    done
    
    if [ "$all_connected" = true ]; then
        print_success "All pods are properly connected!"
        return 0
    else
        print_error "Some pods are not properly connected"
        return 1
    fi
}

# Main execution
main() {
    print_header "Post-Startup Peer Discovery"
    
    # Wait for all pods to be ready
    if ! wait_for_pods_ready; then
        exit 1
    fi
    
    # Perform peer discovery
    perform_peer_discovery
    
    # Verify connectivity
    if verify_cluster_connectivity; then
        print_success "Peer discovery completed successfully!"
    else
        print_error "Peer discovery failed - some pods are not connected"
        exit 1
    fi
}

# Run main function
main "$@" 