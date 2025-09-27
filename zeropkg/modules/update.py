# Zeropkg/zeropkg1.0/modules/update.py
"""
update.py — checagem de versões upstream, geração de relatórios e cópia de novos .meta para /base/<pkg>/

Funcionalidades:
- Varre os pacotes em repo_base (base) e também os metas em db/available.
- Para cada pacote com campo upstream_url tenta descobrir a última versão upstream.
- Compara com versão corrente no meta e, se houver nova, salva novo .meta em /base/<pkg>/<pkg>-<versão>.meta
  e atualiza db/available/<pkg>.yaml.
- Gera updates_report.yaml (detalhado) e updates_summary.yaml (resumo numérico para bar).
- Dispara notify-send (se disponível) com resumo.
"""
import os
import re
import yaml
import requests
import subprocess
import json
from datetime import datetime
from bs4 import BeautifulSoup

from core import CONFIG, log
from meta import MetaPackage

# Timeouts / headers
HTTP_TIMEOUT = CONFIG.get("http_timeout", 10)
USER_AGENT = CONFIG.get("user_agent", "zeropkg-updater/1.0")

# Arquivos gerados
def _get_paths():
    db_dir = CONFIG.get("db_dir", "db")
    os.makedirs(db_dir, exist_ok=True)
    report_file = os.path.join(db_dir, "updates_report.yaml")
    summary_file = os.path.join(db_dir, "updates_summary.yaml")
    bar_file = os.path.join(db_dir, "updates_bar.json")  # JSON para bar (polybar/waybar)
    return report_file, summary_file, bar_file

# --------------------------
# Versão / comparação
# --------------------------
def _parse_version_candidates(text: str) -> list:
    """
    Retorna lista de strings que parecem versões (ex: 1.2.3, v1.2, 14.0.1).
    """
    # regex para versões (simples, captura 1.2 1.2.3 1.2.3-rc1 etc)
    pattern = r'v?(\d+(?:\.\d+){0,3}(?:[-_a-zA-Z0-9\.]*)?)'
    matches = re.findall(pattern, text)
    # filtrar ruídos curtos
    candidates = [m for m in matches if len(m) >= 1]
    return candidates

def _normalize_version(v: str) -> str:
    # remove prefix "v"
    if not v:
        return v
    if v.startswith("v"):
        return v[1:]
    return v

def _version_cmp(a: str, b: str) -> int:
    """
    Compara versões de forma robusta se possível (usa packaging.version se disponível),
    senão faz comparação numérica heurística.
    Retorna: 1 se a > b, -1 se a < b, 0 se iguais.
    """
    try:
        from packaging.version import parse as vparse
        va = vparse(a)
        vb = vparse(b)
        if va > vb:
            return 1
        if va < vb:
            return -1
        return 0
    except Exception:
        # heurística: split por non-digit, comparar componentes inteiros onde possível
        def parts(x):
            nums = re.findall(r'\d+', x)
            return [int(n) for n in nums] if nums else [0]
        pa = parts(a)
        pb = parts(b)
        # comparar componente por componente
        for i in range(max(len(pa), len(pb))):
            ai = pa[i] if i < len(pa) else 0
            bi = pb[i] if i < len(pb) else 0
            if ai > bi:
                return 1
            if ai < bi:
                return -1
        return 0

# --------------------------
# Upstream scraping helpers
# --------------------------
def _get_page(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, timeout=HTTP_TIMEOUT, headers=headers)
    resp.raise_for_status()
    return resp.text

