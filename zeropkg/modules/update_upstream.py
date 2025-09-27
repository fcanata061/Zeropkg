# Zeropkg/zeropkg1.0/modules/update_upstream.py
import os
import re
import requests
from core import log, CONFIG
from meta import load_meta


def get_latest_version_from_url(url: str) -> str:
    """
    Tenta extrair a versão mais recente de uma página HTML/listagem.
    Exemplo: https://ftp.gnu.org/gnu/wget/
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"Falha ao buscar {url}: {e}")
        return None

    # Regex genérico para capturar versões (ex: 1.2.3, 4.5, 2.0.0-beta)
    versions = re.findall(r'([0-9]+\.[0-9]+(\.[0-9]+)?)', resp.text)
    if not versions:
        return None

    # Pega apenas o número (primeiro grupo da regex)
    versions = [v[0] for v in versions]

    # Ordena numericamente (maior = mais recente)
    versions.sort(key=lambda s: list(map(int, re.findall(r'\d+', s))), reverse=True)

    return versions[0] if versions else None


def check_update(meta_file: str):
    """
    Verifica se existe nova versão para um pacote.
    """
    meta = load_meta(meta_file)
    pkg_name = meta.name
    current_version = meta.version
    homepage = meta.data.get("homepage")

    if not homepage:
        log.warn(f"{pkg_name} não possui 'homepage' em meta.yaml, impossível checar upstream")
        return

    log.info(f"🔍 Checando upstream para {pkg_name} ({homepage})")

    latest = get_latest_version_from_url(homepage)

    if not latest:
        log.warn(f"Não foi possível detectar versão nova para {pkg_name}")
        return

    if latest != current_version:
        log.success(f"📦 {pkg_name}: versão {current_version} → nova versão {latest}")
    else:
        log.info(f"{pkg_name} já está atualizado ({current_version})")


def check_all(meta_files: list):
    """
    Checa updates para todos os pacotes listados.
    """
    for mf in meta_files:
        try:
            check_update(mf)
        except Exception as e:
            log.error(f"Falha ao checar {mf}: {e}")
