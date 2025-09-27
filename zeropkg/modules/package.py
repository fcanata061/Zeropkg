# Zeropkg/zeropkg1.0/modules/package.py
import os
import tarfile
import hashlib
import time
import yaml
from core import CONFIG, log, run_cmd
from meta import MetaPackage
from hooks import run_hooks


def _hash_file(path):
    """Calcula hash SHA256 de um arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _generate_manifest(meta: MetaPackage, pkgroot: str, zpkg_path: str):
    """Gera manifesto YAML com todos os arquivos instalados."""
    files = []
    for root, _, filenames in os.walk(pkgroot):
        for fname in filenames:
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, pkgroot)
            files.append({
                "path": relpath,
                "hash": _hash_file(fpath),
                "size": os.path.getsize(fpath)
            })

    manifest = {
        "name": meta.name,
        "version": meta.version,
        "build_system": meta.build_system,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": files,
        "package_file": zpkg_path
    }

    db_dir = CONFIG["db_dir"]
    os.makedirs(os.path.join(db_dir, "installed"), exist_ok=True)
    manifest_path = os.path.join(db_dir, "installed", f"{meta.name}.yaml")
    with open(manifest_path, "w") as f:
        yaml.safe_dump(manifest, f)

    log.info(f"📑 Manifesto salvo em {manifest_path}")
    return manifest


def _create_zpkg(pkgroot: str, meta: MetaPackage):
    """Compacta staging em pacote .zpkg."""
    out_dir = CONFIG["packages_dir"]
    os.makedirs(out_dir, exist_ok=True)
    zpkg_path = os.path.join(out_dir, f"{meta.name}-{meta.version}.zpkg")

    with tarfile.open(zpkg_path, "w:xz") as tar:
        tar.add(pkgroot, arcname="")

    log.success(f"📦 Pacote criado: {zpkg_path}")
    return zpkg_path


def install_package(meta: MetaPackage, install_dir: str):
    """
    Instala pacote com fluxo completo:
    - hooks pre-install
    - fakeroot install em staging
    - hooks post-install
    - empacota em .zpkg
    - gera manifesto + log
    - instala real
    """
    pkg_build_dir = os.path.join(CONFIG["build_dir"], f"{meta.name}-{meta.version}")
    pkgroot = os.path.join(pkg_build_dir, "pkgroot")
    os.makedirs(pkgroot, exist_ok=True)

    # Hooks pre-install
    run_hooks(meta.data.get("hooks", {}), "pre-install", cwd=pkg_build_dir)

    # Instalação fake em staging
    log.info(f"📦 Instalando {meta.name} em staging (fakeroot)")
    run_cmd("make install DESTDIR=" + pkgroot, cwd=pkg_build_dir)

    # Hooks post-install
    run_hooks(meta.data.get("hooks", {}), "post-install", cwd=pkg_build_dir)

    # Cria pacote
    zpkg_path = _create_zpkg(pkgroot, meta)

    # Gera manifesto
    _generate_manifest(meta, pkgroot, zpkg_path)

    # Instala real
    log.info(f"📂 Extraindo {zpkg_path} para {install_dir}")
    with tarfile.open(zpkg_path, "r:xz") as tar:
        tar.extractall(install_dir)

    log.success(f"✅ Pacote {meta.name}-{meta.version} instalado em {install_dir}")


def remove_package(pkg_name: str):
    """
    Remove pacote com base no manifesto:
    - hooks pre-remove
    - remove arquivos listados
    - hooks post-remove
    - limpa registro
    """
    manifest_path = os.path.join(CONFIG["db_dir"], "installed", f"{pkg_name}.yaml")
    if not os.path.exists(manifest_path):
        log.error(f"Manifesto do pacote {pkg_name} não encontrado")
        return False

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Hooks pre-remove
    run_hooks(manifest.get("hooks", {}), "pre-remove", cwd=CONFIG["install_dir"])

    # Remove arquivos
    for entry in manifest["files"]:
        fpath = os.path.join(CONFIG["install_dir"], entry["path"])
        if os.path.exists(fpath):
            os.remove(fpath)
            log.debug(f"🗑️ Removido {fpath}")

    # Hooks post-remove
    run_hooks(manifest.get("hooks", {}), "post-remove", cwd=CONFIG["install_dir"])

    # Remove manifesto
    os.remove(manifest_path)
    log.success(f"✅ Pacote {pkg_name} removido e registro apagado")
    return True
