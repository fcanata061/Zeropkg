# Zeropkg/zeropkg1.0/modules/system.py
import os
import shutil
import subprocess
from datetime import datetime

from core import CONFIG, log
from package import load_pkgdb


# ========================
# Auditoria
# ========================

def list_installed():
    """Lista pacotes instalados."""
    db = load_pkgdb()
    if not db:
        log.info("Nenhum pacote instalado.")
        return
    log.info("Pacotes instalados:")
    for name, meta in db.items():
        log.info(f" - {name} ({meta['path']})")


def audit_system():
    """
    Auditoria básica:
      - lista pacotes
      - simula verificação de vulnerabilidades
    """
    db = load_pkgdb()
    if not db:
        log.info("Nenhum pacote para auditar.")
        return

    log.info("=== Auditoria de sistema ===")
    for name in db.keys():
        log.info(f"[OK] {name} instalado.")
        # (futuro: integrar com CVE/GLSA)
    log.info("Auditoria concluída.")


# ========================
# Notificações
# ========================

def notify(title: str, message: str):
    """
    Notificação simples no terminal e opcionalmente via notify-send.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[NOTIFY {timestamp}] {title}: {message}")

    # Tenta usar notify-send (Linux)
    if shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", title, message])
        except Exception as e:
            log.debug(f"notify-send falhou: {e}")
