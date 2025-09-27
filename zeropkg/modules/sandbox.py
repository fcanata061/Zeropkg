# Zeropkg/zeropkg1.0/modules/sandbox.py
import os, shutil, subprocess
from core import CONFIG, log

def _cmd_for_backend(cmd: str, cwd: str):
    backend = CONFIG.get("sandbox",{}).get("backend","proot")
    if backend == "bubblewrap":
        return ["bwrap","--unshare-all","--proc","/proc","--dev","/dev","--tmpfs","/tmp","--ro-bind","/","/","sh","-c", cmd]
    if backend == "docker":
        image = CONFIG.get("sandbox",{}).get("image","debian:stable-slim")
        return ["docker","run","--rm","-v",f"{cwd}:/workspace","-w","/workspace", image, "sh","-c", cmd]
    if backend == "chroot":
        rootfs = CONFIG.get("sandbox",{}).get("rootfs")
        if not rootfs:
            raise RuntimeError("chroot rootfs not configured")
        return ["chroot", rootfs, "sh","-c", cmd]
    # default proot
    return ["proot","-w",cwd,"sh","-c",cmd]

def run_in_sandbox(cmd: str, cwd: str=None, check: bool=True):
    cwd = cwd or os.getcwd()
    final = _cmd_for_backend(cmd, cwd)
    log.debug("[SANDBOX] " + " ".join(final))
    proc = subprocess.run(final, capture_output=True, text=True)
    if proc.returncode != 0:
        log.error(proc.stderr.strip())
        if check:
            raise RuntimeError(f"Sandbox command failed: {cmd}")
    else:
        log.debug(proc.stdout.strip())
    return proc
