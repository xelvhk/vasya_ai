from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import secrets
import shutil
import subprocess
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "llama3"


@dataclass(frozen=True)
class StepResult:
    name: str
    status: str
    message: str


def main() -> None:
    args = _parse_args(sys.argv[1:])
    results = run_setup(
        root_dir=ROOT_DIR,
        dry_run=args.dry_run,
        install_dependencies=not args.skip_dependencies,
        pull_model=args.pull_model,
        model=args.model,
    )
    _print_results(results)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Idempotent macOS setup for Vasya AI")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without changing files")
    parser.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="Do not install Python dependencies",
    )
    parser.add_argument(
        "--pull-model",
        action="store_true",
        help="Run `ollama pull <model>` when Ollama is installed",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model to recommend or pull")
    return parser.parse_args(argv)


def run_setup(
    *,
    root_dir: Path,
    dry_run: bool = False,
    install_dependencies: bool = True,
    pull_model: bool = False,
    model: str = DEFAULT_MODEL,
) -> list[StepResult]:
    root = root_dir.resolve()
    results = [
        _check_macos(),
        _ensure_venv(root, dry_run=dry_run),
        _ensure_env_file(root, dry_run=dry_run),
        _ensure_storage_dirs(root, dry_run=dry_run),
    ]
    if install_dependencies:
        results.append(_install_dependencies(root, dry_run=dry_run))
    else:
        results.append(StepResult("dependencies", "SKIP", "dependency install skipped by flag"))
    results.append(_check_or_prepare_ollama(root=root, model=model, pull_model=pull_model, dry_run=dry_run))
    results.append(StepResult("first run", "NEXT", _first_run_summary(model=model)))
    return results


def _check_macos() -> StepResult:
    if sys.platform == "darwin":
        return StepResult("platform", "OK", "macOS detected")
    return StepResult("platform", "WARN", "not running on macOS; continuing with portable setup steps")


def _ensure_venv(root: Path, *, dry_run: bool) -> StepResult:
    venv_dir = root / ".venv"
    if venv_dir.exists():
        return StepResult("virtualenv", "OK", ".venv already exists")
    if dry_run:
        return StepResult("virtualenv", "PLAN", "would create .venv")
    _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=root)
    return StepResult("virtualenv", "OK", "created .venv")


def _install_dependencies(root: Path, *, dry_run: bool) -> StepResult:
    pip_path = root / ".venv" / "bin" / "pip"
    if not pip_path.exists():
        return StepResult(
            "dependencies",
            "WARN",
            ".venv/bin/pip not found; create virtualenv first",
        )
    if dry_run:
        return StepResult("dependencies", "PLAN", "would install requirements.txt")
    _run([str(pip_path), "install", "--upgrade", "pip"], cwd=root)
    _run([str(pip_path), "install", "-r", "requirements.txt"], cwd=root)
    return StepResult("dependencies", "OK", "installed Python dependencies")


def _ensure_env_file(root: Path, *, dry_run: bool) -> StepResult:
    env_path = root / ".env"
    if env_path.exists():
        return StepResult("env", "OK", ".env already exists; left unchanged")
    if dry_run:
        return StepResult("env", "PLAN", "would create .env from .env.example with generated API token")

    example_path = root / ".env.example"
    if example_path.exists():
        content = _build_env_from_example(example_path.read_text(encoding="utf-8"))
    else:
        content = _default_env_content()
    env_path.write_text(content, encoding="utf-8")
    return StepResult("env", "OK", "created .env with generated VASYA_API_AUTH_TOKEN")


def _build_env_from_example(template: str) -> str:
    token = _generate_api_token()
    lines = []
    token_seen = False
    for raw_line in template.splitlines():
        if raw_line.startswith("VASYA_API_AUTH_TOKEN="):
            lines.append(f"VASYA_API_AUTH_TOKEN={token}")
            token_seen = True
        else:
            lines.append(raw_line)
    if not token_seen:
        lines.append(f"VASYA_API_AUTH_TOKEN={token}")
    return "\n".join(lines).rstrip() + "\n"


def _default_env_content() -> str:
    return (
        "APP_VERSION=0.5.50\n"
        "OLLAMA_MODEL=llama3\n"
        "GOOGLE_CALENDAR_ENABLED=false\n"
        f"VASYA_API_AUTH_TOKEN={_generate_api_token()}\n"
        "VASYA_API_REQUIRE_AUTH=true\n"
        "MEMORY_WIKI_DIR=storage/memory_wiki\n"
    )


def _generate_api_token() -> str:
    return secrets.token_urlsafe(32)


def _ensure_storage_dirs(root: Path, *, dry_run: bool) -> StepResult:
    paths = [
        root / "storage",
        root / "storage" / "memory_wiki",
        root / "storage" / "voices",
    ]
    if dry_run:
        return StepResult("storage", "PLAN", "would ensure storage, memory_wiki, and voices dirs")
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    return StepResult("storage", "OK", "storage directories are ready")


def _check_or_prepare_ollama(*, root: Path, model: str, pull_model: bool, dry_run: bool) -> StepResult:
    if shutil.which("ollama") is None:
        return StepResult("ollama", "WARN", "Ollama not found; install with `brew install ollama`")
    if pull_model:
        if dry_run:
            return StepResult("ollama", "PLAN", f"would pull Ollama model {model}")
        _run(["ollama", "pull", model], cwd=root)
        return StepResult("ollama", "OK", f"Ollama found and model pull requested: {model}")
    return StepResult("ollama", "OK", f"Ollama found; ensure model is available with `ollama pull {model}`")


def _first_run_summary(*, model: str) -> str:
    return (
        "next: source .venv/bin/activate; "
        f"ollama pull {model}; "
        "python scripts/doctor.py; "
        "python main.py"
    )


def first_run_checklist(model: str = DEFAULT_MODEL) -> list[str]:
    return [
        "Activate the virtualenv: source .venv/bin/activate",
        f"Install or verify Ollama model: ollama pull {model}",
        "Grant microphone/accessibility permissions when macOS asks",
        "Run diagnostics: python scripts/doctor.py",
        "Start desktop shell: python main.py",
        "Optional API: python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8787 --reload",
    ]


def _print_results(results: list[StepResult]) -> None:
    print("== Vasya AI macOS setup ==")
    for result in results:
        print(f"[{result.status}] {result.name}: {result.message}")
    print()
    print("First-run checklist:")
    for item in first_run_checklist():
        print(f"- {item}")


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


if __name__ == "__main__":
    main()
