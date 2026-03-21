import subprocess
import os
import psutil
import time
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()
# --- Configuration ---
REPO_PATH = os.getenv('REPO_PATH')
SCRIPT_TO_RUN = os.getenv('SCRIPT_TO_RUN')  # The file you want to execute
INTERPRETER = os.getenv('INTERPRETER')      # or 'python3'

def kill_existing_process(script_name):
    """Clean up any old bot instances."""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['cmdline'] and script_name in " ".join(proc.info['cmdline']):
                if proc.info['pid'] != os.getpid():
                    proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def update_repo(path, retries=5, delay=10):
    """Try to pull updates, retrying if DNS/Network isn't ready yet."""
    for i in range(retries):
        print(f"Checking for updates (Attempt {i+1}/{retries})...")
        try:
            # Use the actual path variable here
            subprocess.run(['git', '-C', path, 'pull'], check=True, capture_output=True)
            print("✅ Update successful.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Network not ready or Git error: {e.stderr.decode().strip()}")
            if i < retries - 1:
                print(f"Waiting {delay} seconds to retry...")
                time.sleep(delay)
    print("❌ Failed to update after multiple attempts. Starting bot with local code.")
    return False

def start_bot(path, script):
    """Launch the bot in the background."""
    script_path = os.path.join(path, script)
    print(f"🚀 Launching {script}...")
    # Using Popen so the manager can exit if needed, 
    # but we'll use 'RemainAfterExit=yes' in systemd to keep it clean.
    subprocess.Popen([INTERPRETER, script_path], cwd=path)

if __name__ == "__main__":
    # Ensure we are working with an absolute path string
    path_to_use = str(REPO_PATH)
    
    kill_existing_process(SCRIPT_TO_RUN)
    update_repo(path_to_use)
    start_bot(path_to_use, SCRIPT_TO_RUN)