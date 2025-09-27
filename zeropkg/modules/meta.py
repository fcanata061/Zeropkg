# Zeropkg/zeropkg1.0/modules/meta.py
"""
meta.py — carregamento, validação e helpers para arquivos .meta / meta.yaml

Classe MetaPackage:
- Carrega um arquivo .meta/.yaml (path) ou um dicionário bruto.
- Valida campos essenciais (name, version).
- Expande variáveis com base em core.CONFIG (ex: ${PREFIX}, ${BUILD_DIR}).
- Salva meta atualizado em /base/<name>/<name>-<version>.meta
- Salva cópia/atualização em db/available/<name>.yaml
- Helpers para listar versões disponíveis no repo_base.
"""

import os
import re
import yaml
import shutil
from typing import List, Optional
from core import CONFIG, log

# Campos obrigatórios mínimos
REQUIRED_FIELDS = ("name", "version")


class MetaPackage:
    def __init__(self, source):
        """
        source: caminho para arquivo .meta/.yaml OU um dict com os campos do meta.
        Após inicialização, .data contém o dicionário do meta.
        """
        self.path = None
        self.data = {}
        if isinstance(source, (str, os.PathLike)):
            self.path = str(source)
            self.load_from_file(self.path)
        elif isinstance(source, dict):
            self.data = source.copy()
            self._expand_vars()
            self.validate()
        else:
            raise TypeError("MetaPackage: source deve ser path ou dict")

    # --------------------------
    # Load / Save
    # --------------------------
    def load_from_file(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Meta file não encontrado: {path}")
        with open(path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}
        self.path = path
        self._expand_vars()
        self.validate()
        log.debug(f"MetaPackage carregado: {self.name} {self.version}")

    def validate(self):
        missing = [k for k in REQUIRED_FIELDS if not self.data.get(k)]
        if missing:
            raise ValueError(f"Meta inválido — faltando campos: {missing}")

        # normalizar listas
        for key in ("depends", "build_depends", "provides", "sources", "patches"):
            if key in self.data and self.data[key] is None:
                self.data[key] = []
        # ensure hooks dict
        if "hooks" in self.data and self.data["hooks"] is None:
            self.data["hooks"] = {}
        if "hooks" not in self.data:
            self.data["hooks"] = {}

    # --------------------------
    # Variable expansion
    # --------------------------
    def _expand_vars(self):
        """
        Expande ocorrências ${KEY} usando core.CONFIG keys (case-insensitive).
        Exemplo: ${PREFIX}, ${BUILD_DIR}, ${DB_DIR}
        """
        def replace_in_str(s: str) -> str:
            if not isinstance(s, str):
                return s
            # primeira, substitui variáveis de ambiente do sistema
            for env_k, env_v in os.environ.items():
                s = s.replace(f"${{{env_k}}}", env_v)
            # agora substitui CONFIG keys
            for k, v in CONFIG.items():
                key = "${" + k.upper() + "}"
                s = s.replace(key, str(v))
            return s

        def recurse(obj):
            if isinstance(obj, str):
                return replace_in_str(obj)
            elif isinstance(obj, list):
                return [recurse(x) for x in obj]
            elif isinstance(obj, dict):
                return {k: recurse(v) for k, v in obj.items()}
            else:
                return obj

        self.data = recurse(self.data)

    # --------------------------
    # Propriedades úteis
    # --------------------------
    @property
    def name(self) -> str:
        return self.data.get("name")

    @property
    def version(self) -> str:
        return self.data.get("version")

    @property
    def category(self) -> Optional[str]:
        return self.data.get("category")

    @property
    def priority(self) -> str:
        return self.data.get("priority", "normal")

    @property
    def upstream_url(self) -> Optional[str]:
        return self.data.get("upstream_url")

    @property
    def description(self) -> Optional[str]:
        return self.data.get("description")

    @property
    def depends(self) -> List[str]:
        return self.data.get("depends", []) or []

    @property
    def build_depends(self) -> List[str]:
        return self.data.get("build_depends", []) or []

    @property
    def provides(self) -> List[str]:
        return self.data.get("provides", []) or []

    @property
    def sources(self) -> List:
        return self.data.get("sources", []) or []

    @property
    def patches(self) -> List:
        patches = self.data.get("patches", []) or []
        # if patches is list of dicts with 'file' key, normalize
        normalized = []
        for p in patches:
            if isinstance(p, dict) and "file" in p:
                normalized.append(p["file"])
            elif isinstance(p, str):
                normalized.append(p)
        return normalized

    @property
    def hooks(self) -> dict:
        return self.data.get("hooks", {}) or {}

    @property
    def build_system(self) -> str:
        return self.data.get("build", {}).get("system", self.data.get("build_system", "autotools"))

    @property
    def install_commands(self) -> List[str]:
        return self.data.get("install", {}).get("commands", []) or []

    @property
    def build_commands(self) -> List[str]:
        return self.data.get("build", {}).get("commands", []) or []

    # --------------------------
    # Save helpers
    # --------------------------
    def save_to_base(self, version: Optional[str] = None, repo_base: Optional[str] = None) -> str:
        """
        Salva (cria) um novo arquivo .meta em /base/<name>/<name>-<version>.meta.
        - version: se fornecido, setará self.data['version'] = version antes de salvar.
        - retorna o caminho do arquivo criado.
        """
        if version:
            self.data["version"] = version
        repo_base = repo_base or CONFIG.get("repo_base", "base")
        target_dir = os.path.join(repo_base, self.name)
        os.makedirs(target_dir, exist_ok=True)
        fname = f"{self.name}-{self.version}.meta"
        out_path = os.path.join(target_dir, fname)
        # não sobrescreve por padrão; cria um arquivo novo (se já existir, acrescenta suffix)
        if os.path.exists(out_path):
            # acrescentar timestamp para não sobrescrever
            import time
            ts = int(time.time())
            out_path = os.path.join(target_dir, f"{self.name}-{self.version}-{ts}.meta")
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, sort_keys=False)
        log.info(f"Meta salvo em base: {out_path}")
        return out_path

    def save_to_available(self, db_dir: Optional[str] = None) -> str:
        """
        Salva/atualiza db/available/<name>.yaml com a versão atual deste meta.
        Retorna caminho do arquivo gravado.
        """
        db_dir = db_dir or CONFIG.get("db_dir", "db")
        avail_dir = os.path.join(db_dir, "available")
        os.makedirs(avail_dir, exist_ok=True)
        out_path = os.path.join(avail_dir, f"{self.name}.yaml")
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, sort_keys=False)
        log.debug(f"Meta salvo em db available: {out_path}")
        return out_path

    # --------------------------
    # Listing / finding
    # --------------------------
    @staticmethod
    def list_package_names(repo_base: Optional[str] = None) -> List[str]:
        """Lista os nomes de pacotes existentes em repo_base (diretórios)."""
        repo_base = repo_base or CONFIG.get("repo_base", "base")
        if not os.path.isdir(repo_base):
            return []
        names = [d for d in os.listdir(repo_base) if os.path.isdir(os.path.join(repo_base, d))]
        return sorted(names)

    @staticmethod
    def list_versions_in_base(name: str, repo_base: Optional[str] = None) -> List[str]:
        """Retorna lista de versões encontradas em /base/<name> (baseando-se nos nomes dos arquivos)."""
        repo_base = repo_base or CONFIG.get("repo_base", "base")
        pkg_dir = os.path.join(repo_base, name)
        if not os.path.isdir(pkg_dir):
            return []
        versions = []
        for f in os.listdir(pkg_dir):
            if f.startswith(name + "-") and f.endswith(".meta"):
                ver = f[len(name) + 1 : -len(".meta")]
                versions.append(ver)
        # ordena alfabeticamente (agonisticamente) — consumidores podem aplicar comparação semântica
        versions.sort()
        return versions

    @staticmethod
    def load_from_base_latest(name: str, repo_base: Optional[str] = None):
        """
        Tenta carregar o meta mais recente do /base/<name> (arquivo com maior nome lexicográfico).
        Retorna MetaPackage ou None.
        """
        repo_base = repo_base or CONFIG.get("repo_base", "base")
        pkg_dir = os.path.join(repo_base, name)
        if not os.path.isdir(pkg_dir):
            return None
        meta_files = sorted([f for f in os.listdir(pkg_dir) if f.endswith(".meta")])
        if not meta_files:
            return None
        latest = meta_files[-1]
        return MetaPackage(os.path.join(pkg_dir, latest))

    # --------------------------
    # Representação
    # --------------------------
    def to_dict(self) -> dict:
        return self.data.copy()

    def __repr__(self):
        return f"<MetaPackage {self.name}-{self.version}>"

# --------------------------
# utilitário de conveniência
# --------------------------
def load_meta(path_or_name: str) -> MetaPackage:
    """
    Tenta carregar um MetaPackage a partir de:
      - caminho para arquivo (.meta/.yaml)
      - se for apenas um nome, tenta carregar o latest em /base/<name>/ ou db/available/<name>.yaml
    """
    # se path existe como arquivo direto
    if os.path.exists(path_or_name):
        return MetaPackage(path_or_name)

    # tentar carregar do repo base
    mp = MetaPackage.load_from_base_latest(path_or_name)
    if mp:
        return mp

    # tentar db/available
    db_av = os.path.join(CONFIG.get("db_dir", "db"), "available", f"{path_or_name}.yaml")
    if os.path.exists(db_av):
        return MetaPackage(db_av)

    raise FileNotFoundError(f"Meta '{path_or_name}' não encontrado em base nem em db/available")
