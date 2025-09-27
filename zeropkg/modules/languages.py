# Zeropkg/zeropkg1.0/modules/languages.py
import os
from core import log, CONFIG, run_cmd
from meta import MetaPackage


# ========================
# Python builder
# ========================

def build_python(meta: MetaPackage, build_dir: str):
    log.info(f"🐍 Build Python package {meta.name}")
    src_dir = os.path.join(build_dir, f"{meta.name}-{meta.version}")
    run_cmd(f"{CONFIG['python_bin']} setup.py build", cwd=src_dir, check=True)


def install_python(meta: MetaPackage, install_dir: str):
    log.info(f"📦 Install Python package {meta.name}")
    src_dir = os.path.join(CONFIG["build_dir"], f"{meta.name}-{meta.version}")
    run_cmd(f"{CONFIG['python_bin']} setup.py install --prefix={install_dir}", cwd=src_dir, check=True)


# ========================
# Rust builder
# ========================

def build_rust(meta: MetaPackage, build_dir: str):
    log.info(f"🦀 Build Rust crate {meta.name}")
    src_dir = os.path.join(build_dir, f"{meta.name}-{meta.version}")
    run_cmd("cargo build --release", cwd=src_dir, check=True)


def install_rust(meta: MetaPackage, install_dir: str):
    log.info(f"📦 Install Rust crate {meta.name}")
    src_dir = os.path.join(CONFIG["build_dir"], f"{meta.name}-{meta.version}")
    run_cmd(f"cargo install --path . --root {install_dir}", cwd=src_dir, check=True)


# ========================
# Java builder
# ========================

def build_java(meta: MetaPackage, build_dir: str):
    log.info(f"☕ Build Java project {meta.name}")
    src_dir = os.path.join(build_dir, f"{meta.name}-{meta.version}")
    run_cmd("javac -d build $(find src -name '*.java')", cwd=src_dir, check=True)


def install_java(meta: MetaPackage, install_dir: str):
    log.info(f"📦 Install Java project {meta.name}")
    jar_file = f"{meta.name}-{meta.version}.jar"
    src_dir = os.path.join(CONFIG["build_dir"], f"{meta.name}-{meta.version}")
    run_cmd(f"jar cf {jar_file} -C build .", cwd=src_dir, check=True)
    os.makedirs(install_dir, exist_ok=True)
    run_cmd(f"mv {jar_file} {install_dir}/", cwd=src_dir, check=True)


# ========================
# Dispatcher
# ========================

def build(meta: MetaPackage, build_dir: str):
    system = meta.build_system.lower()
    if system == "python":
        build_python(meta, build_dir)
    elif system == "rust":
        build_rust(meta, build_dir)
    elif system == "java":
        build_java(meta, build_dir)
    else:
        log.warn(f"⚠️ Linguagem '{system}' não suportada neste módulo")


def install(meta: MetaPackage, install_dir: str):
    system = meta.build_system.lower()
    if system == "python":
        install_python(meta, install_dir)
    elif system == "rust":
        install_rust(meta, install_dir)
    elif system == "java":
        install_java(meta, install_dir)
    else:
        log.warn(f"⚠️ Linguagem '{system}' não suportada neste módulo")
