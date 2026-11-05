#!/usr/bin/env python3
"""
Mind — Gerador do Grafo de Código

Roda ANTES da skill (chamado pelo mind-stage.py) para produzir um grafo de
código estruturado do repositório alvo. Os arquivos de saída ficam em .mind/_global/
e são lidos pelo agente durante as tarefas onboard-repo / update-repo.

Linguagens suportadas: Java, Python, TypeScript, JavaScript
Profundidade da análise:
  Java
  - Todas as classes / interfaces / enums com pacote, anotações e campos
  - Assinaturas de métodos com tipos de parâmetro, tipo de retorno e anotações
  - Grafo aproximado de chamadas dentro do repo (métodos chamados por cada método)
  - Topologia de listeners Kafka  (tópicos do @KafkaListener)
  - Mapa de endpoints REST        (@GetMapping / @PostMapping etc.)
  - Tarefas agendadas             (@Scheduled)
  TypeScript / JavaScript
  - Classes com decorators (Angular @Component, @Injectable, @NgModule, @Pipe, @Directive)
  - Interfaces e type aliases
  - Componentes React / funções standalone
  - Array de Routes do Angular
  - Chamadas de cliente HTTP (HttpClient / axios / fetch)
  Python
  - Classes, métodos, decorators
  - Decorators de rota FastAPI / Flask (@app.get, @router.post etc.)
  - Decorators de tarefa Celery (@celery.task, @shared_task)

Saída:
  .mind/_global/code-graph.json     grafo legível por máquina
  .mind/_global/code-graph.md       resumo em Markdown formatado para o agente
  .mind/context/code-graph.md       cópia commitada (pulada se não houver arquivos analisáveis ou se nada mudou)

Uso:
  python3 mind-code-graph.py [raiz-do-repo]   (padrão: diretório atual)
"""

import sys, os, json, subprocess, re, tempfile
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Mensagens em pt-BR: força UTF-8 na saída (no Windows, a saída redirecionada usa cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
GLOBAL_DIR = REPO_ROOT / ".mind" / "_global"
GLOBAL_DIR.mkdir(parents=True, exist_ok=True)

MAX_CALL_DEPTH = 50    # máximo de chamadas registradas por método

# ── 1. Instalar dependências ──────────────────────────────────────────────────

_PKGS_DIR = os.path.join(tempfile.gettempdir(), "_tree_sitter_pkgs")  # portável (Windows/Linux/macOS)

def install_deps():
    pkgs = [
        "tree-sitter>=0.24.0",  # 0.24+ é exigido pela ABI 15 de linguagem usada pelos pacotes de gramática atuais
        "tree-sitter-java",
        "tree-sitter-python",
        "tree-sitter-javascript",
        "tree-sitter-typescript",
    ]
    print("Instalando as dependências do tree-sitter...", flush=True)
    Path(_PKGS_DIR).mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade",
         "--target", _PKGS_DIR] + pkgs,
        check=True,
    )
    # Torna os pacotes recém-instalados visíveis para o processo atual.
    if _PKGS_DIR not in sys.path:
        sys.path.insert(0, _PKGS_DIR)
    import importlib
    importlib.invalidate_caches()

try:
    import tree_sitter
    _ver_str = getattr(tree_sitter, "__version__", "0.0.0")
    ver = tuple(int(x) for x in _ver_str.split(".")[:2])
    if ver < (0, 24):
        raise ImportError(f"tree-sitter {_ver_str} antigo demais — é preciso >=0.24.0")
    import tree_sitter_java as _tsjava
    import tree_sitter_python as _tspython
    import tree_sitter_javascript as _tsjs
    import tree_sitter_typescript as _tsts
except (ImportError, ModuleNotFoundError):
    install_deps()
    import tree_sitter
    import tree_sitter_java as _tsjava
    import tree_sitter_python as _tspython
    import tree_sitter_javascript as _tsjs
    import tree_sitter_typescript as _tsts

from tree_sitter import Language, Parser, Node

JAVA_LANG = Language(_tsjava.language())
PY_LANG   = Language(_tspython.language())
JS_LANG   = Language(_tsjs.language())
TSX_LANG  = Language(_tsts.language_tsx())
TS_LANG   = Language(_tsts.language_typescript())

def make_parser(lang: Language) -> Parser:
    p = Parser(lang)
    return p

PARSERS = {
    ".java": make_parser(JAVA_LANG),
    ".py":   make_parser(PY_LANG),
    ".ts":   make_parser(TS_LANG),
    ".tsx":  make_parser(TSX_LANG),
    ".js":   make_parser(JS_LANG),
    ".jsx":  make_parser(JS_LANG),
}

# ── 2. Utilitários de travessia da AST ─────────────────────────────────────────────

def node_text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()

def child_by_type(node: Node, *types: str) -> Node | None:
    for child in node.children:
        if child.type in types:
            return child
    return None

