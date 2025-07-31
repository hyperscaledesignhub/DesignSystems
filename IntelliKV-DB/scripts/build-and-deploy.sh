#!/bin/bash

# Build and Deploy Script for Distributed Database
# Cleans Docker resources, builds image, and loads into Kind cluster

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

# Function to clean Docker resources
clean_docker() {
    print_header "Cleaning Docker Resources"
    
    print_info "Stopping all running containers..."
    docker stop $(docker ps -q) 2>/dev/null || true
    
    print_info "Removing all containers..."
    docker rm $(docker ps -aq) 2>/dev/null || true
    
    print_info "Removing all images..."
    docker rmi $(docker images -q) 2>/dev/null || true
    
    print_info "Removing all volumes..."
    docker volume rm $(docker volume ls -q) 2>/dev/null || true
    
    print_info "Removing all networks..."
    docker network rm $(docker network ls -q) 2>/dev/null || true
    
    print_info "Pruning system..."
    docker system prune -af --volumes
    
    print_success "Docker cleanup completed"
}

# Function to build Docker image
build_image() {
    print_header "Building Docker Image"
    
    print_info "Building distributed-database:latest..."
    docker build -t distributed-database:latest .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi
}

# Function to wait for Kind cluster to be ready
wait_for_kind_cluster() {
    print_info "Waiting for Kind cluster to be ready..."
    
    # Wait for the cluster to be ready
    for i in {1..30}; do
        if kubectl cluster-info &>/dev/null; then
            print_success "Kind cluster is ready"
            return 0
        fi
        print_info "Waiting for cluster to be ready... ($i/30)"
        sleep 5
    done
    
    print_error "Kind cluster failed to become ready within timeout"
    return 1
}

# Function to load image into Kind cluster
load_to_kind() {
    print_header "Loading Image to Kind Cluster"
    
    # Check if Kind cluster exists, create if not
    if ! kind get clusters | grep -q "kvdb-cluster"; then
        print_info "Kind cluster 'kvdb-cluster' not found. Creating it..."
        kind create cluster --name kvdb-cluster
        
        if [ $? -eq 0 ]; then
            print_success "Kind cluster created successfully"
            
            # Wait for cluster to be ready
            if ! wait_for_kind_cluster; then
                exit 1
            fi
        else
            print_error "Failed to create Kind cluster"
            exit 1
        fi
    else
        print_info "Kind cluster 'kvdb-cluster' already exists"
        
        # Wait for cluster to be ready
        if ! wait_for_kind_cluster; then
            exit 1
        fi
    fi
    
    print_info "Loading image into Kind cluster..."
    kind load docker-image distributed-database:latest --name kvdb-cluster
    
    if [ $? -eq 0 ]; then
        print_success "Image loaded into Kind cluster successfully"
    else
        print_error "Failed to load image into Kind cluster"
        exit 1
    fi
}

# Function to restart Kubernetes pods
restart_pods() {
    print_header "Restarting Kubernetes Pods"
    
    # Get the script directory to ensure we're using correct paths
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # Check if namespace exists, create resources if not
    if ! kubectl get namespace distributed-db &>/dev/null; then
        print_info "Namespace 'distributed-db' not found. Creating Kubernetes resources..."
        
        print_info "Creating namespace..."
        kubectl apply -f "$PROJECT_ROOT/yaml/k8s-namespace.yaml"
        
        print_info "Creating ConfigMap..."
        kubectl apply -f "$PROJECT_ROOT/yaml/k8s-config-map.yaml"
        
        print_info "Creating Services..."
        kubectl apply -f "$PROJECT_ROOT/yaml/k8s-service.yaml"
        
        print_info "Creating StatefulSet..."
        kubectl apply -f "$PROJECT_ROOT/yaml/k8s-stateful-set.yaml"
        
        print_success "Kubernetes resources created successfully"
    else
        print_info "Namespace 'distributed-db' exists. Deleting existing pods to use new image..."
        kubectl delete pods -n distributed-db --all --force --grace-period=0 2>/dev/null || true
    fi
    
    print_info "Waiting for pods to restart..."
    sleep 10
    
    print_info "Current pod status:"
    kubectl get pods -n distributed-db
    
    print_success "Pods restarted with new image"
}

# Function to show usage
show_usage() {
    echo "Build and Deploy Script for Distributed Database"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  clean-only     Clean Docker resources only"
    echo "  build-only     Build Docker image only"
    echo "  load-only      Load image to Kind cluster only"
    echo "  restart-only   Restart Kubernetes pods only"
    echo "  delete-kind    Delete the Kind cluster (kvdb-cluster)"
    echo "  full           Complete Kind deployment (create cluster + full cycle)"
    echo "  test           Build and deploy test pod"
    echo "  ecr-build      Build and push images to ECR"
    echo "  ecr-test       Build, push to ECR, and test demos"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 full        # Complete Kind deployment"
    echo "  $0 build-only  # Just build the image"
    echo "  $0 delete-kind # Delete the Kind cluster"
    echo "  $0 ecr-build   # Build and push to ECR"
    echo "  $0 ecr-test    # Full ECR build and test cycle"
    echo ""
}

# Function to delete Kind cluster
delete_kind_cluster() {
    print_header "Deleting Kind Cluster"
    if kind get clusters | grep -q "kvdb-cluster"; then
        print_info "Deleting Kind cluster 'kvdb-cluster'..."
        kind delete cluster --name kvdb-cluster
        if [ $? -eq 0 ]; then
            print_success "Kind cluster 'kvdb-cluster' deleted successfully"
        else
            print_error "Failed to delete Kind cluster 'kvdb-cluster'"
            exit 1
        fi
    else
        print_info "Kind cluster 'kvdb-cluster' does not exist. Nothing to delete."
    fi
}

