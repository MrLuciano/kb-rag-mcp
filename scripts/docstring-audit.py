#!/usr/bin/env python3
"""Docstring coverage audit — scans Python modules for public functions/classes
without proper English Google-style docstrings. One-time static analysis,
no project imports required.

Detects:
  - MISSING   — no docstring present
  - PORTUGUESE — docstring contains Portuguese-language indicators
  - OK        — English docstring found

Extended with inline comment scanning (--check-inline) and CI gate support
(--fail-under).
"""

import argparse
import ast
import os
import sys
from datetime import date
from pathlib import Path


# Portuguese word indicators for heuristic detection
PORTUGUESE_WORDS: set[str] = {
    "classe",
    "função",
    "funções",
    "retorna",
    "retornar",
    "retornado",
    "parâmetro",
    "parâmetros",
    "paramêtro",
    "paramêtros",
    "arquivo",
    "arquivos",
    "diretório",
    "diretórios",
    "usuário",
    "usuários",
    "configura",
    "configurar",
    "configurado",
    "extrai",
    "extrair",
    "extraído",
    "infere",
    "inferir",
    "inferido",
    "gerencia",
    "gerenciar",
    "gerenciado",
    "utiliza",
    "utilizar",
    "utilizado",
    "classificador",
    "classificação",
    "documento",
    "documentos",
    "nome",
    "caminho",
    "caminhos",
    "pasta",
    "pastas",
    "lista",
    "listar",
    "listado",
    "executa",
    "executar",
    "executado",
    "processa",
    "processar",
    "processado",
    "carrega",
    "carregar",
    "carregado",
    "obtém",
    "obter",
    "obtido",
    "define",
    "definir",
    "definido",
    "retorna",
    "cria",
    "criar",
    "criado",
    "indica",
    "indicar",
    "indicado",
    "método",
    "métodos",
    "classe",
    "classes",
    "valor",
    "valores",
    "chave",
    "chaves",
    "padrão",
    "padrões",
    "opcional",
    "obrigatório",
    "erro",
    "erros",
    "exceção",
    "exceções",
    "booleano",
    "inteiro",
    "chamada",
    "retorno",
    "parâmetro",
    "parâmetros",
    "atributo",
    "atributos",
    # Extended set for inline comment detection
    "página",
    "páginas",
    "guia",
    "guias",
    "taxonomia",
    "separador",
    "separadores",
    "avalia",
    "avaliar",
    "critério",
    "critérios",
    "mapeamento",
    "mapear",
    "binários",
    "artefatos",
    "reunião",
    "apresentação",
    "treinamento",
    "referência",
    "tutorial",
    "cookbook",
    "cenário",
    "cenários",
    "código",
    "cacheado",
    "coleção",
    "coleções",
    "conexão",
    "conexões",
    "conectado",
    "conectar",
    "descritor",
    "descritores",
    "diretório",
    "diretórios",
    "documento",
    "documentos",
    "entrada",
    "extração",
    "extrações",
    "filtro",
    "filtros",
    "identificador",
    "identificadores",
    "implementação",
    "implementações",
    "índice",
    "índices",
    "inicialização",
    "inicializar",
    "instalação",
    "instalações",
    "iteração",
    "iterações",
    "mensagem",
    "mensagens",
    "metadados",
    "método",
    "métodos",
    "modelo",
    "modelos",

    "nível",
    "níveis",
    "nota",
    "notas",
    "número",
    "números",
    "operação",
    "operações",
    "parâmetro",
    "parâmetros",
    "plugins",
    "porta",
    "portas",
    "prefixo",
    "prefixos",
    "processo",
    "processos",
    "produto",
    "produtos",
    "projeto",
    "projetos",
    "registro",
    "registros",
    "regra",
    "regras",
    "relatório",
    "relatórios",
    "requisição",
    "requisições",
    "resposta",
    "respostas",
    "resultado",
    "resultados",
    "servidor",
    "servidores",
    "sistema",
    "sistemas",
    "solução",
    "soluções",
    "subdiretório",
    "subdiretórios",
    "subsistema",
    "subsistemas",
    "suporte",
    "suportar",

    "tópico",
    "tópicos",
    "validação",
    "validações",
    "versão",
    "versões",
}


