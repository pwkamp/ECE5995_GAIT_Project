./run.sh shell#!/bin/bash

# GAIT Project - Run Script
# This script provides easy commands for managing the Docker development environment

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_warning "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Main command handler
case "${1:-}" in
    build)
        print_info "Building Docker containers..."
        check_docker
        print_info "Resetting cached python packages volume..."
        docker-compose down -v --remove-orphans >/dev/null 2>&1 || true
        docker-compose build
        print_success "Build complete!"
        ;;
    
    start|up)
        print_info "Starting Docker containers..."
        check_docker
        docker-compose up -d
        print_success "Containers started!"
        print_info "Access the container with: ./run.sh shell"
        ;;
    
    stop|down)
        print_info "Stopping Docker containers..."
        check_docker
        docker-compose down
        print_success "Containers stopped!"
        ;;
    
    restart)
        print_info "Restarting Docker containers..."
        check_docker
        docker-compose restart
        print_success "Containers restarted!"
        ;;
    
    shell|bash)
        print_info "Opening shell in container..."
        check_docker
        docker-compose exec python-dev bash
        ;;
    
    ui|streamlit|app)
        print_info "Starting Streamlit UI..."
        check_docker
        # Ensure service is running before exec
        docker-compose up -d python-dev >/dev/null
        print_success "UI will be available at: http://localhost:8501"
        docker-compose exec -d python-dev streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
        print_success "UI started in background. Access it at http://localhost:8501"
        ;;
    
    logs)
        print_info "Showing container logs..."
        check_docker
        docker-compose logs -f python-dev
        ;;
    
    install)
        if [ -z "${2:-}" ]; then
            print_warning "Usage: ./run.sh install <package-name>"
            exit 1
        fi
        print_info "Installing package: $2"
        check_docker
        docker-compose exec python-dev pip install "$2"
        print_success "Package installed! Don't forget to add it to requirements.txt"
        ;;
    
    python)
        shift
        print_info "Running Python command..."
        check_docker
        docker-compose exec python-dev python "$@"
        ;;
    
    clean)
        print_warning "This will remove all containers and volumes. Continue? (y/N)"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            print_info "Cleaning up Docker resources..."
            check_docker
            docker-compose down -v
            print_success "Cleanup complete!"
        else
            print_info "Cleanup cancelled."
        fi
        ;;
    
    status)
        print_info "Container status:"
        check_docker
        docker-compose ps
        ;;
    
    *)
        echo "GAIT Project - Run Script"
        echo ""
        echo "Usage: ./run.sh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  build          Build Docker containers"
        echo "  start, up      Start containers in background"
        echo "  stop, down     Stop containers"
        echo "  restart        Restart containers"
        echo "  shell, bash    Open interactive shell in container"
        echo "  ui, streamlit  Start Streamlit UI (available at http://localhost:8501)"
        echo "  logs           Show container logs"
        echo "  install <pkg>  Install a Python package in container"
        echo "  python <args>  Run Python command in container"
        echo "  clean          Remove containers and volumes"
        echo "  status         Show container status"
        echo ""
        echo "Examples:"
        echo "  ./run.sh build          # Build containers"
        echo "  ./run.sh start          # Start containers"
        echo "  ./run.sh ui             # Start the UI"
        echo "  ./run.sh shell          # Open shell"
        echo "  ./run.sh python src/app.py  # Run Python script"
        ;;
esac
