# 리포트 자유 입력 번역(backlog 05): 성공, 역번역 불일치 거부, 호출 실패, 금지어 거부, 원문 유지, 번역 건너뛰기.
# LLM은 FakeLLMClient로 바꾸고 외부 네트워크를 쓰지 않는다.

import asyncio
import json

import pytest
from fakes import FakeLLMClient, provider_error
from fastapi.testclient import TestClient

from app.main import app
from app.routers.worker import llm_client
from app.templates.translate import (
    SYSTEM_COMPARE,
    SYSTEM_TRANSLATE,
    BackOutput,
    CompareOutput,
    LineOutput,
    LineTranslation,
    TranslateOutput,
    system_back,
    translate_line,
)

FREE_TEXT = "Ngón tay bị kẹp vào máy dập, bị sưng."
KO = "프레스 기계에 손가락이 끼여서 부었습니다."
BACK = "Ngón tay bị kẹp vào máy dập và bị sưng."
INTAKE = {
    "id": "in-test",
    "language": "vi",
    "bodyParts": ["hand"],
    "symptoms": ["swelling"],
    "freeText": FREE_TEXT,
    "onset": None,
    "workRelated": "yes",
    "workType": None,
    "industry": None,
    "district": None,
    "createdAt": "2026-10-26T01:00:00.000Z",
}
CLINICIAN = {"intake": INTAKE, "included": ["symptoms", "note"], "profile": None, "meds": ""}
CENTER = {
    "intake": INTAKE,
    "requestTypes": ["booking"],
    "coverage": None,
    "insurance": "no",
    "contactMethod": "zalo",
}
UNTRANSLATED_NOTE = f"{FREE_TEXT} (원문, 번역 미연결)"


def replies(ko: str = KO, same: bool = True) -> list[str]:
    return [
        json.dumps({"ko": ko}, ensure_ascii=False),
        json.dumps({"back": BACK}, ensure_ascii=False),
        json.dumps({"same": same, "diff": "" if same else "body part"}),
    ]


def post(path: str, body: dict, fake: FakeLLMClient | None) -> dict:
    app.dependency_overrides[llm_client] = lambda: fake
    try:
        return TestClient(app).post(path, json=body).json()
    finally:
        app.dependency_overrides.clear()


def note(report: dict) -> dict:
    [row] = [r for r in report["rows"] if r["field"] == "note"]
    return row


def test_clinician_note_is_translation_with_original():
    out = post("/api/report/clinician", CLINICIAN, FakeLLMClient(replies()))

    assert out["translation"] == {"status": "ok"}
    assert note(out)["valueKo"] == f"{KO} (원문: {FREE_TEXT})"
    assert FREE_TEXT in note(out)["valueKo"]
    assert note(out)["valueNative"] == FREE_TEXT


def test_three_calls_with_free_text_only_in_user_part():
    fake = FakeLLMClient(replies())
    post("/api/report/clinician", CLINICIAN, fake)

    translate, back, compare = fake.prompts
    assert (translate.system, translate.user) == (SYSTEM_TRANSLATE, FREE_TEXT)
    assert (back.system, back.user) == (system_back("vi"), KO)
    assert compare.system == SYSTEM_COMPARE
    assert json.loads(compare.user) == {"original": FREE_TEXT, "back": BACK}
    assert FREE_TEXT not in translate.system + back.system + compare.system
    assert fake.schemas == [m.model_json_schema() for m in (TranslateOutput, BackOutput, CompareOutput)]
    assert "베트남어" in back.system


def test_back_translation_mismatch_is_rejected():
    out = post("/api/report/clinician", CLINICIAN, FakeLLMClient(replies(same=False)))

    assert out["translation"] == {"status": "rejected"}
    assert note(out)["valueKo"] == UNTRANSLATED_NOTE


@pytest.mark.parametrize(
    "bad",
    ["손가락이 골절된 것 같습니다.", "Ngón tay bị kẹp.", "  "],
    ids=["forbidden", "not-korean", "empty"],
)
def test_guard_rejects_translation_before_back_translation(bad: str):
    fake = FakeLLMClient(replies(ko=bad)[:1])
    out = post("/api/report/clinician", CLINICIAN, fake)

    assert len(fake.prompts) == 1
    assert out["translation"] == {"status": "rejected"}
    assert note(out)["valueKo"] == UNTRANSLATED_NOTE


