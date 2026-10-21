"""Cross-document audit: evidence, time scope, identity and markup regressions."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_audit as c


class ContextAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "a.md").write_text("# 실적\n\n윤대표의 누적 저서는 15권이다.\n", encoding="utf-8")
        (self.root / "b.md").write_text("# 소개\n\n윤영식의 누적 저서는 14권이다.\n", encoding="utf-8")
        self.m = {"version": 1, "documents": [{"id": "a", "path": "a.md"}, {"id": "b", "path": "b.md"}]}

    def claim(self, doc, value, **kw):
        return {"subject": "author", "predicate": "누적 저서", "value": value,
                "scope": "전체", "as_of": "2026-10", "evidence": {"document": doc,
                "quote": "누적 저서는 " + value + "이다."}, **kw}

    def test_clean(self):
        self.assertEqual(c.audit(self.m, self.root)["status"], "pass")

    def test_strict_does_not_block_minor_term_candidate(self):
        self.m["terms"] = [{"preferred": "윤영식", "variants": ["윤대표"]}]
        self.assertEqual(c.audit(self.m, self.root, strict=True)["status"], "warn")

    def test_malformed_manifest_is_input_error(self):
        with self.assertRaises(ValueError):
            c.audit([], self.root)
        self.m["terms"] = [{"preferred": "윤영식", "variants": "윤대표"}]
        with self.assertRaises(ValueError):
            c.audit(self.m, self.root)

    def test_literal_quote_does_not_claim_semantic_verification(self):
        item = self.claim("a", "15권")
        item["value"] = "999권"
        self.m["claims"] = [item]
        data = c.audit(self.m, self.root)
        self.assertTrue(data["claims"][0]["evidence"]["verified_literal"])
        self.assertIn("의미 추론을 하지 않습니다", data["limitations"])

    def test_term_location(self):
        self.m["terms"] = [{"preferred": "윤영식", "variants": ["윤대표"]}]
        item = c.audit(self.m, self.root)["findings"][0]["evidence"]
        self.assertEqual((item["line"], item["section"]), (3, ["실적"]))

    def test_reference_not_rewritten(self):
        self.m["documents"][0]["role"] = "reference"
        self.m["terms"] = [{"preferred": "윤영식", "variants": ["윤대표"]}]
        self.assertFalse(c.audit(self.m, self.root)["findings"])

    def test_markup_excluded_and_label_kept(self):
        text = "---\nname: typo\n---\n```py\ntypo\n```\n~~~\ntypo\n~~~\n`typo` https://typo.test\n> typo\n[typo](local/typo)\n<!-- typo -->"
        masked = c.prose(text)
        self.assertEqual(len(masked), len(text))
        self.assertEqual(masked.count("typo"), 1)

    def test_latin_boundary(self):
        self.assertEqual(len(list(c.occurrences("API APIs api", "API"))), 1)

    def test_aliases_indexed_without_forcing_replacement(self):
        self.m["entities"] = [{"id": "author", "name": "윤영식", "aliases": ["윤대표"]}]
        data = c.audit(self.m, self.root)
        self.assertEqual(len(data["entity_mentions"]["author"]), 2)
        self.assertFalse(data["findings"])

    def test_same_name_not_merged(self):
        self.m["entities"] = [{"id": "p1", "name": "김민수"}, {"id": "p2", "name": "김민수"}]
        self.assertEqual(c.audit(self.m, self.root, strict=True)["status"], "hold")

    def test_conflicting_claims(self):
        self.m["claims"] = [self.claim("a", "15권"), self.claim("b", "14권")]
        self.assertEqual(c.audit(self.m, self.root)["findings"][0]["id"], "CTX-CLAIM")

    def test_different_dates_are_not_conflicts(self):
        self.m["claims"] = [self.claim("a", "15권"), self.claim("b", "14권", as_of="2026-09")]
        self.assertFalse(c.audit(self.m, self.root)["findings"])

    def test_different_scopes_are_not_conflicts(self):
        self.m["claims"] = [self.claim("a", "15권"), self.claim("b", "14권", scope="단독 저서")]
        self.assertFalse(c.audit(self.m, self.root)["findings"])

    def test_unverifiable_quote(self):
        self.m["claims"] = [self.claim("a", "99권")]
        self.assertEqual(c.audit(self.m, self.root)["findings"][0]["id"], "CTX-EVIDENCE")

    def test_missing_file_is_error(self):
        self.m["documents"][0]["path"] = "absent.md"
        with self.assertRaises(OSError):
            c.audit(self.m, self.root)

    def test_duplicate_document_ids_rejected(self):
        self.m["documents"][1]["id"] = "a"
        with self.assertRaises(ValueError):
            c.audit(self.m, self.root)

    def test_hash_changes_with_source(self):
        before = c.audit(self.m, self.root)["documents"][0]["sha256"]
        (self.root / "a.md").write_text("수정", encoding="utf-8")
        self.assertNotEqual(before, c.audit(self.m, self.root)["documents"][0]["sha256"])

    def test_no_implicit_directory_scan(self):
        (self.root / "private.md").write_text("비공개 자료", encoding="utf-8")
        self.assertEqual(len(c.audit(self.m, self.root)["documents"]), 2)

    def test_cli_invalid_and_strict_exit(self):
        path = self.root / "manifest.json"
        path.write_text("{}", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main([str(path), "--json"]), 2)
        self.m["claims"] = [self.claim("a", "99권")]
        path.write_text(json.dumps(self.m), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main([str(path), "--strict", "--json"]), 1)


if __name__ == "__main__":
    unittest.main()
