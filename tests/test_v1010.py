"""v10.10: blog channel, meta description, headings, link text and tag checks."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import korean_writing  # noqa: E402


def ids(data):
    return [item["id"] for item in data["findings"]]


LONG_BODY = "\n\n".join("경산 냉삼을 고르는 기준을 한 가지씩 설명합니다. 반찬과 주차를 봅니다." for _ in range(45))


class BlogChannelTests(unittest.TestCase):
    def test_markdown_is_allowed_on_blog_but_not_on_naver(self):
        text = "## 고르는 기준\n\n**반찬**을 먼저 봅니다."
        self.assertNotIn("CH-3", ids(korean_writing.channel_data(text, "blog")))
        self.assertIn("CH-3", ids(korean_writing.channel_data(text, "naver-blog")))

    def test_aliases(self):
        for name in ("블로그", "워드프레스", "티스토리"):
            self.assertEqual(korean_writing.channel_data("본문입니다.", name)["channel"], "blog")
        self.assertEqual(korean_writing.channel_data("본문입니다.", "브런치스토리")["channel"], "brunch")

    def test_meta_is_not_guessed_and_length_is_checked(self):
        data = korean_writing.channel_data("본문입니다.", "blog")
        self.assertTrue(any("메타 설명 미검사" in note for note in data["notes"]))
        self.assertNotIn("CH-11", ids(data))
        short = korean_writing.channel_data("본문입니다.", "blog", meta="짧은 설명")
        self.assertIn("기준 80자보다 짧음", " ".join(f["message"] for f in short["findings"]))
        good = "경산 냉삼을 고를 때 반찬 구성, 주차, 영업시간을 어떤 순서로 확인하면 헛걸음을 줄일 수 있는지 현장에서 확인한 기준으로 정리했습니다. 처음 가는 분께 맞춘 글입니다."
        ok = korean_writing.channel_data("본문입니다.", "blog", meta=good, keyword="경산 냉삼")
        self.assertNotIn("CH-11", ids(ok))
        missing = korean_writing.channel_data("본문입니다.", "blog", meta=good.replace("경산 냉삼", "고깃집"), keyword="경산 냉삼")
        self.assertIn("핵심어가 메타 설명에 없음", [f["message"] for f in missing["findings"]])

    def test_meta_is_ignored_for_channels_without_meta_spec(self):
        data = korean_writing.channel_data("본문입니다.", "facebook", meta="짧음")
        self.assertNotIn("CH-11", ids(data))
        self.assertFalse(any("메타" in note for note in data["notes"]))

    def test_long_post_without_headings_and_too_many_headings(self):
        self.assertGreaterEqual(len(LONG_BODY), 1500)
        data = korean_writing.channel_data(LONG_BODY, "blog")
        hit = next(f for f in data["findings"] if f["id"] == "CH-12")
        self.assertEqual((hit["value"], hit["severity"]), (0, "warn"))
        self.assertTrue(hit["keep"])
        many = "\n\n".join(f"## 소제목 {i}\n\n본문 문장입니다." for i in range(8))
        self.assertIn("CH-12", ids(korean_writing.channel_data(many, "blog")))
        fine = "## 기준\n\n" + LONG_BODY + "\n\n## 정리\n\n끝입니다."
        self.assertNotIn("CH-12", ids(korean_writing.channel_data(fine, "blog")))

    def test_short_post_needs_no_headings(self):
        self.assertNotIn("CH-12", ids(korean_writing.channel_data("짧은 글입니다. 소제목이 필요 없습니다.", "blog")))

    def test_keyword_in_h2_is_reported_not_enforced(self):
        data = korean_writing.channel_data("## 경산 냉삼 고르는 기준\n\n경산 냉삼은 반찬을 봅니다.", "blog", keyword="경산 냉삼")
        self.assertTrue(data["metrics"]["keyword"]["in_h2"])
        data = korean_writing.channel_data("## 고르는 기준\n\n경산 냉삼은 반찬을 봅니다.", "blog", keyword="경산 냉삼")
        self.assertFalse(data["metrics"]["keyword"]["in_h2"])
        self.assertFalse(any("소제목" in f["message"] for f in data["findings"] if f["id"] == "CH-8"))

    def test_two_mentions_in_a_short_post_are_not_keyword_stuffing(self):
        data = korean_writing.channel_data("리뷰를 늘린 가게가 있습니다.\n\n리뷰 안내문을 붙였습니다.", "blog", keyword="리뷰")
        self.assertFalse(any("기계적 반복" in f["message"] for f in data["findings"]))

    def test_vague_link_text(self):
        data = korean_writing.channel_data("자세한 내용은 [여기](https://example.com/a)를 보세요.", "blog")
        self.assertIn("CH-13", ids(data))
        data = korean_writing.channel_data("자세한 내용은 [냉삼 굽는 순서](https://example.com/a)에 있습니다.", "blog")
        self.assertNotIn("CH-13", ids(data))


class TagTests(unittest.TestCase):
    def test_brunch_keyword_count_and_duplicates(self):
        data = korean_writing.channel_data("본문입니다.", "brunch", tags="글쓰기, 일상, 가게, 사장")
        hit = next(f for f in data["findings"] if f["id"] == "CH-14")
        self.assertEqual((hit["value"], hit["limit"], hit["basis"], hit["severity"]), (4, 3, "reported", "warn"))
        data = korean_writing.channel_data("본문입니다.", "brunch", tags="글쓰기,일상,일상")
        self.assertEqual([f["message"] for f in data["findings"] if f["id"] == "CH-14"], ["중복된 태그가 있음"])

    def test_tags_are_counted_without_a_limit(self):
        data = korean_writing.channel_data("본문입니다.", "facebook", tags="하나,둘")
        self.assertEqual(data["metrics"]["tags"], 2)
        self.assertNotIn("CH-14", ids(data))

    def test_new_checks_never_hold(self):
        data = korean_writing.channel_data(LONG_BODY + "\n\n[여기](https://example.com)", "blog", meta="짧음", tags="a,a")
        self.assertEqual(data["status"], "warn")


class ReferenceTests(unittest.TestCase):
    def test_channel_procedures_are_linked_from_workflow_and_exist(self):
        workflow = (ROOT / "korean-writing/SKILL.md").read_text(encoding="utf-8")
        for name in ("channel-facebook", "channel-blog", "channel-brunch"):
            path = ROOT / f"korean-writing/references/{name}.md"
            self.assertTrue(path.exists(), name)
            self.assertIn(f"references/{name}.md", workflow)

    def test_playbook_channels_match_specs(self):
        playbook = (ROOT / "korean-writing/references/channel-playbooks.md").read_text(encoding="utf-8")
        for name in korean_writing.load_channel_specs()["channels"]:
            self.assertIn(f"(`{name}`)", playbook, name)


if __name__ == "__main__":
    unittest.main()