def children_by_type(node: Node, *types: str) -> list[Node]:
    return [c for c in node.children if c.type in types]

def find_all(node: Node, *types: str) -> list[Node]:
    """Coleta em profundidade todos os nós dos tipos informados."""
    result = []
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in types:
            result.append(n)
        stack.extend(reversed(n.children))
    return result

def find_first(node: Node, *types: str) -> Node | None:
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in types:
            return n
        stack.extend(reversed(n.children))
    return None

# ── 3. Análise Java ──────────────────────────────────────────────────────────

def _java_annotation_text(ann_node: Node, src: bytes) -> str:
    """Retorna a anotação como string '@Nome' ou '@Nome(...)'."""
    return "@" + node_text(ann_node, src).lstrip("@")

def _java_annotations(node: Node, src: bytes) -> list[str]:
    mods = child_by_type(node, "modifiers")
    if not mods:
        return []
    return [_java_annotation_text(a, src) for a in find_all(mods, "annotation", "marker_annotation")]

def _java_modifiers(node: Node, src: bytes) -> list[str]:
    mods = child_by_type(node, "modifiers")
    if not mods:
        return []
    return [node_text(c, src) for c in mods.children
            if c.type not in ("annotation", "marker_annotation", "comment")]

def _java_type_name(type_node: Node, src: bytes) -> str:
    if type_node is None:
        return "void"
    return node_text(type_node, src)

def _java_formal_params(params_node: Node, src: bytes) -> list[dict]:
    params = []
    for fp in find_all(params_node, "formal_parameter", "spread_parameter"):
        type_node = child_by_type(fp, "type_identifier", "void_type",
                                   "integral_type", "floating_point_type",
                                   "boolean_type", "array_type", "generic_type",
                                   "scoped_type_identifier")
        name_node = child_by_type(fp, "variable_declarator_id", "identifier")
        params.append({
            "type": _java_type_name(type_node, src) if type_node else "?",
            "name": node_text(name_node, src) if name_node else "?",
        })
    return params

def _java_method_callees(body_node: Node, src: bytes) -> list[str]:
    """Chamadas aproximadas: todos os nomes de method_invocation no corpo de um método."""
    if body_node is None:
        return []
    seen, result = set(), []
    for inv in find_all(body_node, "method_invocation"):
        name_node = None
        for c in inv.children:
            if c.type == "identifier":
                name_node = c
            elif c.type == "argument_list":
                break
        obj_node = child_by_type(inv, "identifier", "field_access", "this")
        callee_parts = []
        if obj_node and obj_node != name_node:
            callee_parts.append(node_text(obj_node, src))
        if name_node:
            callee_parts.append(node_text(name_node, src))
        callee = ".".join(callee_parts) if callee_parts else ""
        if callee and callee not in seen:
            seen.add(callee)
            result.append(callee)
            if len(result) >= MAX_CALL_DEPTH:
                break
    return result

def _java_annotation_arg(ann_text: str, arg_name: str) -> list[str]:
    """Extrai os valores de argumento do texto da anotação, ex.: tópicos do @KafkaListener."""
    pattern = rf'{arg_name}\s*=\s*\{{([^}}]+)\}}|{arg_name}\s*=\s*"([^"]+)"'
    m = re.search(pattern, ann_text)
    if not m:
        return []
    if m.group(1):
        return [v.strip().strip('"') for v in m.group(1).split(",") if v.strip()]
    return [m.group(2)]

