# Zeropkg/zeropkg1.0/modules/core.py
import os
import sys
import yaml
import subprocess
import logging

# ========================
# Configuração
# ========================

DEFAULT_CONFIG = {
    "build_dir": "/var/tmp/zeropkg/build",
    "sandbox_dir": "/var/tmp/zeropkg/sandbox",
    "install_dir": "/usr/local",
    "log_dir": "/var/log/zeropkg",
    "jobs": 4,
    "color": True,
    "verbose": False,
}

CONFIG_PATHS = [
    "/etc/zeropkg/config.yaml",
    os.path.expanduser("~/.config/zeropkg/config.yaml"),
]


def load_config():
    """Carrega configuração do Zeropkg a partir de YAML, com fallback para DEFAULT_CONFIG."""
    config = DEFAULT_CONFIG.copy()
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    config.update(data)
            except Exception as e:
                print(f"[WARN] Falha ao carregar {path}: {e}", file=sys.stderr)
    return config


CONFIG = load_config()

# ========================
# Logger colorido
# ========================

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",   # ciano
        logging.INFO: "\033[32m",    # verde
        logging.WARNING: "\033[33m", # amarelo
        logging.ERROR: "\033[31m",   # vermelho
        logging.CRITICAL: "\033[41m" # vermelho fundo
    }
    RESET = "\033[0m"

    def format(self, record):
        msg = super().format(record)
        if CONFIG.get("color", True):
            color = self.COLORS.get(record.levelno, "")
            return f"{color}{msg}{self.RESET}"
        return msg


def setup_logger():
    """Configura o logger global."""
    logger = logging.getLogger("zeropkg")
    if not logger.handlers:
        level = logging.DEBUG if CONFIG.get("verbose") else logging.INFO
        logger.setLevel(level)

        ch = logging.StreamHandler(sys.stdout)
        formatter = ColorFormatter("[%(levelname)s] %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        os.makedirs(CONFIG["log_dir"], exist_ok=True)
        fh = logging.FileHandler(os.path.join(CONFIG["log_dir"], "zeropkg.log"))
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)

    return logger


log = setup_logger()

# ========================
# Funções utilitárias
# ========================

def run_cmd(cmd, cwd=None, env=None, check=True):
    """
    Executa um comando no shell.
    Retorna stdout como string.
    """
    log.debug(f"Executando comando: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            shell=True,
            check=check,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        log.error(f"Comando falhou ({cmd}): {e.stderr.strip()}")
        if check:
            sys.exit(1)
        return e.stderr.strip()
