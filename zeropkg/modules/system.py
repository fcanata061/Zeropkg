# Zeropkg - system.py
# Evoluído com glsa_check

import os
import yaml
import requests
from core import CONFIG, log


def list_installed():
    """Lista pacotes instalados no db/installed"""
    db_dir = CONFIG.get("db_dir", "db")
    installed_dir = os.path.join(db_dir, "installed")
    if not os.path.isdir(installed_dir):
        log.warn("Nenhum pacote instalado.")
        return []
    pkgs = [p.replace(".yaml", "") for p in os.listdir(installed_dir) if p.endswith(".yaml")]
    for p in pkgs:
        print(p)
    return pkgs


def glsa_check():
    """
    Verifica boletins de segurança (GLSA-like).
    - Busca advisories de CONFIG['glsa_url'] (HTTP) ou db/glsa.yaml local.
    - Compara pacotes instalados com os afetados.
    - Retorna lista de vulnerabilidades encontradas.
    """
    glsa_url = CONFIG.get("glsa_url")
    db_dir = CONFIG.get("db_dir", "db")
    local_file = os.path.join(db_dir, "glsa.yaml")

    advisories = []
    if glsa_url:
        try:
            log.info(f"🔎 Baixando advisories de {glsa_url}")
            r = requests.get(glsa_url, timeout=10)
            r.raise_for_status()
            advisories = yaml.safe_load(r.text) or []
            os.makedirs(db_dir, exist_ok=True)
            with open(local_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(advisories, f)
        except Exception as e:
            log.warn(f"⚠️ Falha ao baixar advisories: {e}")
    elif os.path.exists(local_file):
        advisories = yaml.safe_load(open(local_file)) or []

    vulns = []
    installed_dir = os.path.join(db_dir, "installed")
    for adv in advisories:
        affected = adv.get("affected", [])
        for pkg in affected:
            pkg_file = os.path.join(installed_dir, f"{pkg}.yaml")
            if os.path.exists(pkg_file):
                vulns.append({
                    "package": pkg,
                    "glsa": adv.get("id"),
                    "severity": adv.get("severity", "unknown"),
                    "description": adv.get("description")
                })

    if vulns:
        log.warn(f"⚠️ {len(vulns)} vulnerabilidades detectadas!")
    else:
        log.success("✅ Nenhuma vulnerabilidade encontrada")

    return vulns
