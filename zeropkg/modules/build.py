# Zeropkg/zeropkg1.0/modules/build.py
import os
from core import CONFIG, log
from meta import MetaPackage
from hooks import run_hooks
import languages
from sandbox import run_in_sandbox


def prepare_build_dir(meta: MetaPackage, build_dir: str):
    """Prepara diretório de build limpo para o pacote."""
    pkg_build_dir = os.path.join(build_dir, f"{meta.name}-{meta.version}")
    os.makedirs(pkg_build_dir, exist_ok=True)
    log.debug(f"Build dir preparado: {pkg_build_dir}")
    return pkg_build_dir


def apply_patches(meta: MetaPackage, build_dir: str):
    """Aplica patches definidos no meta.yaml dentro do sandbox."""
    for patch in meta.patches:
        patch_path = os.path.join(CONFIG["patches_dir"], patch)
        if not os.path.exists(patch_path):
            log.warn(f"Patch não encontrado: {patch_path}")
            continue
        log.info(f"📌 Aplicando patch {patch}")
        run_in_sandbox(f"patch -p1 < {patch_path}", cwd=build_dir, check=True)


def build_package(meta: MetaPackage, build_dir: str):
    """
    Executa o ciclo de build completo em sandbox:
    - hooks pre-build
    - preparar diretório
    - aplicar patches
    - rodar builder correto (custom ou languages.py)
    - hooks post-build
    """
    log.info(f"🔨 Iniciando build de {meta.name}-{meta.version}")

    pkg_build_dir = prepare_build_dir(meta, build_dir)

    # Hooks pre-build
    run_hooks(meta.data.get("hooks", {}), "pre-build", cwd=pkg_build_dir)

    # Aplica patches
    apply_patches(meta, pkg_build_dir)

    # Build real
    if meta.build_commands:
        log.info("⚙️ Usando comandos customizados de build")
        for cmd in meta.build_commands:
            run_in_sandbox(cmd, cwd=pkg_build_dir, check=True)
    else:
        log.info(f"⚙️ Usando builder: {meta.build_system}")
        languages.build(meta, pkg_build_dir)

    # Hooks post-build
    run_hooks(meta.data.get("hooks", {}), "post-build", cwd=pkg_build_dir)

    log.success(f"✅ Build concluído para {meta.name}-{meta.version}")
    return pkg_build_dir
