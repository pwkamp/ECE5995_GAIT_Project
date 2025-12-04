# GAIT Project

A Python development environment with Docker for consistent development across team members.

## Prerequisites

- [Docker](https://www.docker.com/get-started) (Docker Desktop recommended)
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

## Setup

1. **Clone the repository** (once connected to GitHub):
   ```bash
   git clone <your-repo-url>
   cd GAIT_Project
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. **Build and start the Docker container**:
   ```bash
   ./run.sh build
   ./run.sh start
   ```
   Or use docker-compose directly:
   ```bash
   docker-compose up -d --build
   ```

4. **Access the container**:
   ```bash
   ./run.sh shell
   ```
   Or use docker-compose directly:
   ```bash
   docker-compose exec python-dev bash
   ```

## Usage

### Quick Start with Run Script

The `run.sh` script makes common tasks easier:

```bash
./run.sh build          # Build Docker containers
./run.sh start          # Start containers
./run.sh ui             # Start the Streamlit UI (http://localhost:8501)
./run.sh shell          # Open interactive shell
./run.sh status         # Check container status
./run.sh help           # Show all available commands
```

### Running the UI

Start the Streamlit UI (simple placeholder interface):
```bash
./run.sh ui
```

Then open your browser to: **http://localhost:8501**

Or manually:
```bash
docker-compose exec python-dev streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
```

### Running Python scripts

From inside the container:
```bash
python your_script.py
```

Or from your host machine using the run script:
```bash
./run.sh python your_script.py
```

Or using docker-compose directly:
```bash
docker-compose exec python-dev python your_script.py
```

### Installing new packages

1. **Edit `requirements.txt`** and add your package:
   ```
   package-name>=1.0.0
   ```

2. **Rebuild the container**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

   Or install temporarily inside the container:
   ```bash
   docker-compose exec python-dev pip install package-name
   ```

### Using OpenAI API

See `example_openai.py` for a basic example. Your API key will be available as an environment variable:
```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
```

## Development Workflow

- Your code is mounted as a volume, so changes to files are immediately reflected in the container
- The container stays running in the background for quick access
- All team members will have the same Python version and package versions

## Commands

### Using the Run Script (Recommended)

- **Build containers**: `./run.sh build`
- **Start container**: `./run.sh start`
- **Stop container**: `./run.sh stop`
- **View logs**: `./run.sh logs`
- **Access shell**: `./run.sh shell`
- **Start UI**: `./run.sh ui`
- **Run Python**: `./run.sh python <script>`
- **Install package**: `./run.sh install <package-name>`
- **Status check**: `./run.sh status`

### Using Docker Compose Directly

- **Start container**: `docker-compose up -d`
- **Stop container**: `docker-compose down`
- **View logs**: `docker-compose logs -f python-dev`
- **Access shell**: `docker-compose exec python-dev bash`
- **Rebuild**: `docker-compose up -d --build`

## Project Structure

```
GAIT_Project/
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python package dependencies
├── run.sh                  # Convenience script for common tasks
├── .env.example           # Example environment variables
├── .gitignore             # Files to ignore in git
├── .dockerignore          # Files to ignore in Docker build
├── README.md              # This file
├── example_openai.py      # Example script using OpenAI API
└── src/                   # Project source code
    ├── __init__.py        # Package initialization
    └── app.py             # Streamlit UI application
```

## Notes

- Never commit `.env` file to git (it's in `.gitignore`)
- Always update `requirements.txt` when adding new packages
- The container runs as a non-root user for security

