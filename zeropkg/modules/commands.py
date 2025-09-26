# Zeropkg/zeropkg1.0/modules/commands.py
import argparse
import os

from core import log, CONFIG
from fetch import download_file, extract_file
from build import create_sandbox, clean_sandbox, apply_patches, build_package
from package import install_package, remove_package, check_dependencies
from system import list_installed, audit_system, notify


def cmd_install(args):
    pkg = args.name
    url = args.url
    patches = args.patches or []
    build_system = args.build
    prefix = CONFIG["install_dir"]

    log.info(f"==> Instalando pacote {pkg}")

    # 1. Baixar
    src = download_file(url)

    # 2. Extrair se for arquivo
    sandbox = create_sandbox(pkg)
    if os.path.isfile(src):
        extract_file(src, sandbox)
    else:
        sandbox = src  # já é diretório (ex: git clone)

    # 3. Aplicar patches
    if patches:
        apply_patches(sandbox, patches)

    # 4. Build
    build_package(sandbox, build_system, prefix)

    # 5. Instalar
    install_package(pkg, sandbox, prefix)

    notify("Zeropkg", f"Pacote {pkg} instalado com sucesso.")


def cmd_remove(args):
    pkg = args.name
    log.info(f"==> Removendo pacote {pkg}")
    remove_package(pkg)
    notify("Zeropkg", f"Pacote {pkg} removido.")


def cmd_list(args):
    list_installed()


def cmd_audit(args):
    audit_system()


# ========================
# CLI principal
# ========================

def main():
    parser = argparse.ArgumentParser(prog="zeropkg", description="Zeropkg package manager")
    sub = parser.add_subparsers(dest="command")

    # install
    p_install = sub.add_parser("install", help="Instalar um pacote")
    p_install.add_argument("name", help="Nome do pacote")
    p_install.add_argument("url", help="URL de origem (tar.gz, git, etc)")
    p_install.add_argument("--build", default="autotools", help="Sistema de build (autotools, cargo, go, python, java, custom)")
    p_install.add_argument("--patches", nargs="*", help="Lista de patches a aplicar")
    p_install.set_defaults(func=cmd_install)

    # remove
    p_remove = sub.add_parser("remove", help="Remover um pacote")
    p_remove.add_argument("name", help="Nome do pacote")
    p_remove.set_defaults(func=cmd_remove)

    # list
    p_list = sub.add_parser("list", help="Listar pacotes instalados")
    p_list.set_defaults(func=cmd_list)

    # audit
    p_audit = sub.add_parser("audit", help="Auditar sistema")
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
