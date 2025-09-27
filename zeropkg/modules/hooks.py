# Zeropkg/zeropkg1.0/modules/hooks.py
import os
from core import CONFIG, log, run_cmd


class HookManager:
    """
    Gerencia hooks definidos em meta.yaml ou config.yaml.
    """

    def __init__(self, hooks: dict = None):
        # Hooks vindos do pacote
        self.package_hooks = hooks or {}
        # Hooks globais (do config.yaml)
        self.global_hooks = CONFIG.get("hooks", {})

    def _expand(self, cmd: str) -> str:
        """Expande variáveis de ambiente do Zeropkg dentro do comando."""
        for k, v in CONFIG.items():
            cmd = cmd.replace("${" + k.upper() + "}", str(v))
        return cmd

    def run(self, stage: str, cwd: str = None):
        """
        Executa hooks de uma fase (ex: pre-build, post-build, pre-install, post-install).
        """
        hooks_to_run = []

        # 1. Hooks globais do config.yaml
        if stage in self.global_hooks:
            hooks_to_run.extend(self.global_hooks[stage])

        # 2. Hooks do pacote (meta.yaml)
        if stage in self.package_hooks:
            hooks_to_run.extend(self.package_hooks[stage])

        # 3. Executa
        if not hooks_to_run:
            log.debug(f"Nenhum hook para {stage}")
            return

        log.info(f"Executando hooks para {stage}")
        for cmd in hooks_to_run:
            cmd_expanded = self._expand(cmd)
            run_cmd(cmd_expanded, cwd=cwd, check=True)


# ========================
# Função utilitária
# ========================

def run_hooks(hooks: dict, stage: str, cwd: str = None):
    """
    Executa hooks direto sem precisar instanciar.
    """
    manager = HookManager(hooks)
    manager.run(stage, cwd)
