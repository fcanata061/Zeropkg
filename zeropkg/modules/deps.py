# Zeropkg - deps.py
# Novo módulo contendo revdep_rebuild

import os
import subprocess
from core import CONFIG, log


def revdep_rebuild():
    """
    Faz checagem reversa de dependências:
    - Percorre binários instalados em db/installed
    - Roda ldd e procura 'not found'
    - Retorna pacotes que precisam ser recompilados
    """
    db_dir = CONFIG.get("db_dir", "db")
    installed_dir = os.path.join(db_dir, "installed")
    if not os.path.isdir(installed_dir):
        log.warn("Nenhum pacote instalado encontrado.")
        return []

    broken = []
    for pkg in os.listdir(installed_dir):
        pkg_path = os.path.join(installed_dir, pkg)
        bin_dir = os.path.join(pkg_path, "bin")
        if not os.path.isdir(bin_dir):
            continue
        for f in os.listdir(bin_dir):
            path = os.path.join(bin_dir, f)
            try:
                res = subprocess.run(["ldd", path], capture_output=True, text=True)
                if "not found" in res.stdout:
                    broken.append(pkg)
                    log.warn(f"⚠️ {pkg} depende de libs quebradas ({f})")
                    break
            except Exception as e:
                log.debug(f"Erro ao rodar ldd em {path}: {e}")

    if broken:
        log.warn(f"Pacotes a recompilar: {broken}")
    else:
        log.success("✅ Nenhuma dependência quebrada detectada")
    return broken