def _versions_from_github(url: str) -> list:
    """
    Tenta detectar versões usando GitHub releases API ou páginas GitHub.
    url: pode ser repo homepage (https://github.com/owner/repo) ou releases page.
    """
    # extrair owner/repo
    m = re.match(r'https?://github.com/([^/]+/[^/]+)', url)
    if not m:
        return []
    repo = m.group(1).rstrip('/')
    api_url = f"https://api.github.com/repos/{repo}/releases"
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(api_url, timeout=HTTP_TIMEOUT, headers=headers)
        r.raise_for_status()
        data = r.json()
        versions = []
        for rel in data:
            tag = rel.get("tag_name")
            if tag:
                versions.append(_normalize_version(str(tag)))
        return versions
    except Exception:
        # fallback scraping releases page
        try:
            page = _get_page(f"https://github.com/{repo}/releases")
            soup = BeautifulSoup(page, "html.parser")
            texts = [a.text for a in soup.find_all("a")]
            candidates = []
            for t in texts:
                candidates.extend(_parse_version_candidates(t))
            return [_normalize_version(x) for x in candidates]
        except Exception:
            return []

def _versions_from_generic_page(url: str, name: str = None) -> list:
    """
    Scrape genérico: busca links e textos que contenham padrões de versão.
    """
    try:
        page = _get_page(url)
    except Exception as e:
        log.debug(f"Falha ao buscar upstream page {url}: {e}")
        return []
    soup = BeautifulSoup(page, "html.parser")
    candidates = []
    # links
    for a in soup.find_all("a"):
        txt = (a.get("href") or "") + " " + (a.text or "")
        candidates.extend(_parse_version_candidates(txt))
    # metas: buscar textos visíveis
    texts = soup.stripped_strings
    for t in texts:
        candidates.extend(_parse_version_candidates(t))
    # filtrar e normalizar
    cleaned = sorted(set([_normalize_version(c) for c in candidates if c and len(c) > 0]))
    return cleaned

def get_latest_version_from_meta(meta: MetaPackage) -> Optional[str]:
    """
    Determina a versão mais recente upstream para o meta:
    - Tenta GitHub API se upstream_url aponta para github
    - Senão, faz scraping genérico da página upstream_url
    - Retorna a versão mais alta detectada, ou None se não foi possível detectar.
    """
    url = meta.upstream_url
    if not url:
        return None
    name = meta.name
    versions = []
    try:
        if "github.com" in url:
            versions = _versions_from_github(url)
        else:
            versions = _versions_from_generic_page(url, name)
    except Exception as e:
        log.debug(f"Erro ao obter versões upstream para {name}: {e}")
        return None
    if not versions:
        return None
    # escolher a melhor versão (a maior segundo our compare)
    latest = versions[0]
    for v in versions[1:]:
        try:
            if _version_cmp(v, latest) == 1:
                latest = v
        except Exception:
            pass
    return latest

# --------------------------
# Priority classification (heurística)
# --------------------------
def classify_priority(meta: MetaPackage, upstream_version: str, release_notes: str = None) -> str:
    """
    Retorna uma prioridade heurística: 'critical', 'urgent', 'normal'.
    - Se meta.priority existir, usar ela.
    - Se release_notes mencionar 'security' ou 'CVE' => critical.
    - Caso contrário 'normal'.
    """
    if meta.priority:
        return meta.priority
    text = (release_notes or "").lower()
    if "security" in text or "cve" in text or "vulnerability" in text:
        return "critical"
    return "normal"

# --------------------------
# Save new meta helper (usa MetaPackage.save_to_base + save_to_available)
# --------------------------
def save_new_meta(meta_obj: MetaPackage, upstream_ver: str) -> str:
    """
    Ajusta meta_obj.data['version']=upstream_ver, salva novo .meta em /base/<name>/<name>-<ver>.meta
    e atualiza db/available/<name>.yaml. Retorna caminho do novo .meta criado.
    """
    meta_obj.data["version"] = upstream_ver
    # salvar na base (cria arquivo .meta)
    new_meta_path = meta_obj.save_to_base(upstream_ver)
    # salvar no db/available
    meta_obj.save_to_available()
    return new_meta_path