def analyze_java_file(filepath: Path, rel_path: str, src: bytes) -> dict | None:
    try:
        tree = PARSERS[".java"].parse(src)
    except Exception:
        return None

    result = {"file": rel_path, "types": []}

    # Deduz o pacote pelo caminho (confiável no layout padrão do Maven)
    pkg = ""
    parts = rel_path.replace("\\", "/").split("/")
    try:
        java_idx = parts.index("java")
        pkg = ".".join(parts[java_idx + 1:-1])
    except ValueError:
        pass

    # Extrai também todas as declarações de package
    for pkg_node in find_all(tree.root_node, "package_declaration"):
        pkg = node_text(pkg_node, src).replace("package ", "").rstrip(";").strip()

    def extract_type(type_node: Node, kind: str) -> dict:
        name_node = child_by_type(type_node, "identifier")
        name = node_text(name_node, src) if name_node else "?"
        annotations = _java_annotations(type_node, src)
        modifiers = _java_modifiers(type_node, src)

        # Superclasse / interfaces
        extends_list, implements_list = [], []
        sc = child_by_type(type_node, "superclass")
        if sc:
            extends_list.append(node_text(sc, src).replace("extends", "").strip())
        si = child_by_type(type_node, "super_interfaces")
        if si:
            for ti in find_all(si, "type_identifier"):
                implements_list.append(node_text(ti, src))

        # Campos
        fields = []
        body = child_by_type(type_node, "class_body", "interface_body", "enum_body")
        if body:
            for fd in children_by_type(body, "field_declaration"):
                f_anns = _java_annotations(fd, src)
                f_type = child_by_type(fd, "type_identifier", "void_type",
                                        "integral_type", "floating_point_type",
                                        "boolean_type", "array_type", "generic_type")
                f_type_str = _java_type_name(f_type, src) if f_type else "?"
                for vd in find_all(fd, "variable_declarator"):
                    f_name_node = child_by_type(vd, "identifier")
                    if f_name_node:
                        fields.append({
                            "name": node_text(f_name_node, src),
                            "type": f_type_str,
                            "annotations": f_anns,
                        })

        # Métodos
        methods = []
        if body:
            for md in find_all(body, "method_declaration", "constructor_declaration"):
                m_name_node = child_by_type(md, "identifier")
                m_name = node_text(m_name_node, src) if m_name_node else "?"
                m_anns = _java_annotations(md, src)
                m_mods = _java_modifiers(md, src)
                ret_type = child_by_type(md, "type_identifier", "void_type",
                                          "integral_type", "floating_point_type",
                                          "boolean_type", "array_type", "generic_type")
                params_node = child_by_type(md, "formal_parameters")
                params = _java_formal_params(params_node, src) if params_node else []
                body_node = child_by_type(md, "block")
                callees = _java_method_callees(body_node, src)

                param_str = ", ".join(f"{p['type']} {p['name']}" for p in params)
                ret_str = _java_type_name(ret_type, src) if ret_type and md.type == "method_declaration" else name
                sig = f"{ret_str} {m_name}({param_str})"

                methods.append({
                    "name": m_name,
                    "signature": sig,
                    "visibility": next((m for m in m_mods if m in ("public","protected","private")), "package"),
                    "annotations": m_anns,
                    "calls": callees,
                })

        qualified = f"{pkg}.{name}" if pkg else name
        return {
            "name": name,
            "qualified_name": qualified,
            "package": pkg,
            "kind": kind,
            "file": rel_path,
            "line": type_node.start_point[0] + 1,
            "annotations": annotations,
            "extends": extends_list,
            "implements": implements_list,
            "fields": fields,
            "methods": methods,
        }

    for node in find_all(tree.root_node, "class_declaration"):
        result["types"].append(extract_type(node, "class"))
    for node in find_all(tree.root_node, "interface_declaration"):
        result["types"].append(extract_type(node, "interface"))
    for node in find_all(tree.root_node, "enum_declaration"):
        result["types"].append(extract_type(node, "enum"))
    for node in find_all(tree.root_node, "annotation_type_declaration"):
        result["types"].append(extract_type(node, "annotation"))

    return result if result["types"] else None

# ── 4. Análise Python ────────────────────────────────────────────────────────

def analyze_python_file(filepath: Path, rel_path: str, src: bytes) -> dict | None:
    try:
        tree = PARSERS[".py"].parse(src)
    except Exception:
        return None

    result = {"file": rel_path, "types": []}

    for cls_node in find_all(tree.root_node, "class_definition"):
        name_node = child_by_type(cls_node, "identifier")
        name = node_text(name_node, src) if name_node else "?"

        # Classes base
        bases = []
        args_node = child_by_type(cls_node, "argument_list")
        if args_node:
            for arg in find_all(args_node, "identifier", "attribute"):
                bases.append(node_text(arg, src))

        # Decorators
        decorators = []
        for dec in find_all(cls_node, "decorator"):
            decorators.append(node_text(dec, src))

        # Métodos
        methods = []
        body = child_by_type(cls_node, "block")
        if body:
            for fn in find_all(body, "function_definition"):
                fn_name_node = child_by_type(fn, "identifier")
                fn_name = node_text(fn_name_node, src) if fn_name_node else "?"
                fn_params_node = child_by_type(fn, "parameters")
                fn_params = node_text(fn_params_node, src) if fn_params_node else "()"
                fn_decs = [node_text(d, src) for d in find_all(fn, "decorator")]

                # Métodos chamados
                fn_body = child_by_type(fn, "block")
                callees = []
                if fn_body:
                    for call in find_all(fn_body, "call"):
                        func_node = child_by_type(call, "identifier", "attribute")
                        if func_node:
                            callees.append(node_text(func_node, src))
                    callees = list(dict.fromkeys(callees))[:MAX_CALL_DEPTH]

                methods.append({
                    "name": fn_name,
                    "signature": f"{fn_name}{fn_params}",
                    "visibility": "public" if not fn_name.startswith("_") else "private",
                    "annotations": fn_decs,
                    "calls": callees,
                })

        result["types"].append({
            "name": name,
            "qualified_name": name,
            "package": str(Path(rel_path).parent).replace("/", ".").replace("\\", "."),
            "kind": "class",
            "file": rel_path,
            "line": cls_node.start_point[0] + 1,
            "annotations": decorators,
            "extends": bases,
            "implements": [],
            "fields": [],
            "methods": methods,
        })

    # Funções standalone com decorators — rotas FastAPI/Flask, tarefas Celery
    src_text = src.decode("utf-8", errors="replace")
    for m in re.finditer(
        r'(@(?:app|router|blueprint|celery|current_app)\.(?:get|post|put|delete|patch|route|task)|@shared_task|@app\.task)'
        r'[^)]*\)?\s*\ndef\s+([a-z_][a-zA-Z0-9_]*)',
        src_text, re.MULTILINE
    ):
        decorator_text = m.group(1)
        fn_name = m.group(2)
        result["types"].append({
            "name": fn_name,
            "qualified_name": fn_name,
            "package": str(Path(rel_path).parent).replace("/", ".").replace("\\", "."),
            "kind": "function",
            "file": rel_path,
            "line": src_text[:m.start()].count("\n") + 1,
            "annotations": [decorator_text],
            "extends": [],
            "implements": [],
            "fields": [],
            "methods": [],
        })

    return result if result["types"] else None

