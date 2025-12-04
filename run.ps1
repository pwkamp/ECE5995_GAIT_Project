# GAIT Project - Run Script (Windows PowerShell)
# Simple Docker management helper

param(
    [Parameter(Position=0)]
    [string]$Command = "",
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

function Test-Docker {
    try {
        docker info | Out-Null
        return $true
    } catch {
        Write-Host "WARNING: Docker is not running. Please start Docker Desktop."
        exit 1
    }
}

switch ($Command.ToLower()) {

    "build" {
        Write-Host "Building Docker containers..."
        Test-Docker
        docker-compose build
        Write-Host "Build complete."
    }

    "start" {
        Write-Host "Starting Docker containers..."
        Test-Docker
        docker-compose up -d
        Write-Host "Containers started."
        Write-Host "Access the container with: .\run.ps1 shell"
    }

    "up" {
        Write-Host "Starting Docker containers..."
        Test-Docker
        docker-compose up -d
        Write-Host "Containers started."
        Write-Host "Access the container with: .\run.ps1 shell"
    }

    "stop" {
        Write-Host "Stopping Docker containers..."
        Test-Docker
        docker-compose down
        Write-Host "Containers stopped."
    }

    "down" {
        Write-Host "Stopping Docker containers..."
        Test-Docker
        docker-compose down
        Write-Host "Containers stopped."
    }

    "restart" {
        Write-Host "Restarting Docker containers..."
        Test-Docker
        docker-compose restart
        Write-Host "Containers restarted."
    }

    "shell" {
        Write-Host "Opening shell in container..."
        Test-Docker
        docker-compose exec python-dev bash
    }

    "bash" {
        Write-Host "Opening shell in container..."
        Test-Docker
        docker-compose exec python-dev bash
    }

    "ui" {
        Write-Host "Starting Streamlit UI..."
        Test-Docker
        Write-Host "UI will be available at: http://localhost:8501"
        docker-compose exec -d python-dev streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
        Write-Host "UI started in background. Access it at http://localhost:8501"
    }

    "streamlit" {
        Write-Host "Starting Streamlit UI..."
        Test-Docker
        Write-Host "UI will be available at: http://localhost:8501"
        docker-compose exec -d python-dev streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
        Write-Host "UI started in background. Access it at http://localhost:8501"
    }

    "app" {
        Write-Host "Starting Streamlit UI..."
        Test-Docker
        Write-Host "UI will be available at: http://localhost:8501"
        docker-compose exec -d python-dev streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
        Write-Host "UI started in background. Access it at http://localhost:8501"
    }

    "logs" {
        Write-Host "Showing container logs..."
        Test-Docker
        docker-compose logs -f python-dev
    }

    "install" {
        if ($Arguments.Count -eq 0) {
            Write-Host "Usage: .\run.ps1 install PACKAGE_NAME"
            exit 1
        }
        $packageName = $Arguments[0]
        Write-Host "Installing package: $packageName"
        Test-Docker
        docker-compose exec python-dev pip install $packageName
        Write-Host "Package installed. Remember to add it to requirements.txt."
    }

    "python" {
        Write-Host "Running Python command in container..."
        Test-Docker
        docker-compose exec python-dev python $Arguments
    }

    "clean" {
        Write-Host "This will remove all containers and volumes. Continue? (y/N)"
        $response = Read-Host
        if ($response -match "^[yY]([eE][sS])?$") {
            Write-Host "Cleaning up Docker resources..."
            Test-Docker
            docker-compose down -v
            Write-Host "Cleanup complete."
        } else {
            Write-Host "Cleanup cancelled."
        }
    }

    "status" {
        Write-Host "Container status:"
        Test-Docker
        docker-compose ps
    }

    default {
        Write-Host "GAIT Project - Run Script"
        Write-Host ""
        Write-Host "Usage: .\run.ps1 COMMAND [options]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  build            Build Docker containers"
        Write-Host "  start, up        Start containers in background"
        Write-Host "  stop, down       Stop containers"
        Write-Host "  restart          Restart containers"
        Write-Host "  shell, bash      Open interactive shell in container"
        Write-Host "  ui, streamlit    Start Streamlit UI (http://localhost:8501)"
        Write-Host "  logs             Show container logs"
        Write-Host "  install NAME     Install a Python package in container"
        Write-Host "  python ARGS      Run Python command in container"
        Write-Host "  clean            Remove containers and volumes"
        Write-Host "  status           Show container status"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\run.ps1 build"
        Write-Host "  .\run.ps1 start"
        Write-Host "  .\run.ps1 ui"
        Write-Host "  .\run.ps1 shell"
        Write-Host "  .\run.ps1 python src/app.py"
    }
}
