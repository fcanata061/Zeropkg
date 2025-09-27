# Zeropkg - package.py
# Gerenciamento de pacotes: criação, instalação, remoção, listagem, info
# Atualizado com suporte a hooks e empacotamento

import os
import tarfile
import subprocess
import yaml
from core import CONFIG, log
from meta import MetaPackage


def list_packages(directory: str):
    """Lista pacotes em um diretório (db/available ou db/installed)."""
    if not os.path.isdir(directory):
        return []
    return [p.replace(".yaml", "") for p in os.listdir(directory) if p.endswith(".yaml")]


def list_installed_packages():
    """Lista pacotes instalados."""
    db_dir = CONFIG.get("db_dir", "db")
    installed_dir = os.path.join(db_dir, "installed")
    return list_packages(installed_dir)


def list_available_packages():
    """Lista pacotes disponíveis para instalação."""
    db_dir = CONFIG.get("db_dir", "db")
    available_dir = os.path.join(db_dir, "available")
    return list_packages(available_dir)


def show_package_info(pkgname: str):
    """Exibe informações de um pacote (meta YAML)."""
    db_dir = CONFIG.get("db_dir", "db")
    available_dir = os.path.join(db_dir, "available")
    meta_file = os.path.join(available_dir, f"{pkgname}.yaml")

    if not os.path.exists(meta_file):
        log.warn(f"Pacote {pkgname} não encontrado no available.")
        return None

    data = yaml.safe_load(open(meta_file))
    print(yaml.dump(data, sort_keys=False))
    return data


# -----------------------------
# 🔥 Evoluções: Hooks e Empacotamento
# -----------------------------

def run_hooks(hook_type: str, meta: MetaPackage):
    """Executa hooks pre/post-install/remove se existirem."""
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
