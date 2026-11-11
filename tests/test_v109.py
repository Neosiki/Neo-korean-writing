"""v10.9: channel format checks and voice-sample statistics."""
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

SCRIPT = ROOT / "scripts/korean_writing.py"


def ids(data):
    return [item["id"] for item in data["findings"]]


class ChannelSpecTests(unittest.TestCase):
    def test_every_limit_declares_value_and_known_basis(self):
        specs = korean_writing.load_channel_specs()
        levels = set(specs["basis_levels"])
        for name, spec in specs["channels"].items():
            self.assertIn("label", spec, name)
            for key, item in spec.items():
                if isinstance(item, dict):
                    self.assertIn(item["basis"], levels, f"{name}.{key}")
                    self.assertIsInstance(item["value"], (int, float), f"{name}.{key}")

    def test_aliases_resolve_to_declared_channels(self):
        channels = set(korean_writing.load_channel_specs()["channels"])
        self.assertTrue(set(korean_writing.CHANNEL_ALIASES.values()) <= channels)

    def test_unknown_channel_is_an_error_not_a_pass(self):
        data = korean_writing.channel_data("본문입니다.", "mystery")
        self.assertEqual(data["status"], "error")


class ThreadsTests(unittest.TestCase):
    def test_three_short_posts_pass(self):
        text = "첫 포스트야.\n---\n둘째 포스트야.\n---\n셋째 포스트야."
        data = korean_writing.channel_data(text, "스레드")
        self.assertEqual(data["status"], "pass")
        self.assertEqual(len(data["metrics"]["posts"]), 3)

    def test_post_over_platform_limit_holds_with_post_index(self):
        text = "짧은 글.\n---\n" + "가" * 501 + "\n---\n마지막 글."
        data = korean_writing.channel_data(text, "threads")
        self.assertEqual(data["status"], "hold")
        hit = next(item for item in data["findings"] if item["id"] == "CH-1")
        self.assertEqual((hit["post"], hit["value"], hit["basis"]), (2, 501, "platform"))

    def test_post_count_is_only_a_warning(self):
        data = korean_writing.channel_data("하나.\n---\n둘.", "threads")
        self.assertEqual(data["status"], "warn")
        self.assertEqual(ids(data), ["CH-10"])

    def test_separator_is_not_reported_as_markdown(self):
        data = korean_writing.channel_data("하나.\n---\n둘.\n---\n셋.", "threads")
        self.assertNotIn("CH-3", ids(data))


class PlainChannelTests(unittest.TestCase):
    def test_markdown_residue_holds_but_hashtag_and_comparison_do_not(self):
        clean = "매출이 3 > 2로 늘었습니다. #소상공인"
        self.assertNotIn("CH-3", ids(korean_writing.channel_data(clean, "facebook")))
        dirty = "## 소제목\n\n**굵게** 쓴 문장입니다."
        data = korean_writing.channel_data(dirty, "facebook")
        self.assertEqual(data["status"], "hold")
        hit = next(item for item in data["findings"] if item["id"] == "CH-3")
        self.assertEqual(hit["value"], {"heading": 1, "bold": 1})

    def test_assumption_limits_never_hold(self):
        data = korean_writing.channel_data("가" * 2500, "facebook")
        self.assertEqual(data["status"], "warn")
        self.assertTrue(all(item["basis"] == "assumption" for item in data["findings"]))

    def test_instagram_platform_limits_hold(self):
        data = korean_writing.channel_data("가" * 2201, "instagram")
        self.assertEqual(data["status"], "hold")
        tags = " ".join(f"#태그{i}" for i in range(31))
        data = korean_writing.channel_data("사진 설명입니다. " + tags, "instagram")
        hit = next(item for item in data["findings"] if item["id"] == "CH-4")
        self.assertEqual((hit["value"], hit["severity"]), (31, "hold"))

    def test_first_sentence_past_fold_is_warned_with_preview(self):
        long_first = "이 문장은 " + "길게 이어지고 " * 20 + "끝납니다."
        data = korean_writing.channel_data(long_first, "facebook")
        self.assertIn("CH-2", ids(data))
        self.assertEqual(len(data["preview"]), 120)


class OpeningTests(unittest.TestCase):
    def test_formula_openings_are_contextual_candidates(self):
        data = korean_writing.channel_data("안녕하세요. 오늘은 냉삼에 대해 알아보겠습니다.\n\n본문입니다.", "facebook")
        kinds = {item["value"] for item in data["findings"] if item["id"] == "CH-9"}
        self.assertEqual(kinds, {"greeting", "meta"})
        self.assertTrue(all(item["severity"] == "warn" and item["keep"] for item in data["findings"] if item["id"] == "CH-9"))

    def test_material_led_opening_is_not_flagged(self):
        data = korean_writing.channel_data("사장님은 블로그를 석 달 만에 접었습니다. 올릴 사진이 없었기 때문입니다.", "facebook")
        self.assertNotIn("CH-9", ids(data))

    def test_only_the_opening_is_inspected(self):
        text = "사장님은 블로그를 접었습니다. 사진이 없었습니다.\n\n글 끝에서 인사드립니다. 안녕하세요."
        self.assertNotIn("CH-9", ids(korean_writing.channel_data(text, "facebook")))


