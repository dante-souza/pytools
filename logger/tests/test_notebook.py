"""Notebook can be opened and its two sample HTML outputs are safe and colorful."""
import json
import unittest
from pathlib import Path


class NotebookTests(unittest.TestCase):
    def test_notebook_contains_rendered_html_previews(self):
        root = Path(__file__).resolve().parents[1]
        nb = json.loads((root / "notebooks" / "logger_general_exemplos.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(nb["nbformat"], 4)
        self.assertGreaterEqual(len(nb["cells"]), 10)
        rich = []
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                for output in cell.get("outputs", []):
                    if "text/html" in output.get("data", {}):
                        rich.append("".join(output["data"]["text/html"]))
        self.assertGreaterEqual(len(rich), 2)
        self.assertTrue(all("<pre" in output and "style=" in output for output in rich))
        self.assertTrue(all("<script" not in output for output in rich))


if __name__ == "__main__":
    unittest.main()
