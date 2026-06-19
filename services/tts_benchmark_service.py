from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

from config.settings import (
    PIPER_COMMAND,
    PIPER_LENGTH_SCALE,
    PIPER_SPEAKER,
    TTS_HYBRID_SHORT_TEXT_MAX_WORDS,
    TTS_RATE,
    TTS_VOICE,
    XTTS_COMMAND,
    XTTS_LANGUAGE,
    XTTS_MODEL_NAME,
    XTTS_TIMEOUT_SECONDS,
)
from utils.platform_runtime import get_platform_name
from voice.profiles import get_profile_model_path, get_profile_speaker_wav, get_voice_profile


DEFAULT_TTS_BENCHMARK_TEXT = "Привет, это короткий тест скорости голоса Васи."
BASELINE_BACKENDS = ("say", "piper", "hybrid", "xtts")
EXPERIMENTAL_BACKENDS = ("chatterbox", "misotts")
CHATTERBOX_LANGUAGE = "ru"
CHATTERBOX_T3_MODEL = "v3"
CHATTERBOX_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class TTSBenchmarkPlan:
    backend: str
    selected_backend: str
    command: list[str]
    output_path: Path
    stdin_text: str | None = None
    timeout_seconds: int = 120
    backend_status: str = ""
    heavy: bool = False
    experimental: bool = False


@dataclass(frozen=True)
class TTSBenchmarkResult:
    backend: str
    status: str
    selected_backend: str
    backend_status: str
    time_to_first_audio_ms: float | None = None
    total_synthesis_ms: float | None = None
    output_path: str | None = None
    failure_reason: str | None = None
    heavy: bool = False
    experimental: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessTiming:
    time_to_first_audio_ms: float | None
    total_synthesis_ms: float


ProcessRunner = Callable[[TTSBenchmarkPlan], ProcessTiming]


def run_tts_benchmark(
    *,
    text: str = DEFAULT_TTS_BENCHMARK_TEXT,
    backends: list[str] | None = None,
    include_heavy: bool = False,
    include_experimental: bool = False,
    save_artifacts: bool = False,
    artifact_dir: Path | None = None,
    process_runner: ProcessRunner | None = None,
) -> dict[str, object]:
    selected_backends = backends or list(BASELINE_BACKENDS)
    if include_experimental:
        for experimental_backend in EXPERIMENTAL_BACKENDS:
            if experimental_backend not in selected_backends:
                selected_backends.append(experimental_backend)

    runner = process_runner or _execute_plan
    with tempfile.TemporaryDirectory(prefix="vasya-tts-benchmark-") as tmp:
        if save_artifacts:
            output_dir = artifact_dir or Path("storage/tts_benchmarks")
        else:
            output_dir = Path(tmp)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = [
            _benchmark_backend(
                backend=backend,
                text=text,
                output_dir=output_dir,
                include_heavy=include_heavy,
                runner=runner,
            )
            for backend in selected_backends
        ]

    return {
        "text": text,
        "include_heavy": include_heavy,
        "include_experimental": include_experimental,
        "save_artifacts": save_artifacts,
        "results": [result.to_dict() for result in results],
    }


def build_tts_benchmark_report(snapshot: dict[str, object]) -> str:
    lines = [
        "TTS benchmark",
        f"Text: {snapshot.get('text', '')}",
        (
            "Mode: "
            f"include_heavy={bool(snapshot.get('include_heavy'))}, "
            f"include_experimental={bool(snapshot.get('include_experimental'))}, "
            f"save_artifacts={bool(snapshot.get('save_artifacts'))}"
        ),
    ]
    results = snapshot.get("results")
    if not isinstance(results, list):
        return "\n".join(lines)

    for item in results:
        if not isinstance(item, dict):
            continue
        backend = item.get("backend", "unknown")
        status = item.get("status", "unknown")
        selected = item.get("selected_backend", backend)
        backend_status = item.get("backend_status", "")
        total_ms = item.get("total_synthesis_ms")
        first_ms = item.get("time_to_first_audio_ms")
        failure = item.get("failure_reason")
        if status == "OK":
            lines.append(
                f"- {backend} ({selected}): OK, first audio {_format_ms(first_ms)}, "
                f"total {_format_ms(total_ms)} - {backend_status}"
            )
        elif status == "SKIP":
            lines.append(f"- {backend} ({selected}): SKIP - {failure or backend_status}")
        else:
            lines.append(f"- {backend} ({selected}): FAIL - {failure or backend_status}")
    return "\n".join(lines)


