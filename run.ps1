# GAIT Project - Run Script (Windows PowerShell)
# This script provides easy commands for managing the Docker development environment

param(
    [Parameter(Position=0)]
    [string]$Command = "",
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Function to print colored output
function Print-Info {
    param([string]$Message)
    Write-Host "ℹ " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Print-Success {
    param([string]$Message)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

# Check if Docker is running
function Test-Docker {
    try {
        docker info | Out-Null
        return $true
    } catch {
        Print-Warning "Docker is not running. Please start Docker Desktop."
        exit 1
    }
}

# Main command handler
switch ($Command.ToLower()) {
    "build" {
        Print-Info "Building Docker containers..."
        Test-Docker
        docker-compose build
        Print-Success "Build complete!"
    }
    
    { $_ -in @("start", "up") } {
        Print-Info "Starting Docker containers..."
        Test-Docker
        docker-compose up -d
        Print-Success "Containers started!"
        Print-Info "Access the container with: .\run.ps1 shell"
    }
    
    { $_ -in @("stop", "down") } {
        Print-Info "Stopping Docker containers..."
        Test-Docker
        docker-compose down
        Print-Success "Containers stopped!"
    }
    
    "restart" {
        Print-Info "Restarting Docker containers..."
        Test-Docker
        docker-compose restart
        Print-Success "Containers restarted!"
    }
    
    { $_ -in @("shell", "bash") } {
        Print-Info "Opening shell in container..."
        Test-Docker
        docker-compose exec python-dev bash
    }
    
    { $_ -in @("ui", "streamlit", "app") } {
        Print-Info "Starting Streamlit UI..."
        Test-Docker
        Print-Success "UI will be available at: http://localhost:8501"
        docker-compose exec -d python-dev streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
        Print-Success "UI started in background. Access it at http://localhost:8501"
    }
    
    "logs" {
        Print-Info "Showing container logs..."
        Test-Docker
        docker-compose logs -f python-dev
    }
    
    "install" {
        if ($Arguments.Count -eq 0) {
            Print-Warning "Usage: .\run.ps1 install <package-name>"
            exit 1
        }
        $packageName = $Arguments[0]
        Print-Info "Installing package: $packageName"
        Test-Docker
        docker-compose exec python-dev pip install $packageName
        Print-Success "Package installed! Don't forget to add it to requirements.txt"
    }
    
    "python" {
        Print-Info "Running Python command..."
        Test-Docker
        docker-compose exec python-dev python $Arguments
    }
    
    "clean" {
        Print-Warning "This will remove all containers and volumes. Continue? (y/N)"
        $response = Read-Host
        if ($response -match "^[yY]([eE][sS])?$") {
            Print-Info "Cleaning up Docker resources..."
            Test-Docker
            docker-compose down -v
            Print-Success "Cleanup complete!"
        } else {
            Print-Info "Cleanup cancelled."
        }
    }
    
    "status" {
        Print-Info "Container status:"
        Test-Docker
        docker-compose ps
    }
    
    default {
        Write-Host "GAIT Project - Run Script"
        Write-Host ""
        Write-Host "Usage: .\run.ps1 <command> [options]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  build          Build Docker containers"
        Write-Host "  start, up      Start containers in background"
        Write-Host "  stop, down     Stop containers"
        Write-Host "  restart        Restart containers"
        Write-Host "  shell, bash    Open interactive shell in container"
        Write-Host "  ui, streamlit  Start Streamlit UI (available at http://localhost:8501)"
        Write-Host "  logs           Show container logs"
        Write-Host "  install <pkg>  Install a Python package in container"
        Write-Host "  python <args>  Run Python command in container"
        Write-Host "  clean          Remove containers and volumes"
        Write-Host "  status         Show container status"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\run.ps1 build          # Build containers"
        Write-Host "  .\run.ps1 start          # Start containers"
        Write-Host "  .\run.ps1 ui             # Start the UI"
        Write-Host "  .\run.ps1 shell          # Open shell"
        Write-Host "  .\run.ps1 python src/app.py  # Run Python script"
    }
}