class NaverTests(unittest.TestCase):
    BODY = "경산 냉삼을 고를 때는 반찬 구성을 먼저 봅니다.\n\n주차와 영업시간도 확인합니다."

    def test_title_is_not_guessed_when_missing(self):
        data = korean_writing.channel_data(self.BODY, "naver")
        self.assertNotIn("CH-7", ids(data))
        self.assertTrue(any("제목 미검사" in note for note in data["notes"]))

    def test_keyword_placement_and_repetition(self):
        data = korean_writing.channel_data(self.BODY, "네이버", title="경산 냉삼 고를 때 먼저 볼 세 가지", keyword="경산 냉삼")
        self.assertEqual(data["metrics"]["keyword"]["in_title"], True)
        self.assertEqual(data["metrics"]["keyword"]["in_first_paragraph"], True)
        stuffed = "경산 냉삼 " * 12 + "입니다."
        data = korean_writing.channel_data(stuffed, "naver-blog", title="냉삼 이야기를 길게 풀어 보는 글", keyword="경산 냉삼")
        messages = [item["message"] for item in data["findings"] if item["id"] == "CH-8"]
        self.assertTrue(any("제목에 없음" in m for m in messages))
        self.assertTrue(any("기계적 반복" in m for m in messages))
        self.assertEqual(data["status"], "warn")


class VoiceProfileTests(unittest.TestCase):
    FORMAL = "\n\n".join("이 방식은 현장에서 확인했습니다. 결과는 표로 정리했습니다." for _ in range(12))
    PLAIN = "\n\n".join("이 방식은 현장에서 확인했다. 결과는 표로 정리했다." for _ in range(12))

    def test_particle_ending_in_da_does_not_split_a_sentence(self):
        stats = korean_writing.voice_stats("가격은 매장마다 다르며 반찬도 다릅니다.")
        self.assertEqual(stats["sentences"], 1)
        self.assertEqual(stats["endings"]["formal"], 1.0)

    def test_short_sample_is_out_of_scope(self):
        profile = korean_writing.voice_stats("짧은 표본입니다. 두 문장뿐입니다.")
        result = korean_writing.voice_compare(profile, korean_writing.voice_stats(self.PLAIN))
        self.assertFalse(profile["reliable"])
        self.assertEqual(result["status"], "insufficient_sample")

    def test_same_register_is_aligned_and_switch_is_drift(self):
        profile = korean_writing.voice_stats(self.FORMAL)
        self.assertEqual(korean_writing.voice_compare(profile, korean_writing.voice_stats(self.FORMAL))["status"], "aligned")
        result = korean_writing.voice_compare(profile, korean_writing.voice_stats(self.PLAIN))
        self.assertEqual(result["status"], "drift")
        self.assertEqual(result["drift"][0]["axis"], "ending")

    def test_first_person_absent_from_sample_is_flagged(self):
        profile = korean_writing.voice_stats(self.FORMAL)
        draft = korean_writing.voice_stats(self.FORMAL + "\n\n저는 그날 현장에 있었습니다.")
        axes = [item["axis"] for item in korean_writing.voice_compare(profile, draft)["drift"]]
        self.assertIn("person", axes)

    def test_quoted_speech_is_excluded_from_statistics(self):
        stats = korean_writing.voice_stats('대표님은 “나는 내가 직접 굽는다”고 말했습니다.')
        self.assertEqual(stats["first_person_per_1000"], 0)

    def test_custom_voice_is_accepted_by_handoff(self):
        handoff = json.loads((ROOT / "templates/writer-editor-handoff.json").read_text(encoding="utf-8"))
        handoff["voice"]["profile"] = "custom"
        self.assertTrue(korean_writing.handoff_data(json.dumps(handoff, ensure_ascii=False))["pass"])


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")

    def test_exit_codes_follow_status(self):
        with tempfile.TemporaryDirectory() as temp:
            ok = Path(temp) / "ok.txt"
            ok.write_text("하나.\n---\n둘.\n---\n셋.", encoding="utf-8")
            warn = Path(temp) / "warn.txt"
            warn.write_text("하나.\n---\n둘.", encoding="utf-8")
            hold = Path(temp) / "hold.txt"
            hold.write_text("가" * 501, encoding="utf-8")
            self.assertEqual(self.run_cli("channel-check", str(ok), "--channel", "threads").returncode, 0)
            self.assertEqual(self.run_cli("channel-check", str(warn), "--channel", "threads").returncode, 0)
            self.assertEqual(self.run_cli("channel-check", str(warn), "--channel", "threads", "--strict").returncode, 1)
            self.assertEqual(self.run_cli("channel-check", str(hold), "--channel", "threads").returncode, 1)
            result = self.run_cli("channel-check", str(ok), "--channel", "threads", "--json")
            self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_title_value_is_not_read_as_a_file(self):
        with tempfile.TemporaryDirectory() as temp:
            body = Path(temp) / "body.txt"
            body.write_text("경산 냉삼을 고를 때는 반찬을 봅니다.", encoding="utf-8")
            title = "경산 냉삼 고를 때 먼저 볼 세 가지"
            result = self.run_cli("channel-check", "--title", title, str(body), "--channel", "naver-blog", "--json")
            self.assertEqual(json.loads(result.stdout)["metrics"]["title_chars"], len(title))

    def test_voice_profile_compare_json(self):
        with tempfile.TemporaryDirectory() as temp:
            sample = Path(temp) / "sample.md"
            sample.write_text(VoiceProfileTests.FORMAL, encoding="utf-8")
            draft = Path(temp) / "draft.md"
            draft.write_text(VoiceProfileTests.PLAIN, encoding="utf-8")
            result = self.run_cli("voice-profile", str(sample), "--compare", str(draft), "--json")
            self.assertEqual(json.loads(result.stdout)["comparison"]["status"], "drift")


if __name__ == "__main__":
    unittest.main()