def _benchmark_backend(
    *,
    backend: str,
    text: str,
    output_dir: Path,
    include_heavy: bool,
    runner: ProcessRunner,
) -> TTSBenchmarkResult:
    try:
        plan_or_skip = build_tts_benchmark_plan(
            backend=backend,
            text=text,
            output_dir=output_dir,
            include_heavy=include_heavy,
        )
        if isinstance(plan_or_skip, TTSBenchmarkResult):
            return plan_or_skip
        timing = runner(plan_or_skip)
        return TTSBenchmarkResult(
            backend=plan_or_skip.backend,
            status="OK",
            selected_backend=plan_or_skip.selected_backend,
            backend_status=plan_or_skip.backend_status,
            time_to_first_audio_ms=_round_ms(timing.time_to_first_audio_ms),
            total_synthesis_ms=_round_ms(timing.total_synthesis_ms),
            output_path=str(plan_or_skip.output_path),
            heavy=plan_or_skip.heavy,
            experimental=plan_or_skip.experimental,
        )
    except Exception as exc:
        return TTSBenchmarkResult(
            backend=backend,
            status="FAIL",
            selected_backend=backend,
            backend_status="benchmark failed",
            failure_reason=str(exc),
        )


def build_tts_benchmark_plan(
    *,
    backend: str,
    text: str,
    output_dir: Path,
    include_heavy: bool = False,
) -> TTSBenchmarkPlan | TTSBenchmarkResult:
    normalized = backend.strip().lower()
    if normalized == "say":
        return _build_say_plan(text=text, output_dir=output_dir)
    if normalized == "piper":
        return _build_piper_plan(text=text, output_dir=output_dir)
    if normalized == "hybrid":
        return _build_hybrid_plan(text=text, output_dir=output_dir, include_heavy=include_heavy)
    if normalized == "xtts":
        if not include_heavy:
            return _skip(
                backend="xtts",
                selected_backend="xtts",
                reason="XTTS is heavy and opt-in; rerun with --include-heavy",
                heavy=True,
            )
        return _build_xtts_plan(text=text, output_dir=output_dir)
    if normalized in {"misotts", "miso", "miso_tts"}:
        return _skip(
            backend="misotts",
            selected_backend="misotts",
            reason=(
                "MisoTTS is an experimental high-quality/heavy slot; "
                "benchmark support is intentionally placeholder-only for now"
            ),
            heavy=True,
            experimental=True,
        )
    if normalized in {"chatterbox", "chatterbox-tts", "chatterbox_multilingual"}:
        return _build_chatterbox_plan(text=text, output_dir=output_dir)
    return _skip(backend=backend, selected_backend=backend, reason=f"unknown backend: {backend}")


def _build_say_plan(*, text: str, output_dir: Path) -> TTSBenchmarkPlan | TTSBenchmarkResult:
    if get_platform_name() != "macos" or shutil.which("say") is None:
        return _skip("say", "say", "macOS say command is not available")
    output_path = output_dir / "say.aiff"
    return TTSBenchmarkPlan(
        backend="say",
        selected_backend="say",
        command=["say", "-v", TTS_VOICE, "-r", str(TTS_RATE), "-o", str(output_path), text],
        output_path=output_path,
        timeout_seconds=60,
        backend_status=f"say voice={TTS_VOICE}, rate={TTS_RATE}",
    )


