# Zeropkg/zeropkg1.0/modules/sandbox.py
import os
import subprocess
from core import CONFIG, log


def _build_command(cmd: str, cwd: str) -> list:
    """Constrói comando final baseado no backend do sandbox."""
    backend = CONFIG.get("sandbox", {}).get("backend", "proot")

    if backend == "bubblewrap":
        return [
            "bwrap",
            "--unshare-all",
            "--ro-bind", "/", "/",
            "--tmpfs", "/tmp",
            "--dev", "/dev",
            "--proc", "/proc",
            "--chdir", cwd,
            "sh", "-c", cmd
        ]

    elif backend == "proot":
        return [
            "proot",
            "-R", "/",  # rootfs falso (pode ser ajustado futuramente)
            "-w", cwd,
            "sh", "-c", cmd
        ]

    elif backend == "chroot":
        rootfs = CONFIG.get("sandbox", {}).get("rootfs")
        if not rootfs or not os.path.exists(rootfs):
            raise RuntimeError("Rootfs para chroot não configurado ou não existe")
        return ["chroot", rootfs, "sh", "-c", cmd]

    elif backend == "docker":
        image = CONFIG.get("sandbox", {}).get("image", "debian:stable-slim")
        return ["docker", "run", "--rm", "-v", f"{cwd}:/workspace", "-w", "/workspace", image, "sh", "-c", cmd]

    else:
        raise ValueError(f"Backend de sandbox não suportado: {backend}")


def run_in_sandbox(cmd: str, cwd: str = None, check: bool = True):
    """
    Executa um comando dentro do sandbox configurado.
    """
    cwd = cwd or os.getcwd()
    final_cmd = _build_command(cmd, cwd)

    log.debug(f"[SANDBOX] {final_cmd}")
    proc = subprocess.run(final_cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        log.error(f"Erro no sandbox: {proc.stderr.strip()}")
        if check:
            raise RuntimeError(f"Falha no comando em sandbox: {cmd}")
    else:
        log.debug(proc.stdout.strip())

    return proc
