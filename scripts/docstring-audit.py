#!/usr/bin/env python3
"""Docstring coverage audit — scans Python modules for public functions/classes
without proper English Google-style docstrings. One-time static analysis,
no project imports required.

Detects:
  - MISSING   — no docstring present
  - PORTUGUESE — docstring contains Portuguese-language indicators
  - OK        — English docstring found
"""

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
    "args",
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
    project_root = Path(os.environ.get("PROJECT_ROOT", Path.cwd()))

    # Parse --dir flags or use defaults
    source_dirs: list[Path] = []
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--dir" and i + 1 < len(args):
            source_dirs.append(Path(args[i + 1]))
            i += 2
        else:
            i += 1

    if not source_dirs:
        source_dirs = [project_root / "kb_server", project_root / "ingest"]

    today = date.today().isoformat()

    print("Docstring Coverage Audit")
    print("======================")
    print(f"Generated: {today}")
    print()

    total_nodes = 0
    total_ok = 0
    total_missing = 0
    total_portuguese = 0
    report_lines: list[str] = []

    for src_dir in source_dirs:
        if not src_dir.exists():
            report_lines.append(f"\n{src_dir}: DIRECTORY NOT FOUND")
            continue
        py_files = sorted(src_dir.rglob("*.py"))
        py_files = [f for f in py_files if f.name != "__init__.py" and "__pycache__" not in f.parts]

        for py_file in py_files:
            try:
                results = audit_file(py_file)
            except Exception as e:
                report_lines.append(f"\n{os.path.relpath(str(py_file), str(project_root))}: ERROR: {e}")
                continue

            if not results or "error" in results:
                if "error" in results:
                    report_lines.append(f"\n{os.path.relpath(str(py_file), str(project_root))}: {results['error']}")
                continue

            relative = os.path.relpath(str(py_file), str(project_root))
            has_issues = any(r["status"] != "OK" for r in results.values())
            file_missing = sum(1 for r in results.values() if r["status"] == "MISSING")
            file_portuguese = sum(1 for r in results.values() if r["status"] == "PORTUGUESE")
            file_ok = sum(1 for r in results.values() if r["status"] == "OK")
            total_nodes += len(results)
            total_ok += file_ok
            total_missing += file_missing
            total_portuguese += file_portuguese

            if not has_issues:
                report_lines.append(f"\n{relative}:")
                report_lines.append(f"  All {len(results)} public methods have English docstrings ✓")
                continue

            report_lines.append(f"\n{relative}:")
            for func_name, result in sorted(results.items()):
                if result["status"] != "OK":
                    report_lines.append(f"  {func_name}: {result['status']} — {result['detail']}")
            report_lines.append(
                f"  -> {file_ok} OK | {file_missing} MISSING | {file_portuguese} PORTUGUESE"
            )

    print("\n".join(report_lines))
    print()
    print("Summary:")
    print(f"  Total public methods/classes: {total_nodes}")
    print(f"  OK: {total_ok}")
    print(f"  MISSING: {total_missing}")
    print(f"  PORTUGUESE: {total_portuguese}")


if __name__ == "__main__":
    main()