def _build_piper_plan(*, text: str, output_dir: Path) -> TTSBenchmarkPlan | TTSBenchmarkResult:
    command_path = _resolve_command(PIPER_COMMAND)
    profile = get_voice_profile("ruslan_direct")
    model_path = get_profile_model_path(profile)
    if command_path is None:
        return _skip("piper", "piper", f"Piper command '{PIPER_COMMAND}' was not found")
    if model_path is None:
        return _skip("piper", "piper", "Piper model is not installed")

    output_path = output_dir / "piper.wav"
    command = [command_path, "--model", str(model_path), "--output_file", str(output_path)]
    if PIPER_SPEAKER:
        command.extend(["--speaker", PIPER_SPEAKER])
    length_scale = profile.piper_length_scale or (float(PIPER_LENGTH_SCALE) if PIPER_LENGTH_SCALE else None)
    if length_scale is not None:
        command.extend(["--length_scale", str(length_scale)])
    return TTSBenchmarkPlan(
        backend="piper",
        selected_backend="piper",
        command=command,
        stdin_text=text,
        output_path=output_path,
        timeout_seconds=90,
        backend_status=f"piper profile={profile.profile_id}, model={model_path.name}",
    )


def _build_hybrid_plan(
    *,
    text: str,
    output_dir: Path,
    include_heavy: bool,
) -> TTSBenchmarkPlan | TTSBenchmarkResult:
    words = [word for word in text.split() if word.strip()]
    if len(words) <= max(1, TTS_HYBRID_SHORT_TEXT_MAX_WORDS):
        plan = _build_piper_plan(text=text, output_dir=output_dir)
        if isinstance(plan, TTSBenchmarkPlan):
            return _copy_plan_for_backend(plan, backend="hybrid", status_suffix="hybrid fast path")
    if not include_heavy:
        return _skip(
            "hybrid",
            "xtts",
            "hybrid would use XTTS for this text; rerun with --include-heavy",
            heavy=True,
        )
    xtts_plan = _build_xtts_plan(text=text, output_dir=output_dir)
    if isinstance(xtts_plan, TTSBenchmarkPlan):
        return _copy_plan_for_backend(xtts_plan, backend="hybrid", status_suffix="hybrid natural path")
    return xtts_plan


def _build_xtts_plan(*, text: str, output_dir: Path) -> TTSBenchmarkPlan | TTSBenchmarkResult:
    command_path = _resolve_command(XTTS_COMMAND)
    profile = get_voice_profile("alexa_natural_xtts")
    speaker_wav = get_profile_speaker_wav(profile)
    if command_path is None:
        return _skip("xtts", "xtts", f"XTTS command '{XTTS_COMMAND}' was not found", heavy=True)
    if speaker_wav is None:
        return _skip("xtts", "xtts", "XTTS speaker sample is not configured", heavy=True)

    output_path = output_dir / "xtts.wav"
    language = profile.xtts_language or XTTS_LANGUAGE or "ru"
    return TTSBenchmarkPlan(
        backend="xtts",
        selected_backend="xtts",
        command=[
            command_path,
            "--model_name",
            XTTS_MODEL_NAME,
            "--text",
            text,
            "--speaker_wav",
            str(speaker_wav),
            "--language_idx",
            language,
            "--out_path",
            str(output_path),
        ],
        output_path=output_path,
        timeout_seconds=max(120, XTTS_TIMEOUT_SECONDS),
        backend_status=f"xtts model={XTTS_MODEL_NAME}, speaker={speaker_wav.name}",
        heavy=True,
    )