# ── 5. Análise TypeScript / JavaScript ──────────────────────────────────

def analyze_ts_file(filepath: Path, rel_path: str, src: bytes) -> dict | None:
    ext = filepath.suffix.lower()
    parser = PARSERS.get(ext, PARSERS[".ts"])
    try:
        tree = parser.parse(src)
    except Exception:
        return None

    result = {"file": rel_path, "types": []}

    # Declarações de classe
    for cls_node in find_all(tree.root_node, "class_declaration"):
        name_node = child_by_type(cls_node, "type_identifier", "identifier")
        name = node_text(name_node, src) if name_node else "?"

        # Decorators (Angular @Component, @Injectable etc.)
        decorators = []
        for dec in find_all(cls_node, "decorator"):
            decorators.append(node_text(dec, src).split("\n")[0][:80])

        # Herança
        extends_list, implements_list = [], []
        for clause in find_all(cls_node, "extends_clause", "class_heritage"):
            for ti in find_all(clause, "type_identifier", "identifier"):
                extends_list.append(node_text(ti, src))
        for clause in find_all(cls_node, "implements_clause"):
            for ti in find_all(clause, "type_identifier", "identifier"):
                implements_list.append(node_text(ti, src))

        # Métodos
        methods = []
        body = child_by_type(cls_node, "class_body")
        if body:
            for md in find_all(body, "method_definition", "public_field_definition"):
                mn_node = child_by_type(md, "property_identifier", "identifier")
                mn = node_text(mn_node, src) if mn_node else "?"
                m_decs = [node_text(d, src).split("\n")[0][:60]
                           for d in find_all(md, "decorator")]
                fn_body = find_first(md, "statement_block")
                callees = []
                if fn_body:
                    for call in find_all(fn_body, "call_expression"):
                        fn_node = child_by_type(call, "identifier", "member_expression")
                        if fn_node:
                            callees.append(node_text(fn_node, src)[:60])
                    callees = list(dict.fromkeys(callees))[:MAX_CALL_DEPTH]

                methods.append({
                    "name": mn,
                    "signature": mn,
                    "visibility": "public",
                    "annotations": m_decs,
                    "calls": callees,
                })

        result["types"].append({
            "name": name,
            "qualified_name": name,
            "package": str(Path(rel_path).parent).replace("\\", "/"),
            "kind": "class",
            "file": rel_path,
            "line": cls_node.start_point[0] + 1,
            "annotations": decorators,
            "extends": extends_list,
            "implements": implements_list,
            "fields": [],
            "methods": methods,
        })

    # Declarações de interface
    for iface_node in find_all(tree.root_node, "interface_declaration"):
        name_node = child_by_type(iface_node, "type_identifier", "identifier")
        name = node_text(name_node, src) if name_node else "?"
        extends_list = []
        for clause in find_all(iface_node, "extends_clause"):
            for ti in find_all(clause, "type_identifier", "identifier"):
                extends_list.append(node_text(ti, src))
        result["types"].append({
            "name": name,
            "qualified_name": name,
            "package": str(Path(rel_path).parent).replace("\\", "/"),
            "kind": "interface",
            "file": rel_path,
            "line": iface_node.start_point[0] + 1,
            "annotations": [],
            "extends": extends_list,
            "implements": [],
            "fields": [],
            "methods": [],
        })

    # Funções exportadas / componentes arrow standalone (React / Angular standalone)
    src_text = src.decode("utf-8", errors="replace")
    for m in re.finditer(
        r'export\s+(?:default\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9_]+)',
        src_text
    ):
        fn_name = m.group(1)
        result["types"].append({
            "name": fn_name,
            "qualified_name": fn_name,
            "package": str(Path(rel_path).parent).replace("\\", "/"),
            "kind": "function",
            "file": rel_path,
            "line": src_text[:m.start()].count("\n") + 1,
            "annotations": [],
            "extends": [],
            "implements": [],
            "fields": [],
            "methods": [],
        })

    # Array de Routes do Angular — captura as definições de rota
    routes = []
    for rm in re.finditer(r"path\s*:\s*['\"]([^'\"]*)['\"]", src_text):
        path_val = rm.group(1)
        routes.append(path_val)
    if routes:
        result["angular_routes"] = routes

    # Chamadas de cliente HTTP — captura as chamadas de API dos serviços
    http_calls = []
    for hm in re.finditer(
        r'(?:this\.http|axios|fetch)\s*\.?\s*(get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`\n]+)',
        src_text, re.IGNORECASE
    ):
        http_calls.append({"method": hm.group(1).upper(), "path": hm.group(2)[:120]})
    if http_calls:
        result["http_calls"] = http_calls

    return result if (result["types"] or result.get("angular_routes") or result.get("http_calls")) else None