def _has_portuguese(docstring: str) -> bool:
    """Heuristic check: returns True if docstring contains Portuguese words.

    Skips standard Google-style section headers (Args, Returns, Raises)
    and common English words that overlap with Portuguese.
    """
    lower = docstring.lower()
    # Skip standard Google-style section headers (false positives)
    section_headers = {"args", "returns", "raises"}
    for line in lower.split("\n"):
        stripped = line.strip()
        if stripped in ("args:", "returns:", "raises:") or stripped.startswith(
            ("args: ", "returns: ", "raises: ")
        ):
            continue
        for word in PORTUGUESE_WORDS:
            if word in section_headers:
                continue
            # Word-boundary check using simple substring heuristics
            if (
                f" {word} " in line
                or line.startswith(f"{word} ")
                or line.endswith(f" {word}")
            ):
                return True
            # Also check with common punctuation
            for suffix in (".", ",", ":", ";", "!", "?", ")", "\n", "'", '"'):
                if f" {word}{suffix}" in line or line == word + suffix:
                    return True
    return False


def _get_docstring(node: ast.AST) -> str | None:
    """Extract docstring from a FunctionDef, AsyncFunctionDef, or ClassDef node."""
    body = getattr(node, "body", [])
    if body and isinstance(body[0], ast.Expr):
        expr = body[0]
        if isinstance(expr.value, ast.Constant) and isinstance(expr.value.value, str):
            return expr.value.value
        # Python < 3.8 compatibility: ast.Str
        if isinstance(expr.value, ast.Str):
            return expr.value.s
    return None


def _has_google_section(docstring: str, section: str) -> bool:
    """Check if a docstring contains a Google-style section header (Args, Returns, Raises)."""
    for line in docstring.split("\n"):
        stripped = line.strip()
        if stripped == f"{section}:" or stripped.startswith(f"{section}: "):
            return True
    return False


def _is_decorative_line(comment_text: str) -> bool:
    """Check if a comment line is purely decorative (only ASCII art characters)."""
    stripped = comment_text.strip()
    if not stripped:
        return True
    # Allow only: #, spaces, ─, -, =, *, +, |, ~, _, >, <, (, ), [, ]
    decorative_chars = {"#", " ", "─", "-", "=", "*", "+", "|", "~", "_", ">", "<", "(", ")", "[", "]"}
    for ch in stripped:
        if ch not in decorative_chars:
            return False
    return True


def scan_inline_comments(filepath: Path) -> list[dict]:
    """Scan a Python file for inline comments containing Portuguese words.

    Returns a list of dicts: [{"line": <int>, "text": <str>}, ...]
    Skips shebang lines, encoding declarations, and purely decorative lines.
    """
    findings: list[dict] = []
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return findings

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Find the first # that is not inside a string (naive: assumes # at
        # the start of a comment, not inside a string literal)
        # Skip shebang and encoding declarations
        if line_no == 1 and stripped.startswith("#!"):
            continue
        if "# -*-" in stripped:
            continue

        # Find comment position
        comment_idx = stripped.find("#")
        if comment_idx == -1:
            continue

        comment_text = stripped[comment_idx + 1 :].strip()

        # Skip purely decorative lines
        if _is_decorative_line(comment_text):
            continue

        # Check for Portuguese
        if _has_portuguese(f" {comment_text} "):
            findings.append({"line": line_no, "text": comment_text})

    return findings


