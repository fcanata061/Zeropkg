# Zeropkg/zeropkg1.0/modules/sync.py
import os
import subprocess
from core import log, CONFIG


def _run_git(cmd, cwd):
    """Executa comando git no diretório certo."""
    try:
        subprocess.run(
            ["git"] + cmd,
            cwd=cwd,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        log.error(f"Erro no git {' '.join(cmd)}: {e}")
        raise


def sync_repo():
    """
    Sincroniza o repositório local com o remoto.
    - Puxa commits novos
    - Faz push de commits locais
    """
    repo_dir = CONFIG.get("repo_dir")

    if not repo_dir or not os.path.exists(repo_dir):
        raise FileNotFoundError("Diretório do repositório Git não configurado ou não existe")

    log.info(f"🔄 Sincronizando repositório em {repo_dir}")

    # Atualiza branch atual com remoto
    _run_git(["pull", "--rebase"], cwd=repo_dir)

    # Faz push das mudanças locais
    _run_git(["push"], cwd=repo_dir)

    log.success("✅ Repositório sincronizado com sucesso")


def commit_changes(message="Atualização de pacotes"):
    """
    Adiciona e commita mudanças no repositório local.
    """
    repo_dir = CONFIG.get("repo_dir")

    if not repo_dir or not os.path.exists(repo_dir):
        raise FileNotFoundError("Diretório do repositório Git não configurado ou não existe")

    log.info("📝 Commitando mudanças no repositório")

    _run_git(["add", "."], cwd=repo_dir)
    _run_git(["commit", "-m", message], cwd=repo_dir)

    log.success("✅ Mudanças commitadas localmente")
