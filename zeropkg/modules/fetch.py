# Zeropkg/zeropkg1.0/modules/fetch.py
import os
import shutil
import tarfile
import zipfile
import urllib.request
import subprocess

from core import CONFIG, log, run_cmd


CACHE_DIR = os.path.join(CONFIG["build_dir"], "distfiles")
os.makedirs(CACHE_DIR, exist_ok=True)


# ========================
# Download
# ========================

def download_file(url: str, dest: str = None) -> str:
    """
    Baixa um arquivo da internet ou clona de um repositório.
    Retorna o caminho do arquivo/diretório baixado.
    """
    log.info(f"Baixando: {url}")

    if dest is None:
        filename = os.path.basename(url)
        dest = os.path.join(CACHE_DIR, filename)

    # Se já existe no cache, reaproveita
    if os.path.exists(dest):
        log.info(f"Usando cache: {dest}")
        return dest

    # Git clone
    if url.startswith("git://") or url.endswith(".git") or url.startswith("https://github.com/"):
        repo_name = os.path.basename(url).replace(".git", "")
        dest_dir = os.path.join(CACHE_DIR, repo_name)
        if os.path.exists(dest_dir):
            log.info(f"Repositório já clonado em {dest_dir}")
            return dest_dir
        run_cmd(f"git clone {url} {dest_dir}")
        return dest_dir

    # HTTP/HTTPS/FTP download
    try:
        with urllib.request.urlopen(url) as response, open(dest, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
    except Exception as e:
        log.error(f"Falha no download de {url}: {e}")
        raise

    return dest


# ========================
# Extração
# ========================

def extract_file(archive_path: str, dest_dir: str) -> str:
    """
    Extrai um arquivo compactado para dest_dir.
    Retorna o caminho da pasta extraída.
    """
    log.info(f"Extraindo: {archive_path} → {dest_dir}")
    os.makedirs(dest_dir, exist_ok=True)

    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=dest_dir)
    elif zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)
    else:
        log.error(f"Formato não suportado: {archive_path}")
        raise ValueError("Formato de arquivo não suportado")

    return dest_dir
