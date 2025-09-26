# Zeropkg/zeropkg1.0/modules/package.py
import os
import shutil
import json

from core import CONFIG, log, run_cmd


PKGDB_PATH = os.path.join(CONFIG["install_dir"], ".zeropkg_db.json")


# ========================
# Banco de dados de pacotes
# ========================

def load_pkgdb():
    """Carrega banco de dados simples de pacotes instalados."""
    if os.path.exists(PKGDB_PATH):
        with open(PKGDB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_pkgdb(db):
    os.makedirs(CONFIG["install_dir"], exist_ok=True)
    with open(PKGDB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


# ========================
# Instalação e remoção
# ========================

def install_package(pkg_name: str, source_dir: str, prefix: str = None):
    """
    Copia os arquivos compilados do source_dir para o prefix.
    """
    prefix = prefix or CONFIG["install_dir"]
    log.info(f"Instalando {pkg_name} em {prefix}")

    db = load_pkgdb()
    dest_dir = os.path.join(prefix, pkg_name)

    if os.path.exists(dest_dir):
        log.warning(f"Pacote {pkg_name} já instalado, sobrescrevendo...")

    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

    db[pkg_name] = {"path": dest_dir}
    save_pkgdb(db)
    log.info(f"Pacote {pkg_name} instalado com sucesso.")


def remove_package(pkg_name: str):
    """Remove pacote do prefix."""
    db = load_pkgdb()
    if pkg_name not in db:
        log.error(f"Pacote {pkg_name} não está instalado.")
        return

    pkg_path = db[pkg_name]["path"]
    if os.path.exists(pkg_path):
        shutil.rmtree(pkg_path)
        log.info(f"Removido: {pkg_path}")

    del db[pkg_name]
    save_pkgdb(db)
    log.info(f"Pacote {pkg_name} removido do sistema.")


# ========================
# Dependências
# ========================

def check_dependencies(pkg_name: str, deps: list):
    """
    Verifica se dependências estão instaladas.
    """
    db = load_pkgdb()
    missing = [dep for dep in deps if dep not in db]
    if missing:
        log.warning(f"Dependências ausentes para {pkg_name}: {missing}")
    else:
        log.info(f"Todas dependências de {pkg_name} estão satisfeitas.")
    return missing


# ========================
# Toolchain
# ========================

def select_toolchain(name: str):
    """
    Seleciona um toolchain (ex: gcc-12, clang, etc).
    Apenas muda variáveis de ambiente.
    """
    log.info(f"Selecionando toolchain: {name}")
    os.environ["CC"] = name
    os.environ["CXX"] = name.replace("gcc", "g++") if "gcc" in name else name + "++"
