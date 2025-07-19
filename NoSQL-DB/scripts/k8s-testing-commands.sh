#!/bin/bash

# Kubernetes Testing Commands for Distributed Database
# This file contains all the commands needed to test the distributed database in Kubernetes

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

# Function to show usage
show_usage() {
    echo "Kubernetes Testing Commands for Distributed Database"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy              Deploy the full cluster with test pod"
    echo "  deploy-test         Deploy only the test pod (rebuilds image)"
    echo "  status              Show cluster and pod status"
    echo "  logs                Show logs from database pods"
    echo "  test-logs           Show logs from test pod"
    echo "  exec-test           Execute bash in test pod"
    echo "  port-forward        Start port-forward to cluster (port 8081)"
    echo "  stop-port-forward   Stop port-forward"
    echo "  cleanup             Clean up all resources"
    echo "  ecr-build           Build and push images to ECR"
    echo "  ecr-test            Build, push to ECR, redeploy and test demos"
    echo "  help                Show this help message"
    echo ""
    echo "Demo Commands (run inside test pod):"
    echo "  vector-clock        Run vector clock demo"
    echo "  replication         Run replication demo"
    echo "  anti-entropy        Run anti-entropy demo"
    echo "  consistent-hashing  Run consistent hashing demo"
    echo "  persistence         Run persistence with anti-entropy demo"
    echo "  convergence         Run convergence demo"
    echo "  automated-ae        Run automated anti-entropy demo"
    echo ""
    echo "Examples:"
    echo "  $0 deploy           # Deploy everything"
    echo "  $0 status           # Check status"
    echo "  $0 exec-test        # Get into test pod"
    echo "  $0 vector-clock     # Run vector clock demo"
    echo "  $0 ecr-build        # Build and push to ECR"
    echo "  $0 ecr-test         # Full ECR build and test cycle"
    echo "  $0 run-demos        # Run all demos (existing test pod)"
    echo ""
}

# Function to deploy full cluster
deploy_full() {
    print_header "Deploying Full Cluster with Test Pod"
    ./build-and-deploy.sh full
    print_success "Full deployment completed!"
}

# Function to deploy test pod only
deploy_test() {
    print_header "Deploying Test Pod Only"
    ./build-and-deploy.sh test
    print_success "Test pod deployment completed!"
}

# Function to show status
show_status() {
    print_header "Cluster and Pod Status"
    
    echo "=== Namespace Status ==="
    kubectl get namespace distributed-db
    
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods -n distributed-db
    
    echo ""
    echo "=== Service Status ==="
    kubectl get services -n distributed-db
    
    echo ""
    echo "=== StatefulSet Status ==="
    kubectl get statefulset -n distributed-db
    
    echo ""
    echo "=== ConfigMap Status ==="
    kubectl get configmap -n distributed-db
}

# Function to show database logs
show_logs() {
    print_header "Database Pod Logs"
    
    echo "=== distributed-database-0 logs ==="
    kubectl logs -n distributed-db distributed-database-0 --tail=20
    
    echo ""
    echo "=== distributed-database-1 logs ==="
    kubectl logs -n distributed-db distributed-database-1 --tail=20
    
    echo ""
    echo "=== distributed-database-2 logs ==="
    kubectl logs -n distributed-db distributed-database-2 --tail=20
}

# Function to show test pod logs
show_test_logs() {
    print_header "Test Pod Logs"
    kubectl logs -n distributed-db kvdb-test-pod --tail=50
}

# Function to execute bash in test pod
exec_test() {
    print_header "Executing Bash in Test Pod"
    print_info "Use 'exit' to leave the pod"
    kubectl exec -it kvdb-test-pod -n distributed-db -- /bin/bash
}

# Function to start port-forward
start_port_forward() {
    print_header "Starting Port Forward"
    print_info "Forwarding localhost:8081 to cluster port 8080"
    print_info "Press Ctrl+C to stop"
    kubectl port-forward -n distributed-db svc/db-headless-service 8081:8080
}

# Function to stop port-forward
stop_port_forward() {
    print_header "Stopping Port Forward"
    pkill -f "kubectl port-forward" || true
    print_success "Port forward stopped"
}

# Function to cleanup
cleanup() {
    print_header "Cleaning Up Resources"
    
    print_info "Stopping port forward..."
    pkill -f "kubectl port-forward" || true
    
    print_info "Deleting test pod..."
    kubectl delete pod kvdb-test-pod -n distributed-db --force --grace-period=0 2>/dev/null || true
    
    print_info "Deleting database pods..."
    kubectl delete pods -n distributed-db --all --force --grace-period=0 2>/dev/null || true
    
    print_info "Deleting namespace..."
    kubectl delete namespace distributed-db --force --grace-period=0 2>/dev/null || true
    
    print_success "Cleanup completed!"
}