# ── 6. Descoberta e roteamento de arquivos ────────────────────────────────────────

SKIP_DIRS = {"git", ".mind", "node_modules", "build", "dist", "out",
             ".gradle", ".mvn", "__pycache__", ".pytest_cache", "target",
             "vendor", ".venv", "venv", ".idea", ".vscode",
             # Código gerado — muito ruído, nenhum valor para a análise
             "generated", "generated-sources", "generated-test-sources",
             "avro-generated", "apt-generated", "querydsl"}

SKIP_FILE_PATTERNS = {"*Test*.java", "*Tests.java", "*IT.java", "*Spec.ts", "*.min.js",
                      # Classes geradas por Avro/JAXB — muito boilerplate, sem lógica
                      "*RecordBase*.java"}

def should_skip_file(p: Path) -> bool:
    for pat in SKIP_FILE_PATTERNS:
        if p.match(pat):
            return True
    return False

def discover_files() -> list[Path]:
    files = []
    for ext in PARSERS:
        for f in REPO_ROOT.rglob(f"*{ext}"):
            # Pula diretórios
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            if should_skip_file(f):
                continue
            # Pula classes geradas pelo Avro: ficam em pacotes audit.dto e são
            # 100% boilerplate gerado (subclasses de SpecificRecordBase com mais de 60 métodos Builder)
            if "audit/dto" in str(f).replace("\\", "/") or "audit\\dto" in str(f):
                continue
            files.append(f)
    file_count = len(files)
    print(f"Encontrados {file_count} arquivos de código (sem limite — todos os arquivos que não são gerados nem de teste)", flush=True)
    return sorted(files)

def analyze_file(filepath: Path) -> dict | None:
    rel = str(filepath.relative_to(REPO_ROOT)).replace("\\", "/")
    try:
        src = filepath.read_bytes()
    except (IOError, OSError):
        return None
    ext = filepath.suffix.lower()
    if ext == ".java":
        return analyze_java_file(filepath, rel, src)
    elif ext == ".py":
        return analyze_python_file(filepath, rel, src)
    elif ext in (".ts", ".tsx", ".js", ".jsx"):
        return analyze_ts_file(filepath, rel, src)
    return None

# ── 7. Pós-processamento: extração de índices especiais ─────────────────────────

def extract_kafka_listeners(all_types: list[dict]) -> list[dict]:
    listeners = []
    for t in all_types:
        for m in t.get("methods", []):
            for ann in m.get("annotations", []):
                if "KafkaListener" in ann:
                    topics = _java_annotation_arg(ann, "topics")
                    group  = _java_annotation_arg(ann, "groupId")
                    listeners.append({
                        "class":    t["name"],
                        "method":   m["name"],
                        "topics":   topics,
                        "group_id": group[0] if group else "",
                    })
    return listeners

def extract_rest_endpoints(all_types: list[dict]) -> list[dict]:
    METHOD_MAP = {
        "GetMapping":    "GET",
        "PostMapping":   "POST",
        "PutMapping":    "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping":  "PATCH",
        "RequestMapping": "ANY",
    }
    endpoints = []
    for t in all_types:
        base_path = ""
        for ann in t.get("annotations", []):
            for k, v in METHOD_MAP.items():
                if k in ann:
                    m = re.search(r'"([^"]*)"', ann)
                    if m:
                        base_path = m.group(1)
        for method in t.get("methods", []):
            for ann in method.get("annotations", []):
                for k, http_method in METHOD_MAP.items():
                    if k in ann:
                        m = re.search(r'"([^"]*)"', ann)
                        path = (base_path + (m.group(1) if m else "")).replace("//", "/")
                        endpoints.append({
                            "class":       t["name"],
                            "method":      method["name"],
                            "http_method": http_method,
                            "path":        path or "/",
                        })
    return endpoints

