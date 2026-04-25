from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reddit_rag.rag.query_templates import (
    QueryTemplateError,
    get_template_by_id,
    load_query_template_file,
    load_query_templates,
    validate_required_templates,
)


def _repo_query_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "query_templates"


class TestQueryTemplates(unittest.TestCase):
    def test_load_one_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.md"
            p.write_text(
                "---\nid: my-tpl\ntitle: T\ncategory: vocabulary\n---\n\nHello body.\n",
                encoding="utf-8",
            )
            t = load_query_template_file(p)
            self.assertEqual(t.id, "my-tpl")
            self.assertEqual(t.title, "T")
            self.assertEqual(t.category, "vocabulary")
            self.assertEqual(t.prompt, "Hello body.")

    def test_rejects_bad_category(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.md"
            p.write_text("---\nid: a\ntitle: A\ncategory: not_a_real_cat\n---\n\nBody.\n", encoding="utf-8")
            with self.assertRaises(QueryTemplateError):
                load_query_template_file(p)

    def test_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text(
                "---\nid: dup\ntitle: A\ncategory: themes\n---\n\nOne.\n", encoding="utf-8"
            )
            (root / "b.md").write_text(
                "---\nid: dup\ntitle: B\ncategory: themes\n---\n\nTwo.\n", encoding="utf-8"
            )
            with self.assertRaises(QueryTemplateError):
                load_query_templates(root)

    def test_get_template_by_id(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "z.md").write_text(
                "---\nid: zed\ntitle: Z\ncategory: faqs\n---\n\nZ body.\n", encoding="utf-8"
            )
            t = get_template_by_id(root, "zed")
            self.assertEqual(t.prompt, "Z body.")

    def test_validate_required_templates(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for tid, cat in [
                ("pain-points", "pain_points"),
                ("emotional-drivers", "emotional_drivers"),
                ("objections", "objections"),
                ("vocabulary", "vocabulary"),
                ("faqs", "faqs"),
            ]:
                (root / f"{tid}.md").write_text(
                    f"---\nid: {tid}\ntitle: {tid}\ncategory: {cat}\n---\n\nBody.\n",
                    encoding="utf-8",
                )
            ts = load_query_templates(root)
            validate_required_templates(ts)

    def test_validate_required_templates_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "only.md").write_text(
                "---\nid: only\ntitle: O\ncategory: themes\n---\n\nBody.\n", encoding="utf-8"
            )
            ts = load_query_templates(root)
            with self.assertRaises(QueryTemplateError) as ctx:
                validate_required_templates(ts)
            self.assertIn("pain-points", str(ctx.exception))

    def test_bundled_repo_templates(self) -> None:
        root = _repo_query_templates_dir()
        if not root.is_dir():
            self.skipTest("bundled config/query_templates not present")
        ts = load_query_templates(root)
        validate_required_templates(ts)


if __name__ == "__main__":
    unittest.main()
