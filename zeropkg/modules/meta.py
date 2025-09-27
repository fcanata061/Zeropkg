# Zeropkg/zeropkg1.0/modules/meta.py
import os, re, time, yaml
from typing import List, Dict, Any, Optional
from core import CONFIG, log

REQUIRED = ("name", "version")
LIST_KEYS = ("depends", "build_depends", "provides", "sources", "patches")
DEFAULTS = {"category": "misc", "priority": "normal"}

def parse_version(v: str) -> str:
    if not v: return ""
    v = str(v).strip()
    if v.startswith("v"): v = v[1:]
    return v

def version_compare(a: str, b: str) -> int:
    try:
        from packaging.version import parse as p
        va, vb = p(a), p(b)
        return 1 if va > vb else (-1 if va < vb else 0)
    except Exception:
        pa = [int(x) for x in re.findall(r"\d+", a)] if a else [0]
        pb = [int(x) for x in re.findall(r"\d+", b)] if b else [0]
        for i in range(max(len(pa), len(pb))):
            ai = pa[i] if i < len(pa) else 0
            bi = pb[i] if i < len(pb) else 0
            if ai>bi: return 1
            if ai<bi: return -1
        return 0

class MetaPackage:
    def __init__(self, source: str | Dict[str, Any]):
        self.path: Optional[str] = None
        self.data: Dict[str, Any] = {}
        if isinstance(source, dict):
            self.data = dict(source)
            self._normalize()
        elif isinstance(source, str):
            path = str(source)
            if os.path.exists(path):
                self.path = path
                self._load_file(path)
            else:
                # try find in ports tree
                found = self._find_in_ports(path)
                if found:
                    self.path = found
                    self._load_file(found)
                else:
                    raise FileNotFoundError(f"Meta '{path}' not found")
        else:
            raise TypeError("source must be path or dict")

    def _load_file(self, path):
        with open(path,"r",encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}
        self._normalize()

    def _find_in_ports(self, name: str) -> Optional[str]:
        repo = CONFIG.get("repo_base","/usr/ports/zeropkg")
        if not os.path.isdir(repo): return None
        for cat in os.listdir(repo):
            pkgdir = os.path.join(repo, cat, name)
            if os.path.isdir(pkgdir):
                metas = sorted([f for f in os.listdir(pkgdir) if f.endswith(".meta")])
                if metas:
                    return os.path.join(pkgdir, metas[-1])
        return None

    def _normalize(self):
        for k,v in DEFAULTS.items():
            if k not in self.data or self.data.get(k) is None:
                self.data[k] = v
        for lk in LIST_KEYS:
            val = self.data.get(lk)
            if val is None: self.data[lk]=[]
            elif isinstance(val,str): self.data[lk]=[val]
            elif not isinstance(val,list): self.data[lk]=[str(val)]
        self.data["version"] = parse_version(self.data.get("version"))
        if "hooks" not in self.data: self.data["hooks"] = {}

    # properties
    @property
    def name(self): return self.data.get("name")
    @property
    def version(self): return self.data.get("version")
    @property
    def category(self): return self.data.get("category", "misc")
    @property
    def upstream_url(self): return self.data.get("upstream_url")
    @property
    def priority(self): return self.data.get("priority","normal")
    @property
    def sources(self): return self.data.get("sources",[])
    @property
    def patches(self): return self.data.get("patches",[])
    @property
    def hooks(self): return self.data.get("hooks",{})
    @property
    def depends(self): return self.data.get("depends",[])
    @property
    def build_depends(self): return self.data.get("build_depends",[])

    # I/O
    def save_to_ports(self, version: Optional[str]=None) -> str:
        if version: self.data["version"]=parse_version(version)
        repo = CONFIG.get("repo_base","/usr/ports/zeropkg")
        pkgdir = os.path.join(repo, self.category, self.name)
        os.makedirs(pkgdir, exist_ok=True)
        fname = f"{self.name}-{self.version}.meta"
        out = os.path.join(pkgdir,fname)
        if os.path.exists(out):
            ts = int(time.time()); out = os.path.join(pkgdir, f"{self.name}-{self.version}-{ts}.meta")
        with open(out,"w",encoding="utf-8") as f:
            yaml.safe_dump(self.data,f,sort_keys=False)
        log.info(f"meta saved: {out}")
        return out

    def save_to_available(self) -> str:
        db = CONFIG.get("db_dir","~/zeropkg-db")
        db = os.path.expanduser(db)
        avail = os.path.join(db,"available"); os.makedirs(avail,exist_ok=True)
        out = os.path.join(avail,f"{self.name}.yaml")
        with open(out,"w",encoding="utf-8") as f:
            yaml.safe_dump(self.data,f,sort_keys=False)
        log.debug(f"saved available: {out}")
        return out

    @staticmethod
    def list_packages(repo_base:Optional[str]=None):
        repo = repo_base or CONFIG.get("repo_base","/usr/ports/zeropkg")
        pkgs=[]
        if not os.path.isdir(repo): return pkgs
        for cat in os.listdir(repo):
            catdir = os.path.join(repo,cat)
            if not os.path.isdir(catdir): continue
            for pkg in os.listdir(catdir):
                pkgs.append(f"{cat}/{pkg}")
        return sorted(pkgs)

    @staticmethod
    def load_latest(name: str):
        repo = CONFIG.get("repo_base","/usr/ports/zeropkg")
        for cat in os.listdir(repo):
            pkgdir = os.path.join(repo,cat,name)
            if os.path.isdir(pkgdir):
                metas = sorted([f for f in os.listdir(pkgdir) if f.endswith(".meta")])
                if metas:
                    return MetaPackage(os.path.join(pkgdir,metas[-1]))
        # fallback available
        avail = os.path.join(CONFIG.get("db_dir","~/zeropkg-db"),"available",f"{name}.yaml")
        if os.path.exists(avail):
            return MetaPackage(avail)
        return None

    def to_dict(self): return dict(self.data)
    def __repr__(self): return f"<MetaPackage {self.category}/{self.name}-{self.version}>"
