# Zeropkg/zeropkg1.0/modules/system.py
import os
import json
import requests
from core import CONFIG, log


# ========================
# Pacotes instalados
# ========================

def list_installed():
    """Lista pacotes instalados no diretório de instalação."""
    install_dir = CONFIG.get("install_dir")
    if not install_dir or not os.path.exists(install_dir):
        log.warn("Nenhum diretório de instalação encontrado")
        return []

    pkgs = [p for p in os.listdir(install_dir) if os.path.isdir(os.path.join(install_dir, p))]
    log.info(f"📦 Pacotes instalados: {', '.join(pkgs) if pkgs else 'nenhum'}")
    return pkgs


def verify_integrity(pkg_name: str) -> bool:
    """
    Verifica integridade básica do pacote (placeholder).
    Futuramente: comparar hash de arquivos instalados com manifest.
    """
    pkg_path = os.path.join(CONFIG["install_dir"], pkg_name)
    if not os.path.exists(pkg_path):
        log.error(f"Pacote {pkg_name} não encontrado")
        return False

    # TODO: implementar verificação de manifest
    log.debug(f"Integridade OK (placeholder) para {pkg_name}")
    return True


# ========================
# Auditoria de vulnerabilidades (CVEs)
# ========================

def check_vulnerabilities(pkg_name: str, version: str):
    """
    Consulta vulnerabilidades conhecidas no banco OSV (https://osv.dev/).
    """
    url = "https://api.osv.dev/v1/query"
    payload = {
        "package": {"name": pkg_name},
        "version": version
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"Erro ao consultar OSV para {pkg_name}: {e}")
        return []

    vulns = resp.json().get("vulns", [])
    if not vulns:
        log.success(f"✅ Nenhuma vulnerabilidade conhecida para {pkg_name} {version}")
    else:
        log.warn(f"⚠️ Vulnerabilidades encontradas em {pkg_name} {version}:")
        for v in vulns:
            log.warn(f"- {v.get('id')}: {v.get('summary')}")

    return vulns


# ========================
# Notificações
# ========================

def notify(message: str, level: str = "info"):
    """
    Envia notificação.
    Nível pode ser: info, warn, error, success.
    """
    # Por enquanto: imprime no log
    if level == "info":
        log.info(message)
    elif level == "warn":
        log.warn(message)
    elif level == "error":
        log.error(message)
    elif level == "success":
        log.success(message)

    # Futuro: enviar para webhook/email/etc.


# ========================
# Auditoria geral
# ========================

def audit_all():
    """
    Executa auditoria completa:
    - Lista pacotes
    - Verifica integridade
    - Checa vulnerabilidades
    """
    pkgs = list_installed()
    if not pkgs:
        return

    for pkg in pkgs:
        verify_integrity(pkg)

        # tenta extrair versão do nome do diretório (ex: "foo-1.2.3")
        if "-" in pkg:
            name, version = pkg.rsplit("-", 1)
            check_vulnerabilities(name, version)
        else:
            log.warn(f"Não foi possível determinar versão de {pkg} para checar vulnerabilidades")
