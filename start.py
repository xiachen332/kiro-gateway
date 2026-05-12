import subprocess
import sys

subprocess.run([sys.executable, "main.py", "--workers", "4"] + sys.argv[1:])
