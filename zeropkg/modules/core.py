# Zeropkg/zeropkg1.0/modules/core.py
import os
import shlex
import subprocess
import json
from typing import Dict, Any

# Config defaults — ajuste em runtime ou carregue de arquivo
CONFIG: Dict[str, Any] = {
    "repo_base": "/usr/ports/zeropkg",
    "db_dir": os.path.expanduser("~/zeropkg-db"),
    "build_dir": os.path.expanduser("~/zeropkg-build"),
    "staging_dir": os.path.expanduser("~/zeropkg-staging"),
    "packages_dir": os.path.expanduser("~/zeropkg-packages"),
    "install_dir": os.path.expanduser("~/zeropkg-prefix"),
    "hooks_dir": os.path.expanduser("~/zeropkg-hooks"),
    "sandbox": {"backend": "proot"},  # bubblewrap/proot/chroot/docker
    "notify_cmd": "notify-send",
    "http_timeout": 10,
    "user_agent": "zeropkg-updater/1.0",
    "jobs": 1,
}

# Simple logger
class _Logger:
    def info(self, *a): print("[INFO]", *a)
    def warn(self, *a): print("[WARN]", *a)
    def warning(self, *a): print("[WARN]", *a)
    def error(self, *a): print("[ERROR]", *a)
    def debug(self, *a): print("[DEBUG]", *a)
    def success(self, *a): print("[OK]", *a)

log = _Logger()

def run_cmd(cmd: str, cwd: str = None, check: bool = True, env: dict = None):
    """Run shell command, raise subprocess.CalledProcessError on failure if check."""
    log.debug(f"CMD: {cmd} (cwd={cwd})")
    process = subprocess.run(cmd, shell=True, cwd=cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        log.error(process.stderr.strip())
        if check:
            raise subprocess.CalledProcessError(process.returncode, cmd, output=process.stdout, stderr=process.stderr)
    else:
        log.debug(process.stdout.strip())
    return process
