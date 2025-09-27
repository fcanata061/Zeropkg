# Zeropkg/zeropkg1.0/modules/meta.py
import os
import yaml
from core import CONFIG, log


class MetaPackage:
    """
    Representa os metadados de um pacote (meta.yaml).
    """

    def __init__(self, path: str):
        self.path = path
        self.data = {}
        self.load()

    def load(self):
        """Carrega e valida o meta.yaml."""
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Meta file não encontrado: {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}

        # Substitui variáveis da config (ex: ${PREFIX}, ${BUILD_DIR})
        self._expand_vars()

        log.debug(f"Meta carregado: {self.data.get('name', '???')}")

    def _expand_vars(self):
        """Expande variáveis no YAML usando CONFIG."""
        def expand(value):
            if isinstance(value, str):
                for k, v in CONFIG.items():
                    key = "${" + k.upper() + "}"
                    value = value.replace(key, str(v))
            return value

        def recurse(obj):
            if isinstance(obj, dict):
                return {k: recurse(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [recurse(v) for v in obj]
            else:
                return expand(obj)

        self.data = recurse(self.data)

    # ========================
    # Getters convenientes
    # ========================

    @property
    def name(self):
        return self.data.get("name")

    @property
    def version(self):
        return self.data.get("version")

    @property
    def sources(self):
        return self.data.get("sources", [])

    @property
    def patches(self):
        return [p["file"] for p in self.data.get("patches", [])]

    @property
    def build_system(self):
        return self.data.get("build", {}).get("system", "autotools")

    @property
    def build_commands(self):
        return self.data.get("build", {}).get("commands", [])

    @property
    def install_commands(self):
        return self.data.get("install", {}).get("commands", [])

    @property
    def dependencies_build(self):
        return self.data.get("dependencies", {}).get("build", [])

    @property
    def dependencies_run(self):
        return self.data.get("dependencies", {}).get("run", [])


# ========================
# Função utilitária
# ========================

def load_meta(path: str) -> MetaPackage:
    """Carrega um pacote meta.yaml e retorna objeto MetaPackage."""
    return MetaPackage(path)
