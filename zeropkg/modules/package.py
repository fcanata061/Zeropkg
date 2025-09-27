# Zeropkg - package.py
# Evoluído com create_package, install_package e remove_package com hooks

import os
import tarfile
import subprocess
from core import CONFIG, log
from meta import MetaPackage


def run_hooks(hook_type: str, meta: MetaPackage):
    """Executa hooks pre/post-install/remove se existirem"""
    hooks_dir = CONFIG.get("hooks_dir", "hooks")
    script = os.path.join(hooks_dir, f"{hook_type}-{meta.name}")
    if os.path.exists(script) and os.access(script, os.X_OK):
        try:
            subprocess.run([script, meta.name, meta.version], check=True)
            log.info(f"Hook {hook_type} executado para {meta.name}")
        except subprocess.CalledProcessError as e:
            log.warn(f"Hook {hook_type} falhou: {e}")


def create_package(meta_path: str, build_dir: str, output_dir: str = None) -> str:
    """
    Cria um pacote (tar.xz) a partir de um build instalado em DESTDIR.
    """
    meta = MetaPackage(meta_path)
    output_dir = output_dir or CONFIG.get("packages_dir", "packages")
    os.makedirs(output_dir, exist_ok=True)

    pkgname = f"{meta.name}-{meta.version}.tar.xz"
    pkgpath = os.path.join(output_dir, pkgname)

    with tarfile.open(pkgpath, "w:xz") as tar:
        tar.add(build_dir, arcname="/")

    log.success(f"📦 Pacote criado: {pkgpath}")
    return pkgpath


def install_package(meta: MetaPackage, pkgpath: str, root: str = "/"):
    """
    Instala um pacote (extrai o tar.xz para root).
    """
    run_hooks("pre-install", meta)
    with tarfile.open(pkgpath, "r:xz") as tar:
        tar.extractall(path=root)
    run_hooks("post-install", meta)
    log.success(f"✅ Instalado {meta.name}-{meta.version} em {root}")


def remove_package(meta: MetaPackage, root: str = "/"):
    """
    Remove um pacote instalado com suporte a hooks pre/post-remove.
    """
    run_hooks("pre-remove", meta)

    db_dir = CONFIG.get("db_dir", "db")
    installed_dir = os.path.join(db_dir, "installed")
    meta_file = os.path.join(installed_dir, f"{meta.name}.yaml")
    if os.path.exists(meta_file):
        os.remove(meta_file)
        log.success(f"🗑️ Removido {meta.name} do sistema")
    else:
        log.warn(f"Pacote {meta.name} não está instalado")

    run_hooks("post-remove", meta)