def extract_scheduled(all_types: list[dict]) -> list[dict]:
    scheduled = []
    for t in all_types:
        for m in t.get("methods", []):
            for ann in m.get("annotations", []):
                if "Scheduled" in ann:
                    scheduled.append({
                        "class":  t["name"],
                        "method": m["name"],
                        "config": ann,
                    })
    return scheduled

def extract_python_routes(all_types: list[dict]) -> list[dict]:
    """Extrai funções standalone com decorator de rota FastAPI/Flask."""
    ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "route"}
    routes = []
    for t in all_types:
        if t.get("kind") != "function":
            continue
        for ann in t.get("annotations", []):
            ann_lower = ann.lower()
            http_method = next((m for m in ROUTE_METHODS if f".{m}" in ann_lower), None)
            if http_method:
                path_m = re.search(r'[\'"]([^\'"\n]+)[\'"]', ann)
                routes.append({
                    "function": t["name"],
                    "http_method": http_method.upper() if http_method != "route" else "ANY",
                    "path": path_m.group(1) if path_m else "/",
                    "file": t.get("file", ""),
                })
    return routes

def extract_celery_tasks(all_types: list[dict]) -> list[dict]:
    """Extrai funções com decorator de tarefa Celery."""
    tasks = []
    for t in all_types:
        if t.get("kind") != "function":
            continue
        for ann in t.get("annotations", []):
            if "task" in ann.lower() or "shared_task" in ann.lower():
                tasks.append({"function": t["name"], "decorator": ann, "file": t.get("file", "")})
    return tasks

def extract_angular_components(all_types: list[dict]) -> list[dict]:
    """Extrai classes com os decorators Angular @Component, @Injectable, @NgModule."""
    components = []
    for t in all_types:
        anns = t.get("annotations", [])
        for ann in anns:
            for kind in ("@Component", "@Injectable", "@NgModule", "@Pipe", "@Directive"):
                if ann.startswith(kind):
                    selector_m = re.search(r"selector\s*:\s*['\"]([^'\"]+)['\"]", ann)
                    components.append({
                        "class": t["name"],
                        "kind": kind,
                        "selector": selector_m.group(1) if selector_m else "",
                        "file": t.get("file", ""),
                    })
                    break
    return components

def collect_ts_http_calls(file_results: list[dict]) -> list[dict]:
    """Coleta todas as chamadas HTTP encontradas nos arquivos TypeScript/JS."""
    calls = []
    for fr in file_results:
        for hc in fr.get("http_calls", []):
            calls.append({**hc, "file": fr["file"]})
    return calls

def collect_angular_routes(file_results: list[dict]) -> list[str]:
    """Coleta todos os caminhos de rota Angular nos arquivos TypeScript/JS."""
    seen, routes = set(), []
    for fr in file_results:
        for r in fr.get("angular_routes", []):
            if r not in seen:
                seen.add(r)
                routes.append(r)
    return routes

# ── 8. Geração do resumo em Markdown ───────────────────────────────────────

def _ann_badge(anns: list[str]) -> str:
    key = ["@Service","@Component","@Repository","@RestController","@Controller",
           "@KafkaListener","@Scheduled","@Configuration","@SpringBootApplication",
           "@Injectable","@Component","@NgModule","@Pipe","@Directive"]
    badges = [a for a in anns if any(a.startswith(k) for k in key)]
    return " ".join(f"`{b.split('(')[0]}`" for b in badges[:3])