@pytest.mark.parametrize("failed_call", [0, 1, 2], ids=["translate", "back", "compare"])
def test_any_call_failure_skips_translation(failed_call: int):
    ok = replies()
    fake = FakeLLMClient([*ok[:failed_call], provider_error(), "not json"])
    out = post("/api/report/clinician", CLINICIAN, fake)

    assert len(fake.prompts) == failed_call + 2
    assert out["translation"] == {"status": "skipped"}
    assert note(out)["valueKo"] == UNTRANSLATED_NOTE


def test_without_llm_note_is_unchanged():
    out = post("/api/report/clinician", CLINICIAN, None)

    assert out["translation"] == {"status": "skipped"}
    assert note(out)["valueKo"] == UNTRANSLATED_NOTE


def test_korean_user_skips_llm():
    fake = FakeLLMClient([])
    body = {**CLINICIAN, "intake": {**INTAKE, "language": "ko", "freeText": "손가락이 끼었어요"}}
    out = post("/api/report/clinician", body, fake)

    assert fake.prompts == []
    assert out["translation"] == {"status": "skipped"}
    assert note(out)["valueKo"] == "손가락이 끼었어요"


def test_excluded_note_is_not_sent_to_llm():
    fake = FakeLLMClient([])
    out = post("/api/report/clinician", {**CLINICIAN, "included": ["symptoms"]}, fake)

    assert fake.prompts == []
    assert out["translation"] == {"status": "skipped"}


def test_center_summary_appends_translation_keeps_original():
    off = post("/api/report/center", CENTER, None)
    out = post("/api/report/center", CENTER, FakeLLMClient(replies()))

    assert out["translation"] == {"status": "ok"}
    assert out["ko"] == f'{off["ko"]} 근로자 메모(번역): "{KO}"'
    # 근로자에게 보이는 원문 요약은 바뀌지 않는다.
    assert out["native"] == off["native"]
    assert FREE_TEXT in out["native"]


def test_center_summary_rejected_matches_llm_off():
    off = post("/api/report/center", CENTER, None)
    out = post("/api/report/center", CENTER, FakeLLMClient(replies(same=False)))

    assert off["translation"] == {"status": "skipped"}
    assert out == {**off, "translation": {"status": "rejected"}}


def test_center_case_gets_same_translation_as_preview():
    body = {**CENTER, "contact": "010-0000-0000", "consentedItems": ["증상"]}
    preview = post("/api/report/center", CENTER, FakeLLMClient(replies()))
    try:
        case = post("/api/center/cases", body, FakeLLMClient(replies()))["case"]
        assert case["summaryKo"] == preview["ko"]
        assert case["originalNative"] == preview["native"]
    finally:
        TestClient(app).post("/api/center/reset")


def test_center_case_without_llm_is_unchanged():
    body = {**CENTER, "contact": None, "consentedItems": []}
    try:
        case = post("/api/center/cases", body, None)["case"]
        assert "근로자 메모(번역)" not in case["summaryKo"]
    finally:
        TestClient(app).post("/api/center/reset")


# ---------------------------------------------------------------------------
# 통화 자막 번역(backlog 16): 한 번만 부르고, 같은 언어는 부르지 않고, 한국어 번역만 guard를 거친다.
# ---------------------------------------------------------------------------
def line(text: str, source: str, target: str, client: FakeLLMClient) -> LineTranslation:
    return asyncio.run(translate_line(text, source, target, client))


def test_line_same_language_is_not_called():
    fake = FakeLLMClient([])
    assert line("손이 아파요", "ko", "ko", fake) == LineTranslation("skipped")
    assert fake.prompts == []


def test_line_is_called_once_and_falls_back():
    fake = FakeLLMClient([provider_error(), LineOutput(text="손이 아파요").model_dump_json()])
    assert line(FREE_TEXT, "vi", "ko", fake) == LineTranslation("skipped")
    assert len(fake.prompts) == 1


def test_line_to_worker_language_skips_korean_guard():
    # 근로자 언어로 옮긴 문장에는 한국어 금지어 검사를 할 수 없다. 빈 값만 거른다.
    ok = FakeLLMClient([LineOutput(text=" Hãy đến bệnh viện ").model_dump_json()])
    assert line("병원에 오세요", "ko", "vi", ok) == LineTranslation("ok", "Hãy đến bệnh viện")
    empty = FakeLLMClient([LineOutput(text=" ").model_dump_json()])
    assert line("병원에 오세요", "ko", "vi", empty) == LineTranslation("rejected")
