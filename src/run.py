import subprocess
import sys
import platform
from pathlib import Path

def main():
    app_path = Path("src/app.py").resolve()
    current_os = platform.system().lower()
    if current_os == "windows":
        cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    else:
        cmd = ["streamlit", "run", str(app_path)]
    print(f"Running Streamlit on {current_os} using:")
    print(" ".join(cmd))
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
