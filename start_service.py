import subprocess
import os
import psutil
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()
# --- Configuration ---
REPO_PATH = os.getenv('REPO_PATH')
SCRIPT_TO_RUN = os.getenv('SCRIPT_TO_RUN')  # The file you want to execute
INTERPRETER = os.getenv('INTERPRETER')      # or 'python3'

def kill_existing_process(script_name):
    """Search for and terminate any running instance of the script."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if the process is python and the script name is in the arguments
            if proc.info['cmdline'] and script_name in proc.info['cmdline']:
                print(f"Terminating existing process (PID: {proc.info['pid']})...")
                proc.terminate()
                proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            continue

def update_repo(path, retries=5, delay=15):
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

def start_script(path, script):
    """Launch the script as a background process."""
    script_path = os.path.join(path, script)
    print(f"Starting {script}...")
    # Use Popen so the manager script doesn't block while the target runs
    subprocess.Popen([INTERPRETER, script_path])

if __name__ == "__main__":
    # 1. Kill any old versions running
    kill_existing_process(SCRIPT_TO_RUN)
    
    # 2. Pull the latest code
    if update_repo(REPO_PATH):
        # 3. Start the new version
        start_script(REPO_PATH, SCRIPT_TO_RUN)