# Zeropkg/zeropkg1.0/modules/commands.py
"""
CLI principal do Zeropkg - implementa os comandos do Roadmap.
Este arquivo supõe que os módulos (core, meta, fetch, build, package, update, sync, system, sandbox, hooks, languages, deps, toolchain)
existem na mesma pasta e expõem funções compatíveis. O CLI é tolerante a módulos/funções ausentes.
"""

import argparse
import sys
import os
import importlib
from typing import Optional

# importar utilitários centrais
try:
    from core import CONFIG, log, run_cmd
except Exception:
    # fallback mínimo para permitir execução parcial
    CONFIG = {}
    def run_cmd(cmd, cwd=None, env=None, check=True):
        return None
    class _FakeLog:
        def info(self, *a, **k): print(*a)
        def warn(self, *a, **k): print(*a)
        def warning(self, *a, **k): print(*a)
        def error(self, *a, **k): print(*a, file=sys.stderr)
        def debug(self, *a, **k): print(*a)
        def success(self, *a, **k): print(*a)
    log = _FakeLog()

# util: import modular e tolerante
def safe_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception as e:
        log.debug(f"[IMPORT] módulo {name} indisponível: {e}")
        return None

# importar módulos (podem ser None se faltarem)
meta_mod = safe_import("meta")
fetch_mod = safe_import("fetch")
build_mod = safe_import("build")
package_mod = safe_import("package")
update_mod = safe_import("update")
upgrade_mod = safe_import("upgrade")
sync_mod = safe_import("sync")
system_mod = safe_import("system")
sandbox_mod = safe_import("sandbox")
hooks_mod = safe_import("hooks")
languages_mod = safe_import("languages")
deps_mod = safe_import("deps")
toolchain_mod = safe_import("toolchain")

# -------------------------
# Helpers
# -------------------------
def apply_global_args_to_config(args):
    """Mapeia flags globais para CONFIG (jobs, verbose, dry-run, ask, etc)."""
    if not isinstance(CONFIG, dict):
        return
    if getattr(args, "jobs", None) is not None:
        CONFIG["jobs"] = args.jobs
    if getattr(args, "load_average", None) is not None:
        CONFIG["load_average"] = args.load_average
    # flags booleanas
    if getattr(args, "ask", False):
        CONFIG["ask"] = True
    if getattr(args, "dry_run", False):
        CONFIG["dry_run"] = True
    if getattr(args, "pretend", False):
        CONFIG["pretend"] = True
    if getattr(args, "keep_going", False):
        CONFIG["keep_going"] = True
    if getattr(args, "nodeps", False):
        CONFIG["nodeps"] = True
    if getattr(args, "verbose", False):
        CONFIG["verbose"] = True
    if getattr(args, "quiet", False):
        CONFIG["quiet"] = True

def confirm_if_needed(prompt="Continuar? [y/N] "):
    """Se --ask estiver setado, pergunta; respeita --dry-run e --pretend."""
    if isinstance(CONFIG, dict) and CONFIG.get("dry_run"):
        log.info("[DRY-RUN] confirmação automática (dry-run)")
        return False  # não prosseguir em dry-run
    if isinstance(CONFIG, dict) and CONFIG.get("pretend"):
        log.info("[PRETEND] não executando ação (pretend)")
        return False
    if isinstance(CONFIG, dict) and CONFIG.get("ask"):
        ans = input(prompt)
        return ans.strip().lower().startswith("y")
    return True

def find_meta_by_name(name: str) -> Optional[str]:
    """Procura o .meta (mais recente) em repo base, ou no db/available. Retorna path ou None."""
    base = CONFIG.get("repo_base", "base")
    # 1) procura em base/<name> por arquivos *.meta ordenados (ex: name-version.meta)
    candidate_dir = os.path.join(base, name)
    if os.path.isdir(candidate_dir):
        # ordenar por nome (simples) — o mais novo normalmente vem por versão no nome
        files = sorted([f for f in os.listdir(candidate_dir) if f.endswith(".meta")])
        if files:
            return os.path.join(candidate_dir, files[-1])
    # 2) fallback: db/available/<name>.yaml
    db_av = os.path.join(CONFIG.get("db_dir", "db"), "available", f"{name}.yaml")
    if os.path.exists(db_av):
        return db_av
    return None

