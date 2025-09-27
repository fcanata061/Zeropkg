# Zeropkg/zeropkg1.0/modules/upgrade.py
import os
import yaml
from core import CONFIG, log
from meta import MetaPackage
from fetch import fetch_source
from build import build_package
from package import install, remove
from hooks import run_hooks


def load_installed_meta(pkg_name: str) -> dict:
    """Carrega manifesto do pacote já instalado."""
    manifest_file = os.path.join(CONFIG["db_dir"], "installed", f"{pkg_name}.yaml")
    if not os.path.exists(manifest_file):
        return None
    with open(manifest_file) as f:
        return yaml.safe_load(f)


def upgrade(meta: MetaPackage, staging_dir: str, sources_dir: str, build_dir: str):
    """
    Fluxo de upgrade:
    - carrega versão instalada
    - compara com nova versão
    - executa hooks pre-upgrade
    - roda ciclo fetch → build → install
    - executa hooks post-upgrade
    """
    installed = load_installed_meta(meta.name)
    if installed:
        old_version = installed["version"]
        if old_version == meta.version:
            log.info(f"{meta.name} já está na versão {meta.version}")
            return
        log.info(f"⬆️ Upgrade {meta.name}: {old_version} → {meta.version}")
    else:
        log.info(f"{meta.name} não estava instalado. Instalando novo.")

    # Hooks pre-upgrade
    run_hooks(meta.data.get("hooks", {}), "pre-upgrade", cwd=build_dir)

    # Fetch source
    source_dir = fetch_source(meta, sources_dir)

    # Build
    pkg_build_dir = build_package(meta, build_dir)

    # Install (vai sobrescrever a versão antiga)
    pkg_file = install(meta, pkg_build_dir, staging_dir)

    # Hooks post-upgrade
    run_hooks(meta.data.get("hooks", {}), "post-upgrade", cwd=build_dir)

    log.success(f"✅ {meta.name} atualizado para {meta.version}")
    return pkg_file
