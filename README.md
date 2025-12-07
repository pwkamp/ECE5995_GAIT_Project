# GAIT Project

Docker-based development environment for the GAIT Streamlit application. Use the provided run scripts for all common tasks; they wrap `docker-compose` so you do not have to call it directly.

## Prerequisites

- Docker Desktop (includes Docker Compose)
- An `OPENAI_API_KEY` and `OPENAI_MODEL` configured in `src/.streamlit/secrets.toml` (see Secrets section)

## Official way to run (recommended)

Use the helper for your platform:
- macOS/Linux: `./run.sh <command>`
- Windows (PowerShell): `powershell.exe .\run.ps1 <command>`

First-time startup:
```bash
# macOS/Linux
./run.sh build
./run.sh start
./run.sh ui
```
```pwsh
# Windows
powershell.exe .\run.ps1 build
powershell.exe .\run.ps1 start
powershell.exe .\run.ps1 ui
```
The UI will be served at http://localhost:8501.

## Development loop for local changes

- Restart the stack to pick up code changes: `./run.sh restart` or `powershell.exe .\run.ps1 restart`
- Relaunch the UI: `./run.sh ui` or `powershell.exe .\run.ps1 ui`
- If you change dependencies or the Dockerfile, run `build` again before `restart`.

## Command reference

All commands below work with either `./run.sh` or `powershell.exe .\run.ps1`:

- `build` – build the containers.
- `start` or `up` – start containers in the background.
- `down` or `stop` – stop containers and remove them.
- `restart` – restart running containers.
- `ui` / `streamlit` / `app` – start the Streamlit UI on port 8501.
- `shell` / `bash` – open an interactive shell in the container.
- `logs` – follow the app logs.
- `python <args>` – run a Python command in the container.
- `install <package>` – install a Python package inside the container (remember to update `requirements.txt`).
- `status` – show container status.
- `clean` – remove containers and volumes (destructive; prompts for confirmation).
- No command or `help` prints usage details.

## Secrets

Create `src/.streamlit/secrets.toml` (the `.streamlit` folder lives inside `src/`), and add:
```
OPENAI_API_KEY="your-key"
OPENAI_MODEL="gpt-4o-mini"
ELEVENLABS_API_KEY="your-elevenlabs-key"
ELEVENLABS_MUSIC_LENGTH_MS=45000
FAL_KEY="your-fal-key"
```
Adjust the model/length as needed. This file is ignored by git.

## Project structure

```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.ps1
├── run.sh
├── src/
│   ├── app.py
│   ├── app_state.py
│   ├── character_generation_page.py
│   ├── music_generation_page.py
│   ├── run.py
│   ├── script_page.py
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── image_service.py
│   │   └── music_service.py
│   ├── structured_json_page.py
│   ├── ui_helpers.py
│   ├── video_generation_page.py
│   └── .streamlit/secrets.toml
└── README.md
```

## Notes

- Keep `requirements.txt` in sync with installed packages.
- Containers run as the default Docker user; use the helper scripts for consistency across platforms.

## Running without Docker

You can run the Streamlit app directly for quick local testing, but you must manage Python yourself:

1. Ensure Python 3.11+ is installed and create/activate a virtualenv.
2. Install deps: `pip install -r requirements.txt`.
3. Ensure `src/.streamlit/secrets.toml` exists with `OPENAI_API_KEY` and `OPENAI_MODEL`.
4. Launch: `python src/run.py` (wraps `streamlit run src/app.py`).