# Build test Docker image
build_test_image() {
    print_header "Building Test Docker Image"
    print_info "Building kvdb-test:latest from Dockerfile.test..."
    docker build -f Dockerfile.test -t kvdb-test:latest .
    if [ $? -eq 0 ]; then
        print_success "Test Docker image built successfully"
    else
        print_error "Test Docker build failed"
        exit 1
    fi
}

# Load test image into Kind
load_test_image_to_kind() {
    print_header "Loading Test Image to Kind Cluster"
    kind load docker-image kvdb-test:latest --name kvdb-cluster
    if [ $? -eq 0 ]; then
        print_success "Test image loaded into Kind cluster successfully"
    else
        print_error "Failed to load test image into Kind cluster"
        exit 1
    fi
}

# Deploy test pod
deploy_test_pod() {
    print_header "Deploying Test Pod"
    
    # Get the script directory to ensure we're using correct paths
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # Delete existing test pod if it exists
    if kubectl get pod kvdb-test-pod -n distributed-db &>/dev/null; then
        print_info "Deleting existing test pod..."
        kubectl delete pod kvdb-test-pod -n distributed-db --force --grace-period=0
        sleep 5
    fi
    
    kubectl apply -f "$PROJECT_ROOT/yaml/test-pod.yaml"
    if [ $? -eq 0 ]; then
        print_success "Test pod deployed successfully"
    else
        print_error "Failed to deploy test pod"
        exit 1
    fi
    
    # Wait for pod to be ready
    print_info "Waiting for test pod to be ready..."
    kubectl wait --for=condition=ready pod/kvdb-test-pod -n distributed-db --timeout=60s
    
    print_info "To exec into the test pod and run demo scripts, use:"
    echo "kubectl exec -it kvdb-test-pod -n distributed-db -- /bin/bash"
    print_info "Example:"
    echo "python cluster_demo_runner.py vector_clock_db --config config.yaml --use-existing"
}

# Build and push images to ECR
build_and_push_ecr() {
    print_header "Building and Pushing Images to ECR"
    
    print_info "Changing to k8s directory..."
    cd k8s
    
    print_info "Running ECR build and push script..."
    ./build-and-push-ecr.sh build
    
    if [ $? -eq 0 ]; then
        print_success "ECR build and push completed successfully"
    else
        print_error "ECR build and push failed"
        exit 1
    fi
    
    # Return to original directory
    cd ..
}

# Redeploy test pod with latest ECR image
redeploy_test_pod_ecr() {
    print_header "Redeploying Test Pod with Latest ECR Image"
    
    print_info "Deleting existing test pod..."
    kubectl delete pod kvdb-test-pod -n distributed-db --force --grace-period=0 2>/dev/null || true
    
    print_info "Waiting for pod deletion..."
    sleep 5
    
    print_info "Deploying test pod with latest ECR image..."
    kubectl apply -f k8s/test-pod.yaml
    
    if [ $? -eq 0 ]; then
        print_success "Test pod deployed successfully"
    else
        print_error "Failed to deploy test pod"
        exit 1
    fi
    
    print_info "Waiting for test pod to be ready..."
    kubectl wait --for=condition=ready pod/kvdb-test-pod -n distributed-db --timeout=60s
    
    if [ $? -eq 0 ]; then
        print_success "Test pod is ready"
    else
        print_error "Test pod failed to become ready"
        exit 1
    fi
}

# Run all demos in test pod
run_all_demos() {
    print_header "Running All Demos in Test Pod"
    
    print_info "Running vector clock demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py vector_clock_db --config demo/config.yaml --use-existing
    
    print_info "Running anti-entropy demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py anti_entropy --config demo/config.yaml --use-existing
    
    print_info "Running consistent hashing demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py consistent_hashing --config demo/config.yaml --use-existing
    
    print_info "Running replication demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py replication --config demo/config.yaml --use-existing
    
    print_info "Running persistence anti-entropy demo..."
    kubectl exec -it kvdb-test-pod -n distributed-db -- python demo/cluster_demo_runner.py persistence_anti_entropy --config demo/config.yaml --use-existing
    
    print_success "All demos completed successfully!"
}

# Main execution
main() {
    case "${1:-full}" in
        "clean-only")
            clean_docker
            ;;
        "build-only")
            build_image
            ;;
        "load-only")
            load_to_kind
            ;;
        "restart-only")
            restart_pods
            ;;
        "delete-kind")
            delete_kind_cluster
            ;;
        "test")
            build_test_image
            load_test_image_to_kind
            deploy_test_pod
            ;;
        "full")
            print_header "Complete Kind Deployment"
            print_info "This will create a Kind cluster and deploy everything from scratch..."
            
            # Delete existing cluster if it exists
            if kind get clusters | grep -q "kvdb-cluster"; then
                print_info "Existing Kind cluster found. Deleting it..."
                kind delete cluster --name kvdb-cluster
            fi
            
            clean_docker
            build_image
            load_to_kind
            restart_pods
            build_test_image
            load_test_image_to_kind
            deploy_test_pod
            
            print_header "Complete Kind Deployment Finished!"
            print_success "Your distributed database is now running in a fresh Kind cluster!"
            print_info "Access points:"
            echo "  - API Service: http://localhost:30080"
            echo "  - Health Check: http://localhost:30080/health"
            echo "  - Cluster Info: http://localhost:30080/info"
            ;;
        "help"|*)
            show_usage
            ;;
    esac
}

# Run main function
main "$@" 