# Demo command functions
run_vector_clock() {
    print_header "Running Vector Clock Demo"
    python /app/demo/cluster_demo_runner.py vector_clock_db --config /app/config/config.yaml --use-existing
}

run_replication() {
    print_header "Running Replication Demo"
    
    print_info "Testing replication with existing Kubernetes cluster..."
    
    # Test 1: Write data to node 0
    print_info "Writing test data to node 0..."
    curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_value"}' http://distributed-database-0.db-headless-service.distributed-db.svc.cluster.local:8080/kv/replication_test_key
    
    # Test 2: Verify data is replicated to all nodes
    print_info "Verifying replication to all nodes..."
    echo "Reading from node 0:"
    curl -s http://distributed-database-0.db-headless-service.distributed-db.svc.cluster.local:8080/kv/replication_test_key | python -c "import sys, json; data=json.load(sys.stdin); print(f'Value: {data[\"value\"]}, Replicas: {data[\"replicas_responded\"]}/{data[\"total_replicas\"]}')"
    
    echo "Reading from node 1:"
    curl -s http://distributed-database-1.db-headless-service.distributed-db.svc.cluster.local:8080/kv/replication_test_key | python -c "import sys, json; data=json.load(sys.stdin); print(f'Value: {data[\"value\"]}, Replicas: {data[\"replicas_responded\"]}/{data[\"total_replicas\"]}')"
    
    echo "Reading from node 2:"
    curl -s http://distributed-database-2.db-headless-service.distributed-db.svc.cluster.local:8080/kv/replication_test_key | python -c "import sys, json; data=json.load(sys.stdin); print(f'Value: {data[\"value\"]}, Replicas: {data[\"replicas_responded\"]}/{data[\"total_replicas\"]}')"
    
    # Test 3: Write from different nodes
    print_info "Testing writes from different nodes..."
    echo "Writing from node 1:"
    curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_from_node1"}' http://distributed-database-1.db-headless-service.distributed-db.svc.cluster.local:8080/kv/replication_test_key2
    
    echo "Writing from node 2:"
    curl -X PUT -H 'Content-Type: application/json' -d '{"value":"replication_test_from_node2"}' http://distributed-database-2.db-headless-service.distributed-db.svc.cluster.local:8080/kv/replication_test_key3
    
    # Test 4: Verify all data is accessible from all nodes
    print_info "Verifying all data is accessible from all nodes..."
    for key in replication_test_key replication_test_key2 replication_test_key3; do
        echo "Testing key: $key"
        for node in 0 1 2; do
            echo "  Node $node:"
            curl -s http://distributed-database-$node.db-headless-service.distributed-db.svc.cluster.local:8080/kv/$key | python -c "import sys, json; data=json.load(sys.stdin); print(f'    Value: {data[\"value\"]}')"
        done
    done
    
    print_success "Replication test completed successfully!"
}

run_anti_entropy() {
    print_header "Running Anti-Entropy Demo"
    python /app/demo/cluster_demo_runner.py anti_entropy --config /app/config/config.yaml --use-existing
}

run_consistent_hashing() {
    print_header "Running Consistent Hashing Demo"
    python /app/demo/cluster_demo_runner.py consistent_hashing --config /app/config/config.yaml --use-existing
}

run_persistence() {
    print_header "Running Persistence with Anti-Entropy Demo"
    python /app/demo/cluster_demo_runner.py persistence_anti_entropy --config /app/config/config.yaml --use-existing
}

run_convergence() {
    print_header "Running Convergence Demo"
    python /app/demo/convergence_test.py
}

run_automated_ae() {
    print_header "Running Automated Anti-Entropy Demo"
    python /app/demo/automated_anti_entropy_demo.py
}

# Function to test cluster connectivity
test_connectivity() {
    print_header "Testing Cluster Connectivity"
    
    print_info "Testing health endpoints..."
    for i in {0..2}; do
        echo "Testing distributed-database-$i..."
        curl -s "http://distributed-database-$i.db-headless-service.distributed-db.svc.cluster.local:8080/health" | head -1
    done
    
    print_info "Testing peer discovery..."
    curl -s "http://distributed-database-0.db-headless-service.distributed-db.svc.cluster.local:8080/peers" | head -5
}

# Function to test Merkle snapshots
test_merkle() {
    print_header "Testing Merkle Snapshots"
    
    print_info "Testing Merkle snapshot endpoint..."
    curl -s "http://distributed-database-0.db-headless-service.distributed-db.svc.cluster.local:8080/merkle/snapshot" | head -3
}

# Function to test anti-entropy trigger
test_anti_entropy() {
    print_header "Testing Anti-Entropy Trigger"
    
    print_info "Triggering anti-entropy on all nodes..."
    for i in {0..2}; do
        echo "Triggering on distributed-database-$i..."
        curl -s -X POST "http://distributed-database-$i.db-headless-service.distributed-db.svc.cluster.local:8080/anti-entropy/trigger" | head -1
    done
}