def generate_markdown(graph: dict) -> str:
    lines = []
    repo = graph.get("repo", "")
    ts   = graph.get("analyzed_at", "")
    summary = graph.get("summary", {})

    lines += [
        f"# Grafo de Código — `{repo}`",
        "",
        f"Gerado em: {ts[:10]}  |  "
        f"Arquivos analisados: {summary.get('files_analyzed', 0)}  |  "
        f"Tipos: {summary.get('total_types', 0)}  |  "
        f"Métodos: {summary.get('total_methods', 0)}",
        "",
        "> Gerado automaticamente pelo mind-code-graph.py. Não edite à mão.",
        "> Para atualizar: rode `python .mind/tools/mind-stage.py` ou a skill `update-repo`.",
        "",
    ]

    # Endpoints REST
    endpoints = graph.get("rest_endpoints", [])
    if endpoints:
        lines += ["## Endpoints REST", "", "| Método | Caminho | Classe | Handler |",
                  "|---|---|---|---|"]
        for ep in sorted(endpoints, key=lambda x: x["path"]):
            lines.append(f"| `{ep['http_method']}` | `{ep['path']}` | "
                         f"`{ep['class']}` | `{ep['method']}` |")
        lines.append("")

    # Listeners Kafka
    listeners = graph.get("kafka_listeners", [])
    if listeners:
        lines += ["## Listeners Kafka", "", "| Classe | Método | Tópicos | Group ID |",
                  "|---|---|---|---|"]
        for ls in listeners:
            topics = ", ".join(f"`{t}`" for t in ls["topics"]) or "—"
            lines.append(f"| `{ls['class']}` | `{ls['method']}` | {topics} | "
                         f"`{ls['group_id'] or '—'}` |")
        lines.append("")

    # Tarefas agendadas
    scheduled = graph.get("scheduled_tasks", [])
    if scheduled:
        lines += ["## Tarefas Agendadas", "", "| Classe | Método | Configuração |", "|---|---|---|"]
        for s in scheduled:
            cfg = s["config"].replace("|", "\\|")[:80]
            lines.append(f"| `{s['class']}` | `{s['method']}` | `{cfg}` |")
        lines.append("")

    # Rotas Python (FastAPI / Flask)
    py_routes = graph.get("python_routes", [])
    if py_routes:
        lines += ["## Rotas Python (FastAPI / Flask)", "",
                  "| Método | Caminho | Função | Arquivo |", "|---|---|---|---|"]
        for r in sorted(py_routes, key=lambda x: x["path"]):
            lines.append(f"| `{r['http_method']}` | `{r['path']}` | "
                         f"`{r['function']}` | `{r.get('file','')}` |")
        lines.append("")

    # Tarefas Celery
    celery = graph.get("celery_tasks", [])
    if celery:
        lines += ["## Tarefas Celery", "", "| Função | Decorator | Arquivo |", "|---|---|---|"]
        for t in celery:
            lines.append(f"| `{t['function']}` | `{t['decorator'][:60]}` | `{t.get('file','')}` |")
        lines.append("")

    # Componentes / serviços / módulos Angular
    ng_comps = graph.get("angular_components", [])
    if ng_comps:
        lines += ["## Componentes e Serviços Angular", "",
                  "| Classe | Tipo | Seletor | Arquivo |", "|---|---|---|---|"]
        for c in sorted(ng_comps, key=lambda x: (x["kind"], x["class"])):
            sel = c["selector"] or "—"
            lines.append(f"| `{c['class']}` | `{c['kind']}` | `{sel}` | `{c.get('file','')}` |")
        lines.append("")

    # Rotas Angular
    ng_routes = graph.get("angular_routes", [])
    if ng_routes:
        lines += ["## Rotas Angular", ""]
        for r in sorted(ng_routes):
            lines.append(f"- `{r}`")
        lines.append("")

    # Chamadas HTTP em TypeScript
    http_calls = graph.get("ts_http_calls", [])
    if http_calls:
        lines += ["## Chamadas de Cliente HTTP (TypeScript)", "",
                  "| Método | Caminho | Arquivo |", "|---|---|---|"]
        seen = set()
        for hc in http_calls:
            key = (hc["method"], hc["path"])
            if key not in seen:
                seen.add(key)
                lines.append(f"| `{hc['method']}` | `{hc['path']}` | `{hc.get('file','')}` |")
        lines.append("")

    # Inventário de tipos — agrupado por pacote
    all_types = graph.get("types", [])
    by_pkg = defaultdict(list)
    for t in all_types:
        by_pkg[t.get("package", "")].append(t)

    lines += ["## Inventário de Tipos", ""]
    for pkg in sorted(by_pkg):
        lines.append(f"### `{pkg or '(padrão)'}`")
        lines.append("")
        for t in sorted(by_pkg[pkg], key=lambda x: x["name"]):
            badge = _ann_badge(t.get("annotations", []))
            kind_icon = {"class": "C", "interface": "I", "enum": "E", "annotation": "A"}.get(t["kind"], "?")
            lines.append(f"#### `{t['name']}` ({kind_icon}) {badge}")
            if t.get("extends"):
                lines.append(f"- **Estende**: {', '.join(f'`{e}`' for e in t['extends'])}")
            if t.get("implements"):
                lines.append(f"- **Implementa**: {', '.join(f'`{i}`' for i in t['implements'])}")
            if t.get("fields"):
                field_strs = [f"`{f['name']}: {f['type']}`" for f in t["fields"][:8]]
                lines.append(f"- **Campos**: {', '.join(field_strs)}"
                             + (" …" if len(t["fields"]) > 8 else ""))
            # Tabela de métodos
            public_methods = [m for m in t.get("methods", [])
                              if m["visibility"] in ("public", "protected") or
                              not m["name"].startswith("_")]
            if public_methods:
                lines += ["", "| Método | Assinatura | Anotações | Chamadas (5 primeiras) |",
                          "|---|---|---|---|"]
                for m in public_methods[:20]:
                    ann_str = " ".join(f"`{a.split('(')[0]}`" for a in m["annotations"][:2])
                    calls_str = ", ".join(f"`{c}`" for c in m["calls"][:5])
                    sig = m["signature"].replace("|", "\\|")[:70]
                    lines.append(f"| `{m['name']}` | `{sig}` | {ann_str} | {calls_str} |")
                if len(t.get("methods", [])) > 20:
                    lines.append(f"| … | _mais {len(t['methods']) - 20} métodos_ | | |")
            lines.append("")

    return "\n".join(lines)

