"""Continuation must not reuse work after input/artifact/decision drift."""
import contextlib
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import translation_session as session


class TranslationSession(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.handoff = self.base / "handoff.json"
        self.data = json.loads((ROOT / "templates/writer-editor-handoff.json").read_text(encoding="utf-8"))
        self.source = self.base / "source.md"
        self.source.write_text("The bank may reopen.\n", encoding="utf-8")
        session.initialize(self.data, self.handoff, str(self.source))

    def artifact(self, name, text="작업 결과"):
        path = self.base / (name + ".md")
        path.write_text(text, encoding="utf-8")
        return path

    def step(self, stage):
        session.checkpoint(self.data, self.handoff, stage, str(self.artifact(stage)))

    def decision(self, state="adopted", target="은행", kind="term", text="bank"):
        session.record_decision(self.data, self.handoff, "bank", kind, text, target, state, "model", "금융 문맥의 작업상 선택")

    def test_first_unrecorded_step(self):
        result = session.inspect(self.data, self.base)
        self.assertEqual((result["status"], result["next_stage"]), ("ready", "analysis"))

    def test_checkpoint_resumes_without_redrafting(self):
        self.step("analysis")
        self.step("draft")
        result = session.inspect(self.data, self.base)
        self.assertEqual(result["next_stage"], "review")
        self.assertEqual(result["status"], "ready")

    def test_source_edit_invalidates_prior_work(self):
        self.step("analysis")
        self.source.write_text("The bank will reopen.\n", encoding="utf-8")
        result = session.inspect(self.data, self.base)
        self.assertIn("source_changed", result["input_changes"])
        self.assertEqual((result["status"], result["next_stage"]), ("stale", "analysis"))

    def test_missing_source_does_not_look_valid(self):
        self.source.unlink()
        self.assertIn("source_unavailable", session.inspect(self.data, self.base)["input_changes"])

    def test_glossary_change_invalidates(self):
        glossary = self.artifact("terms", "bank\t은행")
        session.initialize(self.data, self.handoff, glossary=str(glossary), refresh=True)
        glossary.write_text("bank\t강둑", encoding="utf-8")
        self.assertIn("glossary_changed", session.inspect(self.data, self.base)["input_changes"])

    def test_audience_change_invalidates(self):
        self.data["context"]["audience"] = "전문 번역가"
        self.assertIn("brief_changed", session.inspect(self.data, self.base)["input_changes"])

    def test_manual_settings_edit_invalidates(self):
        self.data[session.KEY]["settings"]["domain"] = "geography"
        self.assertIn("settings_or_binding_changed", session.inspect(self.data, self.base)["input_changes"])

    def test_changed_draft_requires_review_again(self):
        for stage in ("analysis", "draft", "review"):
            self.step(stage)
        (self.base / "draft.md").write_text("바뀐 번역", encoding="utf-8")
        result = session.inspect(self.data, self.base)
        self.assertEqual(result["next_stage"], "draft")
        self.assertFalse(result["stages"][2]["valid"])

    def test_missing_artifact_is_stale(self):
        self.step("analysis")
        (self.base / "analysis.md").unlink()
        self.assertEqual(session.inspect(self.data, self.base)["status"], "stale")

    def test_skip_unfinished_step_rejected(self):
        with self.assertRaises(ValueError):
            self.step("draft")

    def test_rerecord_invalidates_downstream_and_keeps_history(self):
        for stage in ("analysis", "draft", "review"):
            self.step(stage)
        self.step("draft")
        self.assertEqual(session.inspect(self.data, self.base)["next_stage"], "review")
        self.assertTrue(any("review" in h.get("stages", {}) for h in self.data[session.KEY]["history"]))

    def test_empty_artifact_does_not_delete_progress(self):
        self.step("analysis")
        before = deepcopy(self.data)
        with self.assertRaises(ValueError):
            session.checkpoint(self.data, self.handoff, "analysis", str(self.artifact("empty", " ")))
        self.assertEqual(self.data, before)

    def test_handoff_cannot_reference_itself(self):
        self.step("analysis")
        session.save(self.handoff, self.data)
        with self.assertRaises(ValueError):
            session.checkpoint(self.data, self.handoff, "draft", str(self.handoff))

    def test_handoff_cannot_be_its_own_glossary(self):
        session.save(self.handoff, self.data)
        with self.assertRaises(ValueError):
            session.initialize(self.data, self.handoff, glossary=str(self.handoff), refresh=True)

    def test_cross_drive_path_falls_back_to_absolute(self):
        with patch.object(session.os.path, "relpath", side_effect=ValueError("different drives")):
            record = session.file_record(self.source, self.base)
        self.assertEqual(Path(record["path"]), self.source.resolve())

    def test_delivery_contract_is_optional_but_checked(self):
        data = deepcopy(self.data)
        data.pop("delivery", None)
        self.assertTrue(session.handoff_data(json.dumps(data))["pass"])
        data["delivery"] = {"mode": "invalid"}
        self.assertFalse(session.handoff_data(json.dumps(data))["pass"])

    def test_invalid_arguments_are_input_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(session.main(["checkpoint", str(self.handoff)]), 3)

    def test_reinit_is_explicit(self):
        before = deepcopy(self.data)
        with self.assertRaises(ValueError):
            session.initialize(self.data, self.handoff, str(self.source))
        self.assertEqual(before, self.data)

    def test_refresh_keeps_other_handoff_fields(self):
        original = {k: deepcopy(v) for k, v in self.data.items() if k != session.KEY}
        self.step("analysis")
        session.initialize(self.data, self.handoff, refresh=True)
        self.assertEqual(original, {k:v for k,v in self.data.items() if k != session.KEY})
        self.assertEqual(self.data[session.KEY]["stages"], {})
        self.assertTrue(self.data[session.KEY]["history"])

    def test_old_decisions_not_auto_adopted_after_source_change(self):
        self.decision()
        self.source.write_text("The bank might close.", encoding="utf-8")
        session.initialize(self.data, self.handoff, refresh=True)
        result = session.inspect(self.data, self.base)
        self.assertEqual(result["usable_decisions"], [])
        self.assertEqual(len(result["reconsider_decisions"]), 1)

    def test_provisional_is_not_user_confirmed(self):
        self.decision(state="provisional")
        self.assertEqual(session.inspect(self.data, self.base)["usable_decisions"], [])
        row = self.data[session.KEY]["decisions"][0]
        self.assertEqual(row["owner"], "model")

    def test_adopted_decision_returned_with_scope_and_owner(self):
        self.decision()
        row = session.inspect(self.data, self.base)["usable_decisions"][0]
        self.assertEqual((row["target"], row["owner"]), ("은행", "model"))
        self.assertIn("scope", row)

    def test_deferred_decision_not_reused(self):
        self.decision(state="deferred")
        self.assertEqual(session.inspect(self.data, self.base)["usable_decisions"], [])

    def test_decision_cannot_import_unrelated_source(self):
        with self.assertRaises(ValueError):
            self.decision(text="a fabricated event")

    def test_changed_decision_invalidates_draft_not_analysis(self):
        self.step("analysis")
        self.step("draft")
        self.decision()
        result = session.inspect(self.data, self.base)
        self.assertEqual(result["next_stage"], "draft")
        self.assertTrue(result["stages"][0]["valid"])

    def test_reaffirm_identical_decision_does_not_repeat_work(self):
        self.decision()
        self.step("analysis")
        self.step("draft")
        self.decision()
        self.assertEqual(session.inspect(self.data, self.base)["next_stage"], "review")

    def test_manual_decision_edit_requires_redrafting(self):
        self.decision()
        self.step("analysis")
        self.step("draft")
        self.data[session.KEY]["decisions"][0]["target"] = "강둑"
        self.assertEqual(session.inspect(self.data, self.base)["next_stage"], "draft")

    def test_changed_source_blocks_checkpoint_and_decision(self):
        self.source.write_text("Something else.", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.step("analysis")
        with self.assertRaises(ValueError):
            self.decision()

    def test_all_stages_are_records_not_quality_certification(self):
        for stage in session.STAGES:
            self.step(stage)
        result = session.inspect(self.data, self.base)
        self.assertEqual(result["status"], "recorded")
        self.assertTrue(result["human_review_required"])
        self.assertIn("증명이 아닙니다", result["note"])

    def test_readonly_inspect_and_exit_status(self):
        session.save(self.handoff, self.data)
        before = self.handoff.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(session.main(["inspect", str(self.handoff), "--json"]), 0)
        self.assertEqual(self.handoff.read_bytes(), before)
        self.source.write_text("Changed", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(session.main(["inspect", str(self.handoff)]), 2)

    def test_invalid_json_leaves_file_untouched(self):
        self.handoff.write_text("{", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(session.main(["inspect", str(self.handoff)]), 3)
        self.assertEqual(self.handoff.read_text(encoding="utf-8"), "{")

    def test_installed_cli_and_script_dispatch(self):
        session.save(self.handoff, self.data)
        commands = [[sys.executable, "-m", "neo_korean_writing.cli", "translation-session"],
                    [sys.executable, str(ROOT / "scripts/korean_writing.py"), "translation-session"]]
        for prefix in commands:
            result = subprocess.run(prefix + ["inspect", str(self.handoff), "--json"], cwd=self.base,
                                    env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["next_stage"], "analysis")

    def test_cli_creates_and_resumes_persistent_session(self):
        self.data.pop(session.KEY)
        session.save(self.handoff, self.data)
        prefix = [sys.executable, str(ROOT / "scripts/translation_session.py")]
        def invoke(arguments, expected=0):
            proc = subprocess.run(prefix + arguments + ["--json"], cwd=self.base,
                                  capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, expected, proc.stderr)
            return json.loads(proc.stdout)
        invoke(["init", "handoff.json", "--source", "source.md", "--domain", "finance"])
        invoke(["decision", "handoff.json", "--id", "bank", "--kind", "term", "--source-text", "bank", "--target", "은행", "--state", "adopted", "--reason", "금융 문맥"])
        for name in ("analysis", "draft"):
            artifact = self.artifact(name)
            invoke(["checkpoint", "handoff.json", "--stage", name, "--artifact", artifact.name])
        report = invoke(["inspect", "handoff.json"])
        self.assertEqual(report["next_stage"], "review")
        self.assertEqual(report["usable_decisions"][0]["scope"]["domain"], "finance")
        self.source.write_text("The bank will reopen.", encoding="utf-8")
        self.assertEqual(invoke(["inspect", "handoff.json"], 2)["usable_decisions"], [])


if __name__ == "__main__":
    unittest.main()