def load_meta_from_path(path: str):
    """Carrega um MetaPackage ou raw YAML conforme módulo meta presente."""
    if meta_mod and hasattr(meta_mod, "load_meta"):
        try:
            return meta_mod.load_meta(path)
        except Exception as e:
            log.debug(f"meta.load_meta falhou para {path}: {e}")
    # fallback: tentar ler YAML bruto
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        log.error(f"Não foi possível carregar meta {path}: {e}")
        return None

# -------------------------
# Handlers dos comandos
# -------------------------
def cmd_install(args):
    """install <meta|nome>"""
    apply_global_args_to_config(args)
    meta_path = args.meta
    # se não for caminho, tenta localizar por nome
    if not os.path.exists(meta_path):
        candidate = find_meta_by_name(meta_path)
        if candidate:
            meta_path = candidate
            log.info(f"Usando meta encontrado: {meta_path}")
        else:
            log.error(f"Meta não encontrado para '{args.meta}'")
            return
    meta = load_meta_from_path(meta_path)
    if not meta:
        log.error("Falha ao carregar meta.")
        return

    if CONFIG.get("dry_run") or CONFIG.get("pretend"):
        log.info("[DRY-RUN/PRETEND] Simulação de install concluída.")
        return

    # 1. fetch
    if fetch_mod and hasattr(fetch_mod, "fetch_sources"):
        try:
            fetch_mod.fetch_sources(meta, CONFIG.get("build_dir"))
        except Exception as e:
            log.warn(f"fetch_sources falhou: {e}")
    else:
        # tentativa simples: baixar a primeira source se existir
        try:
            sources = meta.data.get("sources") if hasattr(meta, "data") else meta.get("sources", [])
            if sources:
                src = sources[0]
                url = src.get("url") if isinstance(src, dict) else src
                if fetch_mod and hasattr(fetch_mod, "download_file"):
                    fetch_mod.download_file(url)
                else:
                    run_cmd(f"curl -L -O {url}")
        except Exception as e:
            log.debug(f"fetch fallback falhou: {e}")

    # 2. build
    if build_mod and hasattr(build_mod, "build_package"):
        try:
            # build_package espera objeto meta ou path dependendo da implementação
            build_mod.build_package(meta, CONFIG.get("build_dir"))
        except Exception as e:
            log.error(f"Erro no build: {e}")
            return
    else:
        log.warn("build_module não disponível; pulando etapa de build (verifique módulos).")

    # 3. install (via package module)
    if package_mod and hasattr(package_mod, "install"):
        try:
            staging_dir = CONFIG.get("staging_dir", os.path.join(CONFIG.get("build_dir", "/var/tmp"), "staging"))
            package_mod.install(meta, os.path.join(CONFIG.get("build_dir"), f"{meta.name}-{meta.version}"), staging_dir)
        except Exception as e:
            log.error(f"Erro na instalação: {e}")
    elif package_mod and hasattr(package_mod, "install_package"):
        try:
            package_mod.install_package(meta, CONFIG.get("install_dir"))
        except Exception as e:
            log.error(f"Erro na instalação: {e}")
    else:
        log.error("Módulo package não disponível ou sem função de instalação.")

def cmd_remove(args):
    """remove nome  ou nome=versão"""
    apply_global_args_to_config(args)
    target = args.pkg
    # suporte nome=versão
    if "=" in target:
        name, version = target.split("=",1)
        # tentar remover versão específica do repo/instalação
        # procurar manifesto por nome-version
        manifest_path = os.path.join(CONFIG.get("db_dir","db"), "installed", f"{name}-{version}.yaml")
        if os.path.exists(manifest_path):
            # usar package.remove se existir
            if package_mod and hasattr(package_mod, "remove"):
                package_mod.remove(name + "-" + version)
            elif package_mod and hasattr(package_mod, "remove_package"):
                package_mod.remove_package(name + "-" + version)
            else:
                log.error("Função de remoção não encontrada no módulo package.")
        else:
            # fallback: remover por nome simples
            if package_mod and hasattr(package_mod, "remove"):
                package_mod.remove(name)
            else:
                log.error(f"Manifesto {manifest_path} não encontrado e função de remoção ausente.")
    else:
        # remover sem versão -> invoca package.remove(nome)
        if package_mod and hasattr(package_mod, "remove"):
            package_mod.remove(target)
        elif package_mod and hasattr(package_mod, "remove_package"):
            package_mod.remove_package(target)
        else:
            log.error("Função de remoção não encontrada no módulo package.")

