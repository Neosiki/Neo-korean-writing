"""v10.11: business-plan mechanical checks."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import korean_writing  # noqa: E402


def ids(data):
    return [item["id"] for item in data["findings"]]


CLEAN = """# 사업계획서

## 1. 문제인식

국내 시장 규모는 2023년 8조 원으로 집계됨. (출처: 통계청, 2024)

| 구분 | 규모 |
|---|---|
| TAM | 8조 원 |
| SAM | 9,000억 원 |
| SOM | 45억 원 |

출처: 통계청(2024), SAM·SOM은 자체 산정

## 2. 실현가능성

대표자가 2026년 3월 시제품을 제작함.

## 3. 성장전략

| 비목 | 금액(천원) | 비율 |
|---|---|---|
| 재료비 | 10,000 | 25% |
| 외주용역비 | 20,000 | 50% |
| 마케팅비 | 10,000 | 25% |
| 합계 | 40,000 | 100% |

## 4. 팀 구성

대표자가 개발을 맡음.
"""


class MoneyTests(unittest.TestCase):
    def test_parse_krw(self):
        cases = {"1조 2,000억 원": 1_200_000_000_000, "350억원": 35_000_000_000, "5천만 원": 50_000_000,
                 "0.4억 원": 40_000_000, "40,000,000원": 40_000_000, "3,000만원": 30_000_000,
                 "1억 5천만 원": 150_000_000}
        for text, expected in cases.items():
            self.assertEqual(korean_writing.parse_krw(text), expected, text)
        self.assertIsNone(korean_writing.parse_krw("금액 없음"))


class BizplanTests(unittest.TestCase):
    def test_clean_plan_passes(self):
        data = korean_writing.bizplan_data(CLEAN)
        self.assertEqual(data["findings"], [])
        self.assertEqual(data["status"], "pass")
        self.assertEqual(data["metrics"]["market"]["SOM"]["won"], 4_500_000_000)

    def test_placeholders_hold_with_lines(self):
        text = CLEAN.replace("대표자가 개발을 맡음.", "대표자는 {핵심 경력}을 보유함. 특허는 [확인 필요]. 협력처는 ○○대학교임.")
        data = korean_writing.bizplan_data(text)
        hit = next(f for f in data["findings"] if f["id"] == "BP-1")
        self.assertEqual(hit["severity"], "hold")
        self.assertEqual([i["span"] for i in hit["items"]], ["{핵심 경력}", "[확인 필요]", "○○"])

    def test_table_sum_mismatch_holds_and_names_column(self):
        data = korean_writing.bizplan_data(CLEAN.replace("| 마케팅비 | 10,000 | 25% |", "| 마케팅비 | 9,000 | 25% |"))
        hits = [f for f in data["findings"] if f["id"] == "BP-4"]
        self.assertEqual(len(hits), 1)
        self.assertEqual((hits[0]["column"], hits[0]["sum"], hits[0]["total"], hits[0]["severity"]),
                         ("금액(천원)", 39000.0, 40000.0, "hold"))

    def test_ratio_column_is_checked_too(self):
        data = korean_writing.bizplan_data(CLEAN.replace("| 마케팅비 | 10,000 | 25% |", "| 마케팅비 | 10,000 | 20% |"))
        self.assertEqual([f["column"] for f in data["findings"] if f["id"] == "BP-4"], ["비율"])

    def test_subtotals_are_not_auto_compared(self):
        table = "| 비목 | 금액 |\n|---|---|\n| 재료비 | 10 |\n| 소계 | 10 |\n| 인건비 | 20 |\n| 합계 | 30 |\n"
        data = korean_writing.bizplan_data(table)
        hit = next(f for f in data["findings"] if f["id"] == "BP-4")
        self.assertEqual(hit["severity"], "warn")

    def test_column_with_text_cells_is_skipped(self):
        table = "| 비목 | 산출 근거 | 금액 |\n|---|---|---|\n| 재료비 | 100개 × 1,000원 | 100 |\n| 인건비 | 2명 | 200 |\n| 합계 | - | 300 |\n"
        self.assertNotIn("BP-4", ids(korean_writing.bizplan_data(table)))

    def test_market_order_violation_holds(self):
        data = korean_writing.bizplan_data(CLEAN.replace("| SOM | 45억 원 |", "| SOM | 1조 원 |"))
        self.assertIn("BP-9", ids(data))
        inline = "TAM 500억 원, SAM 800억 원, SOM 10억 원으로 산정함. (출처: 자체 산정)"
        self.assertIn("BP-9", ids(korean_writing.bizplan_data(inline)))

    def test_unsourced_statistics_are_candidates_not_blocks(self):
        text = CLEAN.replace(" (출처: 통계청, 2024)", "")
        data = korean_writing.bizplan_data(text)
        hit = next(f for f in data["findings"] if f["id"] == "BP-3")
        self.assertEqual(hit["severity"], "warn")
        self.assertEqual(data["status"], "warn")

    def test_own_targets_do_not_need_a_source(self):
        text = "## 성장전략\n\n1년 차 매출 목표는 5,000만 원임. 대표자가 월 10건을 판매함."
        self.assertNotIn("BP-3", ids(korean_writing.bizplan_data(text)))

    def test_default_sections_warn_and_outline_holds(self):
        text = CLEAN.replace("## 4. 팀 구성\n\n대표자가 개발을 맡음.\n", "")
        self.assertEqual([f["severity"] for f in korean_writing.bizplan_data(text)["findings"] if f["id"] == "BP-2"], ["warn"])
        outline = {"sections": [{"title": "문제인식"}, {"title": "창업 아이템의 필요성"}, {"title": "선택 항목", "required": False}]}
        data = korean_writing.bizplan_data(CLEAN, outline)
        self.assertEqual([f["message"] for f in data["findings"] if f["id"] == "BP-2"], ["양식 항목이 원고에 없음: 창업 아이템의 필요성"])
        self.assertEqual(data["status"], "hold")

    def test_outline_section_length_and_spacing(self):
        outline = {"sections": [{"title": "문제 인식", "max_chars": 10}, {"title": "실현가능성"}]}
        data = korean_writing.bizplan_data(CLEAN, outline)
        hit = next(f for f in data["findings"] if f["id"] == "BP-6")
        self.assertEqual((hit["severity"], hit["limit"]), ("warn", 10))
        self.assertEqual([s["title"] for s in data["metrics"]["sections"]], ["문제 인식", "실현가능성"])

    def test_register_mixing(self):
        nominal = "\n".join("대표자가 시제품을 제작함." for _ in range(8))
        formal = "\n".join("대표자가 시제품을 제작합니다." for _ in range(4))
        self.assertIn("BP-5", ids(korean_writing.bizplan_data(nominal + "\n" + formal)))
        self.assertNotIn("BP-5", ids(korean_writing.bizplan_data(nominal + "\n" + nominal)))

    def test_template_outline_is_valid_and_mirrored(self):
        source = ROOT / "templates/bizplan-outline.json"
        outline = json.loads(source.read_text(encoding="utf-8"))
        self.assertTrue(all("title" in item for item in outline["sections"]))
        packaged = ROOT / "src/neo_korean_writing/assets/templates/bizplan-outline.json"
        self.assertEqual(source.read_bytes(), packaged.read_bytes())

    def test_references_exist_and_are_linked(self):
        workflow = (ROOT / "korean-writing/SKILL.md").read_text(encoding="utf-8")
        for name in ("bizplan-workflow", "bizplan-evidence", "bizplan-pitch"):
            self.assertTrue((ROOT / f"korean-writing/references/{name}.md").exists())
            self.assertIn(f"references/{name}.md", workflow)


class BizplanCliTests(unittest.TestCase):
    def test_exit_codes_and_outline_option(self):
        script = ROOT / "scripts/korean_writing.py"
        with tempfile.TemporaryDirectory() as temp:
            plan = Path(temp) / "plan.md"
            plan.write_text(CLEAN, encoding="utf-8")
            outline = Path(temp) / "outline.json"
            outline.write_text(json.dumps({"sections": [{"title": "없는 항목"}]}, ensure_ascii=False), encoding="utf-8")
            run = lambda *args: subprocess.run([sys.executable, str(script), "bizplan-check", *args],
                                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run(str(plan)).returncode, 0)
            result = run("--outline", str(outline), str(plan), "--json")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "hold")


if __name__ == "__main__":
    unittest.main()
