import subprocess
import sys
import os

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Start hypercorn with 4 workers
subprocess.run([
    sys.executable, "-m", "hypercorn",
    "main:app",
    "--bind", "0.0.0.0:8000",
    "--workers", "4",
    "--access-logfile", "-",
    "--error-logfile", "-"
])
