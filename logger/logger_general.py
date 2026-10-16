"""Portable, single-file logger + JSON/JSONL syntax and semantic highlighter.

Python >= 3.10; no runtime dependencies beyond the standard library.
No application-specific tracing, policy, networking, API SDK, or global logger.

Public API:
    GeneralLogger, JsonlWriter, render_json, render_json_html,
    view_file, print_json, highlight_log_line, run_selftest, main.

To reuse: copy ONLY logger_general.py into another Python project.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, TextIO

__version__ = "1.0.0"

_RESET = "\033[0m"
_ANSI = {
    "key": "\033[94m",       # bright blue
    "string": "\033[93m",    # bright yellow
    "number": "\033[96m",    # bright cyan
    "boolean": "\033[95m",   # bright magenta
    "null": "\033[90m",      # bright black / grey
    "success": "\033[92m",   # bright green
    "warning": "\033[93m",   # bright yellow
    "error": "\033[91m",     # bright red
    "debug": "\033[94m",
    "info": "\033[92m",
    "critical": "\033[91m",
}
_HTML = {
    "key": "#93c5fd", "string": "#fde68a", "number": "#67e8f9",
    "boolean": "#d8b4fe", "null": "#94a3b8", "success": "#86efac",
    "warning": "#facc15", "error": "#fca5a5", "debug": "#93c5fd",
    "info": "#86efac", "critical": "#fca5a5",
}
# Only recognized CSS/ANSI styles are accepted in semantic customization.
_STYLES = frozenset(_ANSI)
_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_LOG_LEVEL = re.compile(r"\|\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\|")
_JSON_TOKEN = re.compile(
    r'(?P<string>"(?:\\.|[^"\\])*")(?P<colon>\s*:)?'
    r'|(?P<number>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)'
    r'|(?P<literal>\b(?:true|false|null)\b)'
)
_DEFAULT_SEMANTIC_KEYS = frozenset(
    ("level", "severity", "status", "state", "result", "resultado", "outcome")
)
_DEFAULT_SEMANTIC_VALUES = {
    "ok": "success", "passed": "success", "success": "success",
    "sucesso": "success", "autorizado": "success", "authorized": "success",
    "completed": "success", "info": "success",
    "denied": "warning", "negado": "warning", "warning": "warning",
    "warn": "warning", "pending": "warning", "blocked": "warning",
    "error": "error", "erro": "error", "failed": "error",
    "failure": "error", "falha": "error", "critical": "error",
}


@dataclass(frozen=True)
class DisplayOptions:
    """Presentation preferences. No interaction with the logging subsystem."""

    color: str = "auto"      # auto | always | never
    indent: int = 2
    pretty: bool = True
    semantic_rules: Mapping[str, Mapping[str, str]] | None = None


def _use_color(setting: str, stream: TextIO | None = None) -> bool:
    if setting not in ("auto", "always", "never"):
        raise ValueError("color must be 'auto', 'always' or 'never'")
    if setting == "always":
        return True
    if setting == "never" or "NO_COLOR" in os.environ:
        return False
    target = sys.stdout if stream is None else stream
    return bool(getattr(target, "isatty", lambda: False)()) or "ipykernel" in sys.modules


def _rule_style(key: str | None, value: str,
                rules: Mapping[str, Mapping[str, str]] | None) -> str | None:
    if key is None:
        return None
    key_low, value_low = key.casefold(), value.casefold()
    # User-provided field rules have priority; values are named styles, not raw ANSI/HTML.
    if rules:
        for field, mapping in rules.items():
            if field.casefold() == key_low:
                for target, style in mapping.items():
                    if target.casefold() == value_low:
                        if style not in _STYLES:
                            raise ValueError(f"invalid semantic style: {style!r}")
                        return style
    if key_low in _DEFAULT_SEMANTIC_KEYS:
        return _DEFAULT_SEMANTIC_VALUES.get(value_low)
    return None


def _segments(document: str,
              rules: Mapping[str, Mapping[str, str]] | None = None
              ) -> Iterator[tuple[str, str | None]]:
    """Yield JSON text fragments and color roles, preserving all original bytes.

    A string token followed by ':' is a *key*. Other strings are values.
    Values get semantic coloring only if their enclosing key is configured.
    """
    end = 0
    current_key: str | None = None
    for found in _JSON_TOKEN.finditer(document):
        if found.start() > end:
            yield document[end:found.start()], None
        if found.group("string") is not None:
            token = found.group("string")
            colon = found.group("colon")
            if colon is not None:
                current_key = json.loads(token)
                yield token, "key"
                yield colon, None
            else:
                value = json.loads(token)
                yield token, _rule_style(current_key, value, rules) or "string"
                current_key = None
        elif found.group("number") is not None:
            yield found.group("number"), "number"
            current_key = None
        else:
            token = found.group("literal")
            yield token, "null" if token == "null" else "boolean"
            current_key = None
        end = found.end()
    if end < len(document):
        yield document[end:], None


def _decorate(document: str, *, color: str, stream: TextIO | None,
              semantic_rules: Mapping[str, Mapping[str, str]] | None) -> str:
    if not _use_color(color, stream):
        return document
    return "".join(
        f"{_ANSI[style]}{fragment}{_RESET}" if style else fragment
        for fragment, style in _segments(document, semantic_rules)
    )


def render_json(
    value: Any, *, pretty: bool = True, indent: int = 2,
    color: str = "auto", stream: TextIO | None = None,
    semantic_rules: Mapping[str, Mapping[str, str]] | None = None,
    default: Callable[[Any], Any] | None = None,
) -> str:
    """Return a correctly serialized JSON string with optional ANSI highlighting.

    Callers keep control of data and persistence. `default` is the standard
    json.dumps serializer hook for non-JSON-native Python objects.
    """
    if indent < 0:
        raise ValueError("indent cannot be negative")
    text = json.dumps(
        value, ensure_ascii=False, allow_nan=False,
        indent=indent if pretty else None,
        separators=None if pretty else (",", ":"), default=default,
    )
    return _decorate(text, color=color, stream=stream, semantic_rules=semantic_rules)


def render_json_html(
    value: Any, *, pretty: bool = True, indent: int = 2,
    semantic_rules: Mapping[str, Mapping[str, str]] | None = None,
    default: Callable[[Any], Any] | None = None,
) -> str:
    """Return safe <pre> HTML for IPython.display.HTML (no IPython dependency).

    All source data is HTML-escaped before insertion; color style names are
    mapped to a fixed allowlisted palette. This works without terminal ANSI.
    """
    raw = render_json(value, pretty=pretty, indent=indent, color="never", default=default)
    spans = []
    for fragment, style in _segments(raw, semantic_rules):
        escaped = html.escape(fragment, quote=True)
        spans.append(f'<span style="color:{_HTML[style]}">{escaped}</span>' if style else escaped)
    return (
        '<pre style="background:#0f172a;color:#e2e8f0;'
        'border:1px solid #334155;border-radius:8px;'
        'padding:16px;overflow-x:auto;white-space:pre-wrap;'
        'font:13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace">'
        + "".join(spans) + "</pre>"
    )


def print_json(value: Any, *, stream: TextIO | None = None, **options: Any) -> None:
    """Write one rendered JSON document to a stream (default: stdout)."""
    target = stream or sys.stdout
    target.write(render_json(value, stream=target, **options) + "\n")


def _sanitize_log(message: str) -> str:
    # The logger never copies user-supplied CSI escape sequences into logs.
    return _ANSI_ESCAPE.sub("", str(message))


class _LogFormatter(logging.Formatter):
    def __init__(self, colored: bool) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.colored = colored

    def format(self, record: logging.LogRecord) -> str:
        result = _sanitize_log(super().format(record))
        if not self.colored:
            return result
        role = {"WARNING": "warning", "ERROR": "error", "CRITICAL": "critical",
                "DEBUG": "debug", "INFO": "info"}.get(record.levelname, "info")
        return f"{_ANSI[role]}{result}{_RESET}"


class GeneralLogger:
    """Independent text logger with colored terminal and permanently plain files.

    Creates a private logging.Logger instance, never touching root logging or
    handler lists shared with other libraries. Can be used as a context manager.
    """

    def __init__(
        self, *, name: str = "app", level: str = "INFO", color: str = "auto",
        stream: TextIO | None = None, log_file: str | Path | None = None,
        console: bool = True,
    ) -> None:
        self.stream = sys.stderr if stream is None else stream
        self.color = color
        self._closed = False
        self._logger = logging.Logger(name)
        level_number = logging.getLevelName(level.upper())
        if not isinstance(level_number, int):
            raise ValueError(f"unknown log level: {level!r}")
        self._logger.setLevel(level_number)
        self._logger.propagate = False
        self._handlers: list[logging.Handler] = []
        if console:
            handler = logging.StreamHandler(self.stream)
            handler.setFormatter(_LogFormatter(_use_color(color, self.stream)))
            self._attach(handler)
        if log_file is not None:
            path = Path(log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(path, encoding="utf-8")
            handler.setFormatter(_LogFormatter(False))
            self._attach(handler)

    def _attach(self, handler: logging.Handler) -> None:
        self._logger.addHandler(handler)
        self._handlers.append(handler)

    def log(self, level: str, message: Any) -> None:
        if self._closed:
            raise RuntimeError("GeneralLogger is closed")
        number = logging.getLevelName(level.upper())
        if not isinstance(number, int):
            raise ValueError(f"unknown log level: {level!r}")
        self._logger.log(number, _sanitize_log(str(message)))

    def debug(self, message: Any) -> None:
        self.log("DEBUG", message)

    def info(self, message: Any) -> None:
        self.log("INFO", message)

    def warning(self, message: Any) -> None:
        self.log("WARNING", message)

    def error(self, message: Any) -> None:
        self.log("ERROR", message)

    def critical(self, message: Any) -> None:
        self.log("CRITICAL", message)

    def exception(self, message: Any) -> None:
        """Log traceback when called inside an except block."""
        if self._closed:
            raise RuntimeError("GeneralLogger is closed")
        self._logger.exception(_sanitize_log(str(message)))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for handler in self._handlers:
            self._logger.removeHandler(handler)
            handler.close()
        self._handlers.clear()

    def __enter__(self) -> "GeneralLogger":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


class JsonlWriter:
    """Append JSON-native Python values as one uncolored JSON record per line.

    Intentionally independent of GeneralLogger. Single-process writer;
    concurrency, rotation and retention belong to the embedding application.
    """

    def __init__(self, path: str | Path, *, flush: bool = True,
                 default: Callable[[Any], Any] | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", encoding="utf-8", newline="\n")
        self._flush = flush
        self._default = default

    def write(self, value: Any) -> None:
        if self._file.closed:
            raise RuntimeError("JsonlWriter is closed")
        text = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False, default=self._default,
        )
        self._file.write(text + "\n")
        if self._flush:
            self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "JsonlWriter":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


def highlight_log_line(line: str, *, color: str = "auto",
                       stream: TextIO | None = None) -> str:
    """Color whole human-log lines by DEBUG/INFO/WARNING/ERROR/CRITICAL."""
    plain = _sanitize_log(line)
    matched = _LOG_LEVEL.search(plain)
    if not matched or not _use_color(color, stream):
        return plain
    role = {"DEBUG": "debug", "INFO": "info", "WARNING": "warning",
            "ERROR": "error", "CRITICAL": "critical"}[matched.group(1)]
    body = plain.rstrip("\r\n")
    return f"{_ANSI[role]}{body}{_RESET}{plain[len(body):]}"


def _kind(path: Path, requested: str) -> str:
    if requested not in ("auto", "json", "jsonl", "log"):
        raise ValueError("kind must be auto, json, jsonl or log")
    if requested != "auto":
        return requested
    if path.suffix.lower() == ".json":
        return "json"
    if path.suffix.lower() in (".jsonl", ".ndjson"):
        return "jsonl"
    return "log"


def _heading(value: Any, index: int, *, use_ansi: bool) -> str:
    label = f"Record {index:04d}"
    style = None
    if isinstance(value, dict):
        for key in ("severity", "level", "status", "result", "resultado", "outcome"):
            if key in value and isinstance(value[key], str):
                state = value[key]
                label += f" — {key}: {state}"
                style = _rule_style(key, state, None)
                break
    # Avoid escape/control injection through labels sourced from untrusted files.
    label = _sanitize_log(label).replace("\r", r"\r").replace("\n", r"\n")
    if use_ansi and style:
        return f"{_ANSI[style]}{label}{_RESET}"
    return label


def view_file(
    path: str | Path, *, kind: str = "auto", pretty: bool = True,
    color: str = "auto", stream: TextIO | None = None,
    error_stream: TextIO | None = None, headings: bool = True,
    indent: int = 2,
    semantic_rules: Mapping[str, Mapping[str, str]] | None = None,
) -> int:
    """Display .json, .jsonl/.ndjson, or .log, never modifying their bytes.

    JSONL is streamed line by line. On invalid JSONL, warns with line number,
    prints the original line, and continues. Returns number of valid JSON
    records (or displayed log lines).
    """
    target = sys.stdout if stream is None else stream
    errors = sys.stderr if error_stream is None else error_stream
    source = Path(path)
    detected = _kind(source, kind)
    count = 0
    if detected == "json":
        # Unlike JSONL, a complete .json document must be parsed as a unit.
        with source.open("r", encoding="utf-8") as fh:
            parsed = json.load(fh)
        target.write(render_json(parsed, pretty=pretty, indent=indent,
                                 color=color, stream=target,
                                 semantic_rules=semantic_rules) + "\n")
        return 1
    with source.open("r", encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if detected == "log":
                target.write(highlight_log_line(line, color=color, stream=target))
                count += 1
                continue
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.write(f"[WARN] Invalid JSON on line {number} of {source.name}: {exc.msg}\n")
                target.write(_sanitize_log(line))
                continue
            count += 1
            if pretty and headings:
                target.write(_heading(parsed, count,
                                      use_ansi=_use_color(color, target)) + "\n")
            target.write(render_json(parsed, pretty=pretty, indent=indent,
                                     color=color, stream=target,
                                     semantic_rules=semantic_rules) + "\n")
    return count


def run_demo(*, color: str = "always") -> None:
    """Executable demo with genuine logging, JSON syntax, and JSONL workflow."""
    data = [
        {"id": 1, "level": "INFO", "status": "success", "count": 3,
         "enabled": True, "duration_ms": 1.25, "note": "ação concluída", "extra": None},
        {"id": 2, "level": "WARNING", "status": "denied", "reason": "access denied"},
        {"id": 3, "level": "ERROR", "status": "failed", "detail": {"retry": False}},
    ]
    with tempfile.TemporaryDirectory(prefix="logger-general-") as folder:
        base = Path(folder)
        with GeneralLogger(name="demo", color=color, log_file=base / "example.log") as logger:
            logger.info("Independent logger initialized")
            logger.warning("This is an example warning")
            logger.error("This is an example error")
        with JsonlWriter(base / "events.jsonl") as writer:
            for record in data:
                writer.write(record)
        print("\n--- JSONL: streaming + pretty + syntax/semantic colors ---")
        view_file(base / "events.jsonl", color=color, pretty=True)
        print("\n--- Plain log recolored at reading time ---")
        view_file(base / "example.log", color=color)
        saved = (base / "events.jsonl").read_text(encoding="utf-8")
        assert "\033[" not in saved, "JSONL unexpectedly contains ANSI"
        assert len(saved.splitlines()) == 3
        print("\n[DEMO PASS] Original files remain ANSI-free; no app dependencies.")


def run_selftest(*, color: str = "always") -> None:
    """Fast, assertion-based runtime checks, also executed by make smoke."""
    sample = {"status": "denied", "note": "<script>alert('x')</script>",
              "accent": "ação", "n": 123, "x": None, "list": [True, False]}
    plain = render_json(sample, color="never")
    ansi = render_json(sample, color="always")
    markup = render_json_html(sample)
    assert json.loads(plain) == sample
    assert "\033[" not in plain
    assert "\033[" in ansi
    assert "\033[93m\"denied\"\033[0m" in ansi
    assert "<script>" not in markup and "&lt;script&gt;" in markup
    assert "ação" in plain and "ação" in markup
    with tempfile.TemporaryDirectory(prefix="logger-general-test-") as folder:
        root = Path(folder)
        jl, log = root / "test.jsonl", root / "test.log"
        with JsonlWriter(jl) as writer:
            writer.write(sample)
            writer.write({"status": "success"})
        original = jl.read_bytes()
        result, warns = io.StringIO(), io.StringIO()
        assert view_file(jl, stream=result, error_stream=warns,
                         color="never") == 2
        assert "Record 0002" in result.getvalue()
        assert jl.read_bytes() == original
        with GeneralLogger(stream=io.StringIO(), color="always", log_file=log) as logger:
            logger.warning("Test warning")
        assert "\033[" not in log.read_text(encoding="utf-8")
        assert "WARNING" in log.read_text(encoding="utf-8")
    print("[SELFTEST PASS] JSON/HTML/ANSI, JSONL, safety and logger lifecycle.")
    print_json({"result": "success", "checks": 8}, color=color)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Portable GeneralLogger + JSON/JSONL highlighter (stdlib only)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command", required=True)
    for action in ("demo", "selftest"):
        sub = subs.add_parser(action, help=f"Run {action} without external services")
        sub.add_argument("--color", choices=("auto", "always", "never"), default="always")
    viewer = subs.add_parser("view", help="Read existing JSON, JSONL, NDJSON or log")
    viewer.add_argument("file", help="Path to file")
    viewer.add_argument("--kind", choices=("auto", "json", "jsonl", "log"), default="auto")
    viewer.add_argument("--pretty", action="store_true")
    viewer.add_argument("--no-headings", action="store_true")
    viewer.add_argument("--color", choices=("auto", "always", "never"), default="always")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            run_demo(color=args.color)
        elif args.command == "selftest":
            run_selftest(color=args.color)
        else:
            view_file(args.file, kind=args.kind, pretty=args.pretty,
                      headings=not args.no_headings, color=args.color)
    except (OSError, ValueError, TypeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