def audit_file(filepath: Path) -> dict[str, dict]:
    """Audit a single Python file for docstring coverage on public functions/classes.

    Returns a dict mapping function/class names to their audit result:
      {"name": func_name, "status": "MISSING"|"PORTUGUESE"|"OK", "detail": ...}
    """
    with open(filepath, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except SyntaxError as e:
            return {"error": f"SyntaxError: {e}"}

    results: dict[str, dict] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            # Skip private/internal members
            if name.startswith("_"):
                continue
            # Skip magic methods
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and name.startswith("__"):
                continue

            doc = _get_docstring(node)
            status: str
            detail: str = ""

            if doc is None:
                status = "MISSING"
                detail = "No docstring found"
            elif _has_portuguese(doc):
                status = "PORTUGUESE"
                detail = "Portuguese detected in docstring"
            else:
                status = "OK"
                detail = "English docstring"

            results[name] = {
                "status": status,
                "detail": detail,
            }

    return results


def main():
    parser = argparse.ArgumentParser(description="Docstring coverage audit")
    parser.add_argument(
        "--dir", action="append", type=Path,
        help="Source directories to audit (can be specified multiple times)",
    )
    parser.add_argument(
        "--check-inline", action="store_true",
        help="Also scan inline comments (#) for Portuguese text",
    )
    parser.add_argument(
        "--fail-under", type=int, default=None,
        help="Exit non-zero if total Portuguese findings exceed this threshold",
    )
    args = parser.parse_args()

    project_root = Path(os.environ.get("PROJECT_ROOT", Path.cwd()))
    source_dirs: list[Path] = args.dir if args.dir else [
        project_root / "kb_server", project_root / "ingest"
    ]

    today = date.today().isoformat()

    print("Docstring Coverage Audit")
    print("======================")
    print(f"Generated: {today}")
    print()

    total_nodes = 0
    total_ok = 0
    total_missing = 0
    total_portuguese = 0
    total_inline_portuguese = 0
    report_lines: list[str] = []

    for src_dir in source_dirs:
        if not src_dir.exists():
            report_lines.append(f"\n{src_dir}: DIRECTORY NOT FOUND")
            continue
        py_files = sorted(src_dir.rglob("*.py"))
        py_files = [f for f in py_files if f.name != "__init__.py" and "__pycache__" not in f.parts]

        for py_file in py_files:
            relative = os.path.relpath(str(py_file), str(project_root))

            # Docstring audit
            try:
                results = audit_file(py_file)
            except Exception as e:
                report_lines.append(f"\n{relative}: ERROR: {e}")
                continue

            docstring_issues = False
            if results and "error" not in results:
                has_issues = any(r["status"] != "OK" for r in results.values())
                file_missing = sum(1 for r in results.values() if r["status"] == "MISSING")
                file_portuguese = sum(1 for r in results.values() if r["status"] == "PORTUGUESE")
                file_ok = sum(1 for r in results.values() if r["status"] == "OK")
                total_nodes += len(results)
                total_ok += file_ok
                total_missing += file_missing
                total_portuguese += file_portuguese
                docstring_issues = has_issues

                if has_issues:
                    report_lines.append(f"\n{relative}:")
                    for func_name, result in sorted(results.items()):
                        if result["status"] != "OK":
                            report_lines.append(f"  {func_name}: {result['status']} — {result['detail']}")
            elif results and "error" in results:
                report_lines.append(f"\n{relative}: {results['error']}")
                continue

            # Inline comment audit (if enabled)
            inline_findings: list[dict] = []
            if args.check_inline:
                inline_findings = scan_inline_comments(py_file)
                total_inline_portuguese += len(inline_findings)

            # Decide whether to emit a report line for this file
            if inline_findings:
                if not docstring_issues:
                    report_lines.append(f"\n{relative}:")
                for finding in inline_findings:
                    report_lines.append(f"  Inline comment Line {finding['line']}: {finding['text']}")
                report_lines.append(f"  -> Inline comments: {len(inline_findings)} Portuguese")

            if not docstring_issues and not inline_findings:
                report_lines.append(f"\n{relative}:")
                report_lines.append(f"  All {len(results)} public methods have English docstrings ✓")

    print("\n".join(report_lines))
    print()
    print("Summary:")
    print(f"  Total public methods/classes: {total_nodes}")
    print(f"  OK: {total_ok}")
    print(f"  MISSING: {total_missing}")
    print(f"  PORTUGUESE docstrings: {total_portuguese}")
    print(f"  PORTUGUESE inline comments: {total_inline_portuguese}")

    # Fail-under enforcement
    if args.fail_under is not None:
        total_findings = total_portuguese + total_inline_portuguese
        print()
        if total_findings > args.fail_under:
            print(
                f"FAIL: Found {total_findings} Portuguese items "
                f"(threshold: {args.fail_under})"
            )
            sys.exit(1)
        else:
            print(
                f"PASS: Found {total_findings} Portuguese items "
                f"(threshold: {args.fail_under})"
            )


if __name__ == "__main__":
    main()
