# 같은 입력 → 프론트와 같은 출력인지 비교한다.
# 기대값은 frontend/scripts/dump-fixtures.ts가 프론트 도메인 함수로 만든 tests/fixtures/parity.json이다.

import json
from pathlib import Path

import pytest

from app import clock
from app.data.mock import build_mock_cases, build_stat_records, rng
from app.rules.coverage import is_after_hours, next_open_day, route_coverage
from app.rules.triage import extract_from_text, merge_extraction, triage
from app.rules.urgency import default_category, rate_urgency
from app.schemas import CenterSummaryInput, CoverageInput, Intake, Profile
from app.templates.reports import build_center_summary, build_clinician_report
from app.templates.visit import build_call_script, build_desk_sheet

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "parity.json").read_text())


def dump(model) -> dict:
    return model.model_dump(by_alias=True, mode="json")


def cases(name: str):
    return pytest.mark.parametrize("case", FIXTURES[name], ids=[f"{name}-{n}" for n in range(len(FIXTURES[name]))])


@cases("triage")
def test_triage(case):
    assert dump(triage(Intake.model_validate(case["input"]))) == case["output"]


@cases("extract")
def test_extract(case):
    i = Intake.model_validate(case["input"])
    ex = extract_from_text(i.free_text)
    assert {"extraction": dump(ex), "intake": dump(merge_extraction(i, ex))} == case["output"]


@cases("route")
def test_route(case):
    assert dump(route_coverage(CoverageInput.model_validate(case["input"]))) == case["output"]


@cases("urgency")
def test_urgency(case):
    i = case["input"]
    urgency, reasons = rate_urgency(i["workRelated"], i["insurance"])
    assert {"urgency": urgency, "reasons": reasons} == case["output"]


@cases("category")
def test_default_category(case):
    i = case["input"]
    assert default_category(i["coveragePath"], i["requestTypes"]) == case["output"]


@cases("desk")
def test_desk_sheet(case):
    i = case["input"]
    out = build_desk_sheet(Intake.model_validate(i["intake"]), i["department"], i["firstVisit"], i["lang"])
    assert dump(out) == case["output"]


@cases("call")
def test_call_script(case):
    i = case["input"]
    assert dump(build_call_script(Intake.model_validate(i["intake"]), i["department"], i["lang"])) == case["output"]


@cases("clinician")
def test_clinician_report(case, monkeypatch):
    # 나이는 기대값을 만든 시각 기준으로 계산한다.
    monkeypatch.setattr(clock, "now", lambda: clock.parse_iso(FIXTURES["generatedAt"]).astimezone(clock.SEOUL))
    i = case["input"]
    profile = Profile.model_validate(i["profile"]) if i["profile"] else None
    out = dump(build_clinician_report(Intake.model_validate(i["intake"]), i["included"], profile, i["meds"]))
    # 시각에 따라 바뀌는 값은 비교에서 뺀다.
    del out["id"], out["createdAt"]
    assert out == case["output"]


@cases("center")
def test_center_summary(case):
    assert dump(build_center_summary(CenterSummaryInput.model_validate(case["input"]))) == case["output"]


@cases("hours")
def test_center_hours(case):
    at = clock.parse_iso(case["input"])
    assert {"afterHours": is_after_hours(at), "nextOpenDate": next_open_day(at).isoformat()} == case["output"]


@pytest.mark.parametrize("seed", ["20261024", "77"])
def test_rng_first_ten(seed):
    r = rng(int(seed))
    assert [r() for _ in range(10)] == FIXTURES["rng"][seed]


def test_mock_cases():
    now = clock.parse_iso(FIXTURES["now"])
    assert [dump(c) for c in build_mock_cases(now)] == FIXTURES["mockCases"]


def test_stat_records():
    now = clock.parse_iso(FIXTURES["now"])
    out = [
        {
            "date": clock.iso_utc(r.date),
            "district": r.district,
            "industry": r.industry,
            "language": r.language,
            "insurance": r.insurance,
            "afterHours": r.after_hours,
            "requestType": r.request_type,
            "workRelated": r.work_related,
        }
        for r in build_stat_records(now)
    ]
    assert out == FIXTURES["statRecords"]