def _build_chatterbox_plan(*, text: str, output_dir: Path) -> TTSBenchmarkPlan | TTSBenchmarkResult:
    if importlib.util.find_spec("chatterbox") is None:
        return _skip(
            "chatterbox",
            "chatterbox",
            "Chatterbox package is not installed; install optional dependency with 'pip install chatterbox-tts'",
            heavy=True,
            experimental=True,
        )

    script_path = Path(__file__).resolve().parent.parent / "scripts" / "run_chatterbox_tts.py"
    output_path = output_dir / "chatterbox.wav"
    return TTSBenchmarkPlan(
        backend="chatterbox",
        selected_backend="chatterbox",
        command=[
            sys.executable,
            str(script_path),
            "--text",
            text,
            "--output",
            str(output_path),
            "--language",
            CHATTERBOX_LANGUAGE,
            "--t3-model",
            CHATTERBOX_T3_MODEL,
        ],
        output_path=output_path,
        timeout_seconds=CHATTERBOX_TIMEOUT_SECONDS,
        backend_status=(
            f"chatterbox t3_model={CHATTERBOX_T3_MODEL}, language={CHATTERBOX_LANGUAGE}, device=auto"
        ),
        heavy=True,
        experimental=True,
    )


def _copy_plan_for_backend(plan: TTSBenchmarkPlan, *, backend: str, status_suffix: str) -> TTSBenchmarkPlan:
    output_path = plan.output_path.with_name(f"{backend}-{plan.output_path.name}")
    return TTSBenchmarkPlan(
        backend=backend,
        selected_backend=plan.selected_backend,
        command=_replace_command_value(plan.command, old=str(plan.output_path), new=str(output_path)),
        output_path=output_path,
        stdin_text=plan.stdin_text,
        timeout_seconds=plan.timeout_seconds,
        backend_status=f"{plan.backend_status}; {status_suffix}",
        heavy=plan.heavy,
        experimental=plan.experimental,
    )


def _execute_plan(plan: TTSBenchmarkPlan) -> ProcessTiming:
    plan.output_path.unlink(missing_ok=True)
    started = time.perf_counter()
    process = subprocess.Popen(
        plan.command,
        stdin=subprocess.PIPE if plan.stdin_text is not None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    first_audio_at: float | None = None
    if plan.stdin_text is not None and process.stdin is not None:
        process.stdin.write(plan.stdin_text)
        process.stdin.close()

    while process.poll() is None:
        elapsed = time.perf_counter() - started
        if elapsed > plan.timeout_seconds:
            process.kill()
            process.wait(timeout=5)
            raise RuntimeError(f"backend timed out after {plan.timeout_seconds} seconds")
        if first_audio_at is None and _audio_file_started(plan.output_path):
            first_audio_at = time.perf_counter()
        time.sleep(0.01)

    finished = time.perf_counter()
    if process.returncode != 0:
        raise RuntimeError(f"process exited with {process.returncode}")
    if first_audio_at is None and _audio_file_started(plan.output_path):
        first_audio_at = finished
    if not plan.output_path.exists():
        raise RuntimeError("backend completed without creating an audio artifact")
    return ProcessTiming(
        time_to_first_audio_ms=(first_audio_at - started) * 1000 if first_audio_at is not None else None,
        total_synthesis_ms=(finished - started) * 1000,
    )


def _audio_file_started(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size > 0
    except OSError:
        return False


def _resolve_command(command_name: str) -> str | None:
    candidate = Path(command_name).expanduser()
    if candidate.exists():
        return str(candidate)
    return shutil.which(command_name)


def _replace_command_value(command: list[str], *, old: str, new: str) -> list[str]:
    return [new if item == old else item for item in command]


def _skip(
    backend: str,
    selected_backend: str,
    reason: str,
    *,
    heavy: bool = False,
    experimental: bool = False,
) -> TTSBenchmarkResult:
    return TTSBenchmarkResult(
        backend=backend,
        status="SKIP",
        selected_backend=selected_backend,
        backend_status=reason,
        failure_reason=reason,
        heavy=heavy,
        experimental=experimental,
    )


def _format_ms(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.0f} ms"
    return "n/a"


def _round_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)
