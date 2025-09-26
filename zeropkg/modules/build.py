# Zeropkg/zeropkg1.0/modules/build.py
import os
import subprocess
import shutil

from core import CONFIG, log, run_cmd


# ========================
# Sandbox
# ========================

def create_sandbox(pkg_name: str) -> str:
    """
    Cria diretório sandbox isolado para o pacote.
    """
    sandbox_path = os.path.join(CONFIG["sandbox_dir"], pkg_name)
    if os.path.exists(sandbox_path):
        log.info(f"Reutilizando sandbox existente: {sandbox_path}")
    else:
        os.makedirs(sandbox_path, exist_ok=True)
        log.info(f"Sandbox criado: {sandbox_path}")
    return sandbox_path


def clean_sandbox(pkg_name: str):
    """
    Remove sandbox do pacote.
    """
    sandbox_path = os.path.join(CONFIG["sandbox_dir"], pkg_name)
    if os.path.exists(sandbox_path):
        shutil.rmtree(sandbox_path)
        log.info(f"Sandbox removido: {sandbox_path}")


# ========================
# Patches
# ========================

def apply_patch(source_dir: str, patch_file: str):
    """
    Aplica um patch (arquivo .patch).
    """
    log.info(f"Aplicando patch: {patch_file}")
    run_cmd(f"patch -p1 < {patch_file}", cwd=source_dir)


def apply_patches(source_dir: str, patch_list: list):
    """
    Aplica lista de patches no source.
    """
    for patch in patch_list:
        apply_patch(source_dir, patch)


# ========================
# Build Manager
# ========================

def build_autotools(source_dir: str, prefix: str):
    run_cmd(f"./configure --prefix={prefix}", cwd=source_dir)
    run_cmd(f"make -j{CONFIG['jobs']}", cwd=source_dir)


def build_cargo(source_dir: str, prefix: str):
    run_cmd(f"cargo build --release", cwd=source_dir)
    run_cmd(f"cargo install --path . --root {prefix}", cwd=source_dir)


def build_go(source_dir: str, prefix: str):
    run_cmd(f"go build -o {prefix}/bin/", cwd=source_dir)


def build_python(source_dir: str, prefix: str):
    run_cmd(f"python3 setup.py build", cwd=source_dir)
    run_cmd(f"python3 setup.py install --prefix={prefix}", cwd=source_dir)


def build_java(source_dir: str, prefix: str):
    run_cmd(f"javac *.java", cwd=source_dir)
    # Instalação Java é custom, depende do projeto


def build_custom(source_dir: str, commands: list, prefix: str):
    for cmd in commands:
        run_cmd(cmd.replace("${PREFIX}", prefix), cwd=source_dir)


def build_package(source_dir: str, build_system: str, prefix: str, commands: list = None):
    """
    Detecta e executa build conforme sistema informado.
    """
    log.info(f"Iniciando build ({build_system}) em {source_dir}")
    if build_system == "autotools":
        build_autotools(source_dir, prefix)
    elif build_system == "cargo":
        build_cargo(source_dir, prefix)
    elif build_system == "go":
        build_go(source_dir, prefix)
    elif build_system == "python":
        build_python(source_dir, prefix)
    elif build_system == "java":
        build_java(source_dir, prefix)
    elif build_system == "custom" and commands:
        build_custom(source_dir, commands, prefix)
    else:
        log.error(f"Sistema de build não suportado: {build_system}")
        raise ValueError("Build system inválido")