def cmd_set(args):
    """set nome=versão  -> define versão ativa (toolchain/lang)"""
    apply_global_args_to_config(args)
    if "=" not in args.pkg:
        log.error("Use o formato nome=versão")
        return
    name, version = args.pkg.split("=",1)
    # procurar meta no base
    base_meta = os.path.join(CONFIG.get("repo_base","base"), name, f"{name}-{version}.meta")
    if not os.path.exists(base_meta):
        log.error(f"Meta {base_meta} não encontrado.")
        return
    # copiar para db/available/<name>.yaml
    try:
        import shutil, yaml
        with open(base_meta) as f:
            meta_raw = yaml.safe_load(f)
        avail_dir = os.path.join(CONFIG.get("db_dir","db"), "available")
        os.makedirs(avail_dir, exist_ok=True)
        out_av = os.path.join(avail_dir, f"{name}.yaml")
        with open(out_av, "w") as f:
            yaml.safe_dump(meta_raw, f)
        # opcional: criar symlink em toolchain dir para marcar como ativo
        tool_dir = CONFIG.get("toolchain_dir")
        if tool_dir:
            os.makedirs(tool_dir, exist_ok=True)
            # criar arquivo marker active-version
            marker = os.path.join(tool_dir, f"{name}.active")
            with open(marker, "w") as m:
                m.write(version)
        log.success(f"{name} setado para {version} (ativo).")
    except Exception as e:
        log.error(f"Falha ao setar versão: {e}")

def cmd_recompile(args):
    """recompile/rebuild/recompila nome"""
    apply_global_args_to_config(args)
    name = args.pkg
    # carregar meta do available (versão ativa) ou do base
    meta_path = find_meta_by_name(name)
    if not meta_path:
        log.error(f"Meta para {name} não encontrada.")
        return
    meta = load_meta_from_path(meta_path)
    if not meta:
        log.error("Falha ao carregar meta.")
        return
    # run build + install (recompila e reinstala)
    if build_mod and hasattr(build_mod, "build_package"):
        build_mod.build_package(meta, CONFIG.get("build_dir"))
    if package_mod and hasattr(package_mod, "install"):
        staging = CONFIG.get("staging_dir", os.path.join(CONFIG.get("build_dir","/var/tmp"), "staging"))
        package_mod.install(meta, os.path.join(CONFIG.get("build_dir"), f"{meta.name}-{meta.version}"), staging)
    log.success(f"Recompilação de {name} finalizada.")

def cmd_update(args):
    """update (-u) -> checar upstreams, gerar report, atualizar /base com novos .meta"""
    apply_global_args_to_config(args)
    if update_mod and hasattr(update_mod, "update_check"):
        updates = update_mod.update_check()
        if updates:
            log.info(f"{len(updates)} updates encontrados.")
        else:
            log.info("Nenhum update encontrado.")
    else:
        log.error("Módulo update não disponível (ou update_check não implementado).")

def cmd_sync(args):
    """sync -> sincroniza repo de receitas (git pull/push)"""
    apply_global_args_to_config(args)
    if sync_mod and hasattr(sync_mod, "sync_repo"):
        sync_mod.sync_repo()
    else:
        log.error("sync não disponível (verifique sync module).")

def cmd_revdep_rebuild(args):
    """revdep-rebuild -> reconstrói pacotes órfãos / quebrados (placeholder)"""
    apply_global_args_to_config(args)
    if deps_mod and hasattr(deps_mod, "revdep_rebuild"):
        deps_mod.revdep_rebuild(args)
    else:
        log.warn("revdep-rebuild não implementado no módulo deps. Comportamento placeholder.")
        # placeholder simples: listar pacotes e avisar
        if system_mod and hasattr(system_mod, "list_installed"):
            pkgs = system_mod.list_installed()
            log.info(f"Pacotes instalados: {len(pkgs) if pkgs else 0}")

def cmd_glsa_check(args):
    """glsa-check -t|-f|-p  (listar / corrige / simula)"""
    apply_global_args_to_config(args)
    mode = "list"
    if args.fix:
        mode = "fix"
    if args.pretend:
        mode = "pretend"
    if system_mod and hasattr(system_mod, "glsa_check"):
        system_mod.glsa_check(mode, args.target)
    else:
        log.warn("glsa-check não implementado. Se desejar, implemente system.glsa_check(mode, target).")

