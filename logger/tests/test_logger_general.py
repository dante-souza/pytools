"""Broad offline test suite, standard unittest, no network or SDK imports."""
from __future__ import annotations

import contextlib
import io
import json
import math
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from logger_general import (
    DisplayOptions, GeneralLogger, JsonlWriter, _segments, _use_color,
    highlight_log_line, main, print_json, render_json, render_json_html,
    run_selftest, view_file,
)

ANSI = re.compile(r"\x1b\[[0-9;]*m")


class JsonRenderingTests(unittest.TestCase):
    def test_roundtrip_all_json_types(self):
        value = {"a": "café 🐋", "num": 0, "negative": -0.23,
                 "exp": 1.2e-13, "boolean": True, "off": False, "nil": None,
                 "nested": [1, "2", {"k": "v"}]}
        self.assertEqual(json.loads(render_json(value, color="never")), value)

    def test_indentation_and_utf8(self):
        result = render_json({"coração": "ação"}, color="never", indent=4)
        self.assertIn('    "coração": "ação"', result)
        self.assertNotIn("\\u00e7", result)

    def test_compact_json_can_still_be_highlighted(self):
        item = {"n": 1.23, "flag": True, "status": "failed"}
        colored = render_json(item, pretty=False, color="always")
        self.assertIn('\033[96m1.23\033[0m', colored)
        self.assertIn('\033[95mtrue\033[0m', colored)
        self.assertIn('\033[91m"failed"\033[0m', colored)
        self.assertEqual(json.loads(ANSI.sub("", colored)), item)

    def test_no_color_produces_identical_serialization(self):
        item = {"status": "denied", "text": "a\nb", "integer": -8}
        self.assertEqual(
            render_json(item, pretty=True, color="never"),
            json.dumps(item, ensure_ascii=False, indent=2, allow_nan=False),
        )

    def test_strings_containing_json_keywords_are_not_boolean_tokens(self):
        colored = render_json({"s": "true false null 123"}, color="always")
        self.assertIn('\033[93m"true false null 123"\033[0m', colored)
        self.assertEqual(json.loads(ANSI.sub("", colored)), {"s": "true false null 123"})

    def test_escaped_quotation_and_backslash(self):
        item = {"escaped": 'A "quoted" \\ path', "backslash": "\\u1234"}
        self.assertEqual(json.loads(ANSI.sub("", render_json(item, color="always"))), item)

    def test_empty_lists_and_nested_values(self):
        item = {"nested": {"status": "success", "items": []}, "other": [None, 2.4]}
        encoded = render_json(item, color="always")
        self.assertEqual(json.loads(ANSI.sub("", encoded)), item)
        self.assertIn('\033[92m"success"\033[0m', encoded)

    def test_semantic_deny_error_success(self):
        result = render_json({"status": "denied", "result": "success",
                              "resultado": "erro", "severity": "critical"}, color="always")
        self.assertIn('\033[93m"denied"\033[0m', result)
        self.assertIn('\033[92m"success"\033[0m', result)
        self.assertIn('\033[91m"erro"\033[0m', result)
        self.assertIn('\033[91m"critical"\033[0m', result)

    def test_not_every_string_value_is_semantic(self):
        result = render_json({"message": "denied", "status": "denied"}, color="always")
        self.assertIn('\033[93m"denied"\033[0m', result)  # same visible color palette
        # Custom flag not inherited by unconfigured field.
        marker = render_json({"message": "failed"}, color="always")
        self.assertIn('\033[93m"failed"\033[0m', marker)

    def test_custom_semantic_rule_for_application_fields(self):
        rules = {"deployment": {"ROLLBACK": "error", "deployed": "success"}}
        self.assertIn('\033[91m"rollback"\033[0m',
                      render_json({"deployment": "rollback"}, color="always", semantic_rules=rules))
        self.assertIn('\033[92m"deployed"\033[0m',
                      render_json({"deployment": "deployed"}, color="always", semantic_rules=rules))

    def test_invalid_style_not_injected(self):
        with self.assertRaises(ValueError):
            render_json({"status": "ready"}, color="always",
                        semantic_rules={"status": {"ready": "\033[999m"}})

    def test_invalid_color_mode(self):
        with self.assertRaises(ValueError):
            render_json({"x": 1}, color="pink")

    def test_negative_indent(self):
        with self.assertRaises(ValueError):
            render_json({}, indent=-1)

    def test_strict_nan_is_rejected(self):
        with self.assertRaises(ValueError):
            render_json({"x": math.nan}, color="never")

    def test_json_default_serializer_hook(self):
        self.assertEqual(json.loads(render_json({"x": {1, 2}}, color="never",
                                                default=lambda x: sorted(x))), {"x": [1, 2]})

    def test_print_json_stream(self):
        out = io.StringIO()
        print_json({"status": "ok"}, stream=out, color="never")
        self.assertEqual(json.loads(out.getvalue()), {"status": "ok"})

    def test_html_escaping_protects_jupyter_output(self):
        text = render_json_html({"status": "error", "s": '<script onload="go()">&</script>'})
        self.assertIn("&lt;script", text)
        self.assertIn("&amp;", text)
        self.assertNotIn('<script onload=', text)
        self.assertIn("style=", text)
        self.assertIn("<pre", text)
        self.assertIn('color:#fca5a5', text)

    def test_html_custom_semantic(self):
        text = render_json_html({"phase": "ready"}, semantic_rules={"phase": {"ready": "success"}})
        self.assertIn('color:#86efac', text)

    def test_auto_color_respects_no_color_environment(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(_use_color("auto", io.StringIO()))
            self.assertTrue(_use_color("always", io.StringIO()))


class JsonlAndViewerTests(unittest.TestCase):
    def test_jsonl_writer_preserves_compact_plain_files(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "nested" / "a.jsonl"
            with JsonlWriter(file) as writer:
                writer.write({"status": "denied", "unicode": "maçã"})
                writer.write([1, False, None])
            content = file.read_text(encoding="utf-8")
            self.assertEqual(len(content.splitlines()), 2)
            self.assertIn("maçã", content)
            self.assertNotIn("\033[", content)
            self.assertEqual([json.loads(x) for x in content.splitlines()],
                             [{"status": "denied", "unicode": "maçã"}, [1, False, None]])

    def test_jsonl_writer_rejects_invalid_float_without_partial_line(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.jsonl"
            with JsonlWriter(file) as writer:
                with self.assertRaises(ValueError):
                    writer.write({"bad": math.inf})
            self.assertEqual(file.read_bytes(), b"")

    def test_jsonl_writer_raises_after_close(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = JsonlWriter(Path(directory) / "file.jsonl")
            writer.close()
            with self.assertRaises(RuntimeError):
                writer.write({"x": 3})

    def test_plain_file_bytes_unchanged_after_pretty_view(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.jsonl"
            file.write_text('{"status":"denied"}\n{"status":"success","n":1.25}\n', encoding="utf-8")
            before = file.read_bytes()
            out = io.StringIO()
            count = view_file(file, stream=out, color="always", pretty=True)
            self.assertEqual(count, 2)
            self.assertIn("\033[", out.getvalue())
            self.assertIn("Record 0002", out.getvalue())
            self.assertEqual(file.read_bytes(), before)

    def test_no_color_still_pretty_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.jsonl"
            file.write_text('{"level":"WARNING","n":5}\n', encoding="utf-8")
            out = io.StringIO()
            view_file(file, stream=out, color="never", pretty=True)
            self.assertIn('  "level": "WARNING",', out.getvalue())
            self.assertNotIn("\033[", out.getvalue())

    def test_invalid_json_line_warns_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.jsonl"
            file.write_text('{"a": 1}\n{"invalid":\n{"b": 2}\n', encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            count = view_file(file, stream=out, error_stream=err,
                              color="never", pretty=True)
            self.assertEqual(count, 2)
            self.assertIn("line 2", err.getvalue())
            self.assertIn("Record 0002", out.getvalue())
            self.assertIn('{"invalid":', out.getvalue())

    def test_empty_lines_ignored_without_false_records(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.ndjson"
            file.write_text('\n{"ok":true}\n\n', encoding="utf-8")
            self.assertEqual(view_file(file, stream=io.StringIO(), color="never"), 1)

    def test_json_file_whole_document(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "sample.json"
            file.write_text(json.dumps({"nested": [True, {"status": "error"}]}), encoding="utf-8")
            out = io.StringIO()
            self.assertEqual(view_file(file, stream=out, color="never"), 1)
            self.assertIn('"status": "error"', out.getvalue())

    def test_jsonl_compact_remains_valid_after_ansi_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.jsonl"
            data = {"n": 4.75, "enabled": False}
            file.write_text(json.dumps(data) + "\n", encoding="utf-8")
            out = io.StringIO()
            view_file(file, stream=out, color="always", pretty=False)
            self.assertEqual(json.loads(ANSI.sub("", out.getvalue())), data)

    def test_missing_file_returns_clean_error_from_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["view", "nonexistent_123.jsonl"])
        self.assertEqual(code, 2)
        self.assertIn("[ERROR]", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_human_log_colors_without_modifying_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "a.log"
            file.write_text("2026-10-16 | WARNING  | Be careful\n", encoding="utf-8")
            out = io.StringIO()
            view_file(file, stream=out, color="always", pretty=True)
            self.assertIn("\033[93m", out.getvalue())
            plain = io.StringIO()
            view_file(file, stream=plain, color="never", pretty=True)
            self.assertEqual(plain.getvalue(), file.read_text(encoding="utf-8"))


class GeneralLoggerTests(unittest.TestCase):
    def test_file_is_plain_when_console_colored(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "messages.log"
            stream = io.StringIO()
            with GeneralLogger(stream=stream, color="always", log_file=target) as logger:
                logger.debug("ignored")
                logger.info("start")
                logger.warning("something")
                logger.error("oops")
                logger.critical("last")
            self.assertNotIn("ignored", stream.getvalue())
            self.assertIn("\033[92m", stream.getvalue())
            self.assertIn("\033[93m", stream.getvalue())
            self.assertIn("\033[91m", stream.getvalue())
            self.assertNotIn("\033[", target.read_text(encoding="utf-8"))

    def test_instances_do_not_share_handlers(self):
        one, two = io.StringIO(), io.StringIO()
        with GeneralLogger(stream=one, color="never", name="same") as a:
            with GeneralLogger(stream=two, color="never", name="same") as b:
                a.info("only one")
                b.error("only two")
        self.assertNotIn("only two", one.getvalue())
        self.assertNotIn("only one", two.getvalue())

    def test_closed_instance_rejects_logs(self):
        logger = GeneralLogger(stream=io.StringIO())
        logger.close()
        logger.close()
        with self.assertRaises(RuntimeError):
            logger.info("later")

    def test_log_input_cannot_inject_ansi(self):
        log = io.StringIO()
        with GeneralLogger(stream=log, color="never") as logger:
            logger.warning("oops \033[31minjected\033[0m")
        self.assertNotIn("\033[", log.getvalue())
        self.assertIn("injected", log.getvalue())

    def test_level_validation(self):
        with self.assertRaises(ValueError):
            GeneralLogger(level="VERBOSE")

    def test_log_in_test_stream(self):
        stream = io.StringIO()
        with GeneralLogger(stream=stream, color="never", level="DEBUG") as logger:
            logger.debug("debug run")
        self.assertIn("debug run", stream.getvalue())


class RuntimeTests(unittest.TestCase):
    def test_runtime_selftest_function(self):
        target = io.StringIO()
        with contextlib.redirect_stdout(target):
            run_selftest(color="never")
        self.assertIn("[SELFTEST PASS]", target.getvalue())

    def test_main_runtime_selftest(self):
        target = io.StringIO()
        with contextlib.redirect_stdout(target):
            result = main(["selftest", "--color", "never"])
        self.assertEqual(result, 0)

    def test_display_options_is_immutable(self):
        opts = DisplayOptions(color="always", indent=4)
        self.assertEqual(opts.indent, 4)
        with self.assertRaises(Exception):
            opts.indent = 2


if __name__ == "__main__":
    unittest.main()
