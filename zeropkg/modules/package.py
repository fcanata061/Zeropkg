# Zeropkg/zeropkg1.0/modules/package.py
import os
from core import CONFIG, log, run_cmd
from meta import MetaPackage
from hooks import run_hooks
import languages


def install_package(meta: MetaPackage, install_dir: str):
    """
    Instala um pacote já compilado:
    - hooks pre-install
    - executa comandos customizados OU dispatcher de linguagem
    - hooks post-install
    """
    log.info(f"📦 Instalando {meta.name}-{meta.version} em {install_dir}")
    pkg_build_dir = os.path.join(CONFIG["build_dir"], f"{meta.name}-{meta.version}")

    # Hooks pre-install
    run_hooks(meta.data.get("hooks", {}), "pre-install", cwd=pkg_build_dir)

    # Instalação
    if meta.install_commands:
        log.info("⚙️ Usando comandos customizados de instalação")
        for cmd in meta.install_commands:
            run_cmd(cmd, cwd=pkg_build_dir, check=True)
    else:
        log.info(f"⚙️ Usando installer: {meta.build_system}")
        languages.install(meta, install_dir)

    # Hooks post-install
    run_hooks(meta.data.get("hooks", {}), "post-install", cwd=pkg_build_dir)

    log.success(f"✅ Pacote {meta.name}-{meta.version} instalado com sucesso em {install_dir}")


def remove_package(pkg_name: str):
    """
    Remove pacote instalado do diretório de instalação.
    (Por enquanto simples: apaga diretório)
    """
    pkg_dir = os.path.join(CONFIG["install_dir"], pkg_name)
    if not os.path.exists(pkg_dir):
        log.error(f"Pacote {pkg_name} não encontrado em {CONFIG['install_dir']}")
        return False

    log.info(f"🗑️ Removendo {pkg_name} de {CONFIG['install_dir']}")
    os.system(f"rm -rf {pkg_dir}")
    log.success(f"✅ Pacote {pkg_name} removido com sucesso")
    return True
