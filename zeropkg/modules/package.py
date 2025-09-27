# Zeropkg/zeropkg1.0/modules/package.py
import os
import tarfile
import yaml
import shutil
from datetime import datetime
from core import CONFIG, log
from meta import MetaPackage
from hooks import run_hooks
from sandbox import run_in_sandbox


def fake_install(meta: MetaPackage, build_dir: str, staging_dir: str):
    """Instala o pacote em diretório fake (DESTDIR) dentro do sandbox."""
    destdir = os.path.join(staging_dir, f"{meta.name}-{meta.version}")
    os.makedirs(destdir, exist_ok=True)

    log.info(f"📦 Instalando {meta.name} em staging (fakeroot)")
    run_in_sandbox(f"make install DESTDIR={destdir}", cwd=build_dir, check=True)

    return destdir


def create_package(meta: MetaPackage, staging_dir: str, destdir: str):
    """Empacota o diretório fake em um .zpkg."""
    out_file = os.path.join(staging_dir, f"{meta.name}-{meta.version}.zpkg")

    log.info(f"📦 Criando pacote {out_file}")
    with tarfile.open(out_file, "w:gz") as tar:
        tar.add(destdir, arcname=os.path.basename(destdir))

    return out_file


def register_manifest(meta: MetaPackage, destdir: str):
    """Registra manifesto com todos os arquivos instalados."""
    manifest_dir = os.path.join(CONFIG["db_dir"], "installed")
    os.makedirs(manifest_dir, exist_ok=True)

    files = []
    for root, _, filenames in os.walk(destdir):
        for f in filenames:
            fullpath = os.path.relpath(os.path.join(root, f), destdir)
            files.append(fullpath)

    manifest = {
        "name": meta.name,
        "version": meta.version,
        "files": files,
        "installed_at": datetime.utcnow().isoformat()
    }

    out_file = os.path.join(manifest_dir, f"{meta.name}.yaml")
    with open(out_file, "w") as f:
        yaml.safe_dump(manifest, f)

    log.success(f"✅ Manifesto registrado: {out_file}")


def install(meta: MetaPackage, build_dir: str, staging_dir: str):
    """Fluxo completo de instalação com hooks + sandbox + manifesto."""
    log.info(f"🚀 Instalando {meta.name}-{meta.version}")

    run_hooks(meta.data.get("hooks", {}), "pre-install", cwd=build_dir)

    destdir = fake_install(meta, build_dir, staging_dir)
    pkg_file = create_package(meta, staging_dir, destdir)
    register_manifest(meta, destdir)

    run_hooks(meta.data.get("hooks", {}), "post-install", cwd=destdir)

    log.success(f"🎉 {meta.name}-{meta.version} instalado com sucesso!")
    return pkg_file


def remove(meta_name: str):
    """Remove um pacote baseado no manifesto, com hooks pre/post-remove."""
    manifest_file = os.path.join(CONFIG["db_dir"], "installed", f"{meta_name}.yaml")
    if not os.path.exists(manifest_file):
        log.error(f"Manifesto de {meta_name} não encontrado!")
        return

    with open(manifest_file) as f:
        manifest = yaml.safe_load(f)

    # Hooks pre-remove
    pkg_dir = CONFIG["install_dir"]
    run_hooks({}, "pre-remove", cwd=pkg_dir)  # hooks podem ser carregados do meta original

    # Remover arquivos
    log.info(f"🗑️ Removendo {meta_name}")
    for f in manifest["files"]:
        try:
            os.remove(os.path.join(pkg_dir, f))
        except FileNotFoundError:
            log.warn(f"Arquivo já ausente: {f}")

    # Apagar manifesto
    os.remove(manifest_file)

    # Hooks post-remove
    run_hooks({}, "post-remove", cwd=pkg_dir)

    log.success(f"✅ {meta_name} removido com sucesso!")