# ── 9. Publicar no local commitado ───────────────────────────────────────
# O agente do Copilot commita o que o setup deixar na árvore de trabalho; por isso, gravar
# .mind/context/code-graph.md aqui garante que ele entre no PR sem depender de o
# agente seguir a skill.

def _without_generated_line(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.startswith(("Gerado em: ", "Generated: ")))

def publish_to_context(md_text: str, files_analyzed: int):
    if files_analyzed == 0:
        print("Nenhum arquivo de código analisável — .mind/context/code-graph.md não será publicado", flush=True)
        return
    ctx_path = REPO_ROOT / ".mind" / "context" / "code-graph.md"
    if ctx_path.exists():
        # A comparação por prefixo preserva as seções acrescentadas pelo agente
        # (Referência de Configuração etc.) e evita um diff só de data a cada execução.
        existing = _without_generated_line(ctx_path.read_text(encoding="utf-8", errors="replace"))
        if existing.startswith(_without_generated_line(md_text).rstrip("\n")):
            print(f"Sem alterações: {ctx_path}", flush=True)
            return
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(md_text, encoding="utf-8")
    print(f"Gravado: {ctx_path}", flush=True)

# ── 10. Principal ───────────────────────────────────────────────────────────────

def main():
    print(f"Análise do grafo de código — repo: {REPO_ROOT}", flush=True)
    files = discover_files()
    print(f"Encontrados {len(files)} arquivos de código", flush=True)

    all_types: list[dict] = []
    file_results: list[dict] = []
    errors = 0

    total_files = len(files)
    for i, f in enumerate(files, 1):
        result = analyze_file(f)
        if result:
            file_results.append(result)
            all_types.extend(result["types"])
        else:
            errors += 1
        # Registra no log a cada 25 / 50 / 75 / 100 %
        if total_files > 0 and i % max(1, total_files // 4) == 0:
            print(f"  processados {i}/{total_files} arquivos …", flush=True)

    total_methods = sum(len(t.get("methods", [])) for t in all_types)
    print(f"Extraídos {len(all_types)} tipos, {total_methods} métodos, "
          f"{errors} erros de parse", flush=True)

    kafka     = extract_kafka_listeners(all_types)
    endpoints = extract_rest_endpoints(all_types)
    scheduled = extract_scheduled(all_types)
    py_routes = extract_python_routes(all_types)
    celery    = extract_celery_tasks(all_types)
    ng_comps  = extract_angular_components(all_types)
    ng_routes = collect_angular_routes(file_results)
    http_calls= collect_ts_http_calls(file_results)

    graph = {
        "repo":            REPO_ROOT.name,
        "analyzed_at":     datetime.now(timezone.utc).isoformat(),
        "summary": {
            "files_analyzed":   len(file_results),
            "total_types":      len(all_types),
            "total_methods":    total_methods,
            "kafka_listeners":  len(kafka),
            "rest_endpoints":   len(endpoints),
            "scheduled_tasks":  len(scheduled),
            "python_routes":    len(py_routes),
            "celery_tasks":     len(celery),
            "angular_components": len(ng_comps),
            "angular_routes":   len(ng_routes),
            "ts_http_calls":    len(http_calls),
        },
        "types":             all_types,
        "kafka_listeners":   kafka,
        "rest_endpoints":    endpoints,
        "scheduled_tasks":   scheduled,
        "python_routes":     py_routes,
        "celery_tasks":      celery,
        "angular_components": ng_comps,
        "angular_routes":    ng_routes,
        "ts_http_calls":     http_calls,
    }

    json_path = GLOBAL_DIR / "code-graph.json"
    json_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Gravado: {json_path}", flush=True)

    md_text = generate_markdown(graph)
    md_path = GLOBAL_DIR / "code-graph.md"
    md_path.write_text(md_text, encoding="utf-8")
    print(f"Gravado: {md_path}", flush=True)

    publish_to_context(md_text, len(file_results))

    print(
        f"Grafo de código concluído — "
        f"{len(kafka)} listeners Kafka, {len(endpoints)} endpoints REST, {len(scheduled)} tarefas agendadas, "
        f"{len(py_routes)} rotas Python, {len(celery)} tarefas Celery, "
        f"{len(ng_comps)} componentes Angular, {len(ng_routes)} rotas Angular, "
        f"{len(http_calls)} chamadas HTTP",
        flush=True
    )

if __name__ == "__main__":
    main()