# --------------------------
# Main update check
# --------------------------
def update_check(packages: list = None):
    """
    Checa atualizações para os pacotes.
    - Se 'packages' for None: varre repo_base (base/*) e db/available.
    - Retorna lista de updates detectados (cada item é dict com name, current, upstream, priority, meta_path).
    """
    repo_base = CONFIG.get("repo_base", "base")
    db_dir = CONFIG.get("db_dir", "db")
    os.makedirs(db_dir, exist_ok=True)

    # coletar pacotes: nomes
    pkg_names = set()

    # a) do repo_base: cada diretório sob base é um pacote
    if os.path.isdir(repo_base):
        for name in os.listdir(repo_base):
            if os.path.isdir(os.path.join(repo_base, name)):
                pkg_names.add(name)

    # b) do db/available
    avail_dir = os.path.join(db_dir, "available")
    if os.path.isdir(avail_dir):
        for f in os.listdir(avail_dir):
            if f.endswith(".yaml") or f.endswith(".yml"):
                pkg_names.add(os.path.splitext(f)[0])

    if packages:
        for p in packages:
            pkg_names.add(p)

    updates = []
    for name in sorted(pkg_names):
        try:
            meta_obj = MetaPackage.load_from_base_latest(name) or MetaPackage(os.path.join(avail_dir, f"{name}.yaml"))
        except Exception as e:
            log.debug(f"Não foi possível carregar meta de {name}: {e}")
            continue
        if not meta_obj:
            continue
        current_ver = meta_obj.version
        upstream_url = meta_obj.upstream_url
        if not upstream_url:
            log.debug(f"{name} não tem upstream_url; pulando.")
            continue

        log.info(f"Verificando upstream para {name} (atualmente {current_ver})")
        try:
            latest = get_latest_version_from_meta(meta_obj)
        except Exception as e:
            log.warn(f"Erro ao checar upstream para {name}: {e}")
            latest = None

        if not latest:
            log.debug(f"Nenhuma versão detectada upstream para {name}")
            continue

        if _version_cmp(latest, current_ver) == 1:
            # nova versão encontrada
            log.success(f"Update detectado: {name} {current_ver} → {latest}")
            # classificação de prioridade (heurstica)
            priority = classify_priority(meta_obj, latest)
            # salvar novo meta em /base e atualizar db/available
            new_meta_path = save_new_meta(meta_obj, latest)
            updates.append({
                "name": name,
                "current": current_ver,
                "upstream": latest,
                "priority": priority,
                "upstream_url": upstream_url,
                "new_meta_path": new_meta_path,
                "checked_at": datetime.utcnow().isoformat()
            })
        else:
            log.info(f"{name} já está atualizado ({current_ver})")

    # salvar relatórios
    report_file, summary_file, bar_file = _get_paths()
    with open(report_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(updates, f, sort_keys=False)

    # resumo para o bar (contagem por prioridade)
    summary = {"critical": 0, "urgent": 0, "normal": 0}
    for u in updates:
        p = u.get("priority", "normal")
        if p not in summary:
            summary[p] = summary.get(p, 0) + 1
        else:
            summary[p] += 1

    with open(summary_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(summary, f, sort_keys=False)

    # também gerar JSON compacto para bar UI
    try:
        with open(bar_file, "w", encoding="utf-8") as f:
            json.dump(summary, f)
    except Exception as e:
        log.debug(f"Falha ao escrever bar file: {e}")

    # notificação desktop
    if updates:
        total = len(updates)
        msg = f"{total} updates disponíveis — críticos: {summary.get('critical',0)}, urgentes: {summary.get('urgent',0)}, normais: {summary.get('normal',0)}"
        notify_cmd = CONFIG.get("notify_cmd", "notify-send")
        try:
            # apenas dispara se notify-send estiver no PATH
            import shutil
            if shutil.which(notify_cmd):
                subprocess.run([notify_cmd, "Zeropkg - Updates", msg])
            else:
                log.info(f"[notify] {msg}")
        except Exception as e:
            log.debug(f"Falha ao enviar notificação: {e}")

    log.info(f"Relatório gerado: {report_file}, resumo: {summary_file}")
    return updates