# Function to build and push images to ECR
ecr_build() {
    print_header "Building and Pushing Images to ECR"
    
    print_info "Changing to k8s directory..."
    cd k8s
    
    print_info "Building and pushing images to ECR..."
    ./build-and-push-ecr.sh build
    
    if [ $? -eq 0 ]; then
        print_success "ECR build and push completed successfully!"
        cd ..
    else
        print_error "ECR build and push failed!"
        cd ..
        exit 1
    fi
}

# Function to build, push to ECR, redeploy and test demos
ecr_test() {
    print_header "Full ECR Build and Test Cycle"
    
    print_info "Step 1: Building and pushing images to ECR..."
    ecr_build
    
    print_info "Step 2: Redeploying test pod with latest image..."
    kubectl delete pod kvdb-test-pod -n distributed-db --force --grace-period=0 2>/dev/null || true
    kubectl apply -f test-pod.yaml
    
    print_info "Step 3: Waiting for test pod to be ready..."
    kubectl wait --for=condition=ready pod/kvdb-test-pod -n distributed-db --timeout=60s
    
    if [ $? -eq 0 ]; then
        print_success "Test pod is ready!"
        
        print_info "Step 4: Running all demos to verify functionality..."
        
        print_info "Running Vector Clock Demo..."
        kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py vector_clock_db --config demo/config.yaml --use-existing
        
        print_info "Running Anti-Entropy Demo..."
        kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py anti_entropy --config demo/config.yaml --use-existing
        
        print_info "Running Consistent Hashing Demo..."
        kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py consistent_hashing --config demo/config.yaml --use-existing
        
        print_info "Running Replication Demo..."
        kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py replication --config demo/config.yaml --use-existing
        
        print_info "Running Persistence Anti-Entropy Demo..."
        kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py persistence_anti_entropy --config demo/config.yaml --use-existing
        
        print_success "All demos completed successfully!"
        print_info "ECR build and test cycle completed successfully!"
    else
        print_error "Test pod failed to become ready!"
        exit 1
    fi
}

# Function to run all demos using existing test pod
run_all_demos() {
    print_header "Running All Demos with Existing Test Pod"
    
    print_info "Checking if test pod exists and is ready..."
    if ! kubectl get pod kvdb-test-pod -n distributed-db &>/dev/null; then
        print_error "Test pod 'kvdb-test-pod' not found in namespace 'distributed-db'"
        print_info "Please deploy the test pod first using: $0 deploy-test"
        exit 1
    fi
    
    if ! kubectl wait --for=condition=ready pod/kvdb-test-pod -n distributed-db --timeout=10s &>/dev/null; then
        print_error "Test pod is not ready"
        print_info "Please check pod status using: $0 status"
        exit 1
    fi
    
    print_success "Test pod is ready! Running all demos..."
    
    print_info "Running Vector Clock Demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py vector_clock_db --config demo/config.yaml --use-existing

    sleep 30
    
    print_info "Running Anti-Entropy Demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py anti_entropy --config demo/config.yaml --use-existing
    
    sleep 30
    
    print_info "Running Consistent Hashing Demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py consistent_hashing --config demo/config.yaml --use-existing
    
    sleep 30

    print_info "Running Replication Demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py replication --config demo/config.yaml --use-existing
    
    sleep 30

    
    print_info "Running Persistence Anti-Entropy Demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py persistence_anti_entropy --config demo/config.yaml --use-existing
    
    print_success "All demos completed successfully!"
    print_info "Demo testing completed!"
}

# Main execution
main() {
    case "${1:-help}" in
        "deploy")
            deploy_full
            ;;
        "deploy-test")
            deploy_test
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "test-logs")
            show_test_logs
            ;;
        "exec-test")
            exec_test
            ;;
        "port-forward")
            start_port_forward
            ;;
        "stop-port-forward")
            stop_port_forward
            ;;
        "cleanup")
            cleanup
            ;;
        "vector-clock")
            run_vector_clock
            ;;
        "replication")
            run_replication
            ;;
        "anti-entropy")
            run_anti_entropy
            ;;
        "consistent-hashing")
            run_consistent_hashing
            ;;
        "persistence")
            run_persistence
            ;;
        "convergence")
            run_convergence
            ;;
        "automated-ae")
            run_automated_ae
            ;;
        "test-connectivity")
            test_connectivity
            ;;
        "test-merkle")
            test_merkle
            ;;
        "test-anti-entropy")
            test_anti_entropy
            ;;
        "ecr-build")
            ecr_build
            ;;
        "ecr-test")
            ecr_test
            ;;
        "run-demos")
            run_all_demos
            ;;
        "help"|*)
            show_usage
            ;;
    esac
}

# Run main function
main "$@" 