def cmd_quickpkg(args):
    """quickpkg: cria pacote binário a partir de staging/build"""
    apply_global_args_to_config(args)
    if package_mod and hasattr(package_mod, "create_package"):
        # espera meta ou nome
        meta_path = args.meta
        if not os.path.exists(meta_path):
            meta_path = find_meta_by_name(meta_path) or meta_path
        meta = load_meta_from_path(meta_path)
        if meta:
            staging_dir = CONFIG.get("staging_dir", os.path.join(CONFIG.get("build_dir","/var/tmp"), "staging"))
            destdir = os.path.join(CONFIG.get("build_dir", f"{meta.name}-{meta.version}"), "pkgroot")
            package_mod.create_package(meta, staging_dir, destdir)
    else:
        log.warn("create_package/quickpkg não implementado no módulo package.")

def cmd_search(args):
    """search / info"""
    apply_global_args_to_config(args)
    term = args.term
    # procurar em db/available
    avail_dir = os.path.join(CONFIG.get("db_dir","db"), "available")
    results = []
    if os.path.isdir(avail_dir):
        import yaml
        for root,_,files in os.walk(avail_dir):
            for f in files:
                if f.endswith(".yaml") or f.endswith(".yml"):
                    path = os.path.join(root,f)
                    try:
                        with open(path) as fh:
                            md = yaml.safe_load(fh)
                            name = md.get("name","")
                            desc = md.get("description","")
                            if term.lower() in name.lower() or (term.lower() in (desc or "").lower()):
                                results.append((name, md.get("version"), path))
                    except Exception:
                        continue
    for r in results:
        print(f"{r[0]} {r[1]}  ({r[2]})")
    if not results:
        log.info("Nenhum pacote encontrado.")

def cmd_info(args):
    apply_global_args_to_config(args)
    pkg = args.pkg
    path = find_meta_by_name(pkg) or os.path.join(CONFIG.get("db_dir","db"), "available", f"{pkg}.yaml")
    if not os.path.exists(path):
        log.error(f"Meta/info de {pkg} não encontrado.")
        return
    meta = load_meta_from_path(path)
    import yaml, json
    if isinstance(meta, dict):
        print(yaml.safe_dump(meta))
    else:
        # MetaPackage objeto
        try:
            print(meta.data)
        except Exception:
            print(meta)

def cmd_doctor(args):
    apply_global_args_to_config(args)
    if system_mod and hasattr(system_mod, "doctor"):
        system_mod.doctor(args)
    else:
        log.warn("doctor não implementado no módulo system. Use system.doctor implementado para varredura completa.")

def cmd_clean(args):
    apply_global_args_to_config(args)
    target = args.target or "all"  # options: build, sandbox, logs, prefix, all
    # chamar funções de clean se existirem
    cleaned = False
    if build_mod and hasattr(build_mod, "clean_sandbox"):
        if target in ("sandbox","all"):
            build_mod.clean_sandbox("*")
            cleaned = True
    if package_mod and hasattr(package_mod, "clean"):
        if target in ("build","all"):
            package_mod.clean()
            cleaned = True
    if not cleaned:
        log.info(f"clean: ação '{target}' executada (placeholder)")

def cmd_list(args):
    apply_global_args_to_config(args)
    if system_mod and hasattr(system_mod, "list_installed"):
        system_mod.list_installed()
    else:
        # fallback: listar dir install_dir
        inst = CONFIG.get("install_dir")
        if inst and os.path.isdir(inst):
            for d in os.listdir(inst):
                print(d)
        else:
            log.info("Nenhum pacote instalado encontrado (lista vazia).")

def cmd_available(args):
    apply_global_args_to_config(args)
    # list available in db/available or base
    avail_dir = os.path.join(CONFIG.get("db_dir","db"), "available")
    if os.path.isdir(avail_dir):
        for f in sorted(os.listdir(avail_dir)):
            if f.endswith(".yaml") or f.endswith(".yml"):
                print(f)
    else:
        log.info("Nenhum pacote disponível (db/available vazio).")

