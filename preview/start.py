"""
TwitterYoldas — Preview Server Bootstrap
Preview tool tarafindan baslatiliginda bu script server.py'yi calistirir.
"""
import os, sys, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
root = HERE.parent

# Mutlak yol ile server.py'yi calistir
server = HERE / "server.py"
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'

args = [sys.executable, str(server)] + sys.argv[1:]
proc = subprocess.run(args, env=env, cwd=str(root))
sys.exit(proc.returncode)
