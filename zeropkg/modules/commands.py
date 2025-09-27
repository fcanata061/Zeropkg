# Zeropkg/zeropkg1.0/modules/commands.py
import argparse
import sys
from core import log, CONFIG
from meta import load_meta
from fetch import fetch_sources
from build import build_package
from package import install_package, remove_package
from upgrade import upgrade_package, upgrade_all
from sync import sync_repo, commit_changes
from update_upstream import check_update, check_all
from system import audit_all, list_installed


def main():
    parser = argparse.ArgumentParser(
        prog="zeropkg",
        description="Zeropkg - Gerenciador de pacotes do zero 🚀"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ========================
    # install
    # ========================
    p_install = sub.add_parser("install", help="Instalar pacote")
    p_install.add_argument("meta", help="Arquivo meta.yaml do pacote")

    # ========================
    # remove
    # ========================
    p_remove = sub.add_parser("remove", help="Remover pacote")
    p_remove.add_argument("name", help="Nome do pacote instalado")

    # ========================
    # build
    # ========================
    p_build = sub.add_parser("build", help="Compilar pacote")
    p_build.add_argument("meta", help="Arquivo meta.yaml do pacote")

    # ========================
    # fetch
    # ========================
    p_fetch = sub.add_parser("fetch", help="Baixar fontes do pacote")
    p_fetch.add_argument("meta", help="Arquivo meta.yaml do pacote")

    # ========================
    # upgrade
    # ========================
    p_upgrade = sub.add_parser("upgrade", help="Atualizar pacote")
    p_upgrade.add_argument("meta", nargs="?", help="Arquivo meta.yaml (se vazio, todos)")

    # ========================
    # sync
    # ========================
    p_sync = sub.add_parser("sync", help="Sincronizar repositório Git")
    p_commit = sub.add_parser("commit", help="Commitar mudanças no repo Git")
    p_commit.add_argument("-m", "--message", default="Atualização Zeropkg", help="Mensagem do commit")

    # ========================
    # update-upstream
    # ========================
    p_upstream = sub.add_parser("update", help="Checar novas versões upstream")
    p_upstream.add_argument("meta", nargs="?", help="Arquivo meta.yaml (se vazio, todos)")

    # ========================
    # audit
    # ========================
    sub.add_parser("audit", help="Rodar auditoria completa")
    sub.add_parser("list", help="Listar pacotes instalados")

    args = parser.parse_args()

    # ========================
    # Execução
    # ========================
    if args.command == "install":
        meta = load_meta(args.meta)
        fetch_sources(meta, CONFIG["fetch_dir"])
        build_package(meta, CONFIG["build_dir"])
        install_package(meta, CONFIG["install_dir"])

    elif args.command == "remove":
        remove_package(args.name)

    elif args.command == "build":
        meta = load_meta(args.meta)
        build_package(meta, CONFIG["build_dir"])

    elif args.command == "fetch":
        meta = load_meta(args.meta)
        fetch_sources(meta, CONFIG["fetch_dir"])

    elif args.command == "upgrade":
        if args.meta:
            upgrade_package(args.meta)
        else:
            # TODO: scan all meta.yaml no repo local
            log.warn("Upgrade all ainda não implementado com scan automático")

    elif args.command == "sync":
        sync_repo()

    elif args.command == "commit":
        commit_changes(args.message)

    elif args.command == "update":
        if args.meta:
            check_update(args.meta)
        else:
            # TODO: scan all meta.yaml no repo local
            log.warn("Update all ainda não implementado com scan automático")

    elif args.command == "audit":
        audit_all()

    elif args.command == "list":
        list_installed()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.error("Execução interrompida pelo usuário")
        sys.exit(1)