# -------------------------
# Construção do parser com as opções do roadmap
# -------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="zeropkg", description="Zeropkg package manager (Roadmap CLI)")
    # flags globais
    p.add_argument("-a", "--ask", action="store_true", help="Perguntar antes de executar (ask).")
    p.add_argument("--dry-run", action="store_true", help="Simular sem executar ações.")
    p.add_argument("-p", "--pretend", action="store_true", help="Sinônimo de dry-run / pretend.")
    p.add_argument("-j", "--jobs", type=int, help="Número de jobs paralelos.")
    p.add_argument("-l", "--load-average", type=float, dest="load_average", help="Limite de load-average.")
    p.add_argument("--keep-going", action="store_true", help="Continuar mesmo após erros.")
    p.add_argument("--resume", action="store_true", help="Retomar última compilação interrompida.")
    p.add_argument("--nodeps", action="store_true", help="Ignorar dependências.")
    p.add_argument("--quiet", action="store_true", help="Menos saída.")
    p.add_argument("-v", "--verbose", action="store_true", help="Saída detalhada.")
    sub = p.add_subparsers(dest="command", required=True)

    # install
    pi = sub.add_parser("install", help="Instalar pacote (meta path ou nome)")
    pi.add_argument("meta", help="Arquivo .meta/.yaml do pacote ou nome do pacote")
    pi.set_defaults(func=cmd_install)

    # remove
    pr = sub.add_parser("remove", help="Remover pacote (nome ou nome=versão)")
    pr.add_argument("pkg", help="nome ou nome=versão")
    pr.set_defaults(func=cmd_remove)

    # set
    ps = sub.add_parser("set", help="Definir versão ativa (nome=versão)")
    ps.add_argument("pkg", help="nome=versão")
    ps.set_defaults(func=cmd_set)

    # recompile / rebuild / recompila
    prc = sub.add_parser("recompile", help="Recompilar pacote existente")
    prc.add_argument("pkg", help="nome do pacote")
    prc.set_defaults(func=cmd_recompile)

    # update (upstream check)
    pu = sub.add_parser("update", help="Checar novas versões upstream e gerar relatórios")
    pu.set_defaults(func=cmd_update)

    # sync (repo)
    psync = sub.add_parser("sync", help="Sincronizar repositório de receitas (git pull/push)")
    psync.set_defaults(func=cmd_sync)

    # revdep-rebuild
    prev = sub.add_parser("revdep-rebuild", help="Reconstruir pacotes que dependem de libs quebradas")
    prev.add_argument("--pretend", action="store_true", help="Simular apenas")
    prev.set_defaults(func=cmd_revdep_rebuild)

    # glsa-check
    pglsa = sub.add_parser("glsa-check", help="Checar/corrigir pacotes vulneráveis (GLSA-like)")
    pglsa.add_argument("-t", "--test", action="store_true", help="Testar e listar")
    pglsa.add_argument("-f", "--fix", action="store_true", help="Fix (aplicar correções)")
    pglsa.add_argument("-p", "--pretend", action="store_true", help="Simular")
    pglsa.add_argument("target", nargs="?", default="all", help="Alvo (all, pacote...)")
    pglsa.set_defaults(func=cmd_glsa_check)

    # quickpkg
    pq = sub.add_parser("quickpkg", help="Criar pacote binário a partir do build/staging")
    pq.add_argument("meta", help="meta path ou nome")
    pq.set_defaults(func=cmd_quickpkg)

    # search / info
    psrch = sub.add_parser("search", help="Procurar pacotes por nome/descrição")
    psrch.add_argument("term", help="Termo de busca")
    psrch.set_defaults(func=cmd_search)

    pinfo = sub.add_parser("info", help="Mostrar info do pacote/meta")
    pinfo.add_argument("pkg", help="Nome do pacote")
    pinfo.set_defaults(func=cmd_info)

    # doctor
    pdoc = sub.add_parser("doctor", help="Rodar checagens de sistema (doctor)")
    pdoc.set_defaults(func=cmd_doctor)

    # clean
    pclean = sub.add_parser("clean", help="Limpar diretórios: build, sandbox, logs, prefix")
    pclean.add_argument("target", nargs="?", choices=["build","sandbox","logs","prefix","all"], default="all")
    pclean.set_defaults(func=cmd_clean)

    # list / available
    pl = sub.add_parser("list", help="Listar pacotes instalados")
    pl.set_defaults(func=cmd_list)

    pav = sub.add_parser("available", help="Listar pacotes disponíveis")
    pav.set_defaults(func=cmd_available)

    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        log.error("Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        log.error(f"Erro ao executar comando: {e}")
        if not CONFIG.get("keep_going"):
            sys.exit(1)

if __name__ == "__main__":
    main()
