# Zeropkg/zeropkg1.0/modules/upgrade.py
import os
from core import log, CONFIG
from meta import load_meta
from fetch import fetch_sources
from build import build_package
from package import install_package


def upgrade_package(meta_file: str):
    """
    Atualiza um pacote baseado no seu meta.yaml.
    - Baixa fontes novamente
    - Recompila
    - Reinstala
    """
    log.info(f"⏫ Upgrade iniciado para {meta_file}")

    # 1. Carrega metadados
    meta = load_meta(meta_file)
    pkg_name = meta.name
    pkg_version = meta.version
    log.info(f"Atualizando pacote: {pkg_name} -> {pkg_version}")

    # 2. Baixa fontes
    fetch_dir = CONFIG["fetch_dir"]
    fetch_sources(meta, fetch_dir)

    # 3. Compila
    build_dir = CONFIG["build_dir"]
    build_package(meta, build_dir)

    # 4. Instala
    install_dir = CONFIG["install_dir"]
    install_package(meta, install_dir)

    log.success(f"✅ Pacote {pkg_name} atualizado para versão {pkg_version}")


def upgrade_all(meta_files: list):
    """
    Atualiza todos os pacotes listados em meta_files.
    """
    for mf in meta_files:
        try:
            upgrade_package(mf)
        except Exception as e:
            log.error(f"Falha ao atualizar {mf}: {e}")
