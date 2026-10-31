# 데모용 합성 데이터. 실제 개인 정보가 아니다. frontend/src/data/mock.ts와 1:1.
# - 센터 접수함 mock 사례 24건
# - 통계 탭용 익명 집계 원천(개인 식별값 없음)

import calendar
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app import clock
from app.rules.coverage import is_after_hours, route_coverage
from app.rules.urgency import rate_urgency
from app.schemas import CaseStatus, CenterCase, CenterSummaryInput, ContactMethod, CoverageInput, Intake, RequestType
from app.templates.reports import build_center_summary
from app.vocab import BodyPart, District, Industry, Lang, Onset, Symptom, WorkType, YesNoUnknown

MASK = 0xFFFFFFFF


def _i32(x: int) -> int:
    """JS `|0`: 부호 있는 32비트 정수로 자른다."""
    x &= MASK
    return x - 0x100000000 if x & 0x80000000 else x


def _imul(a: int, b: int) -> int:
    """JS Math.imul: 32비트 곱의 하위 32비트(부호 있음)."""
    return _i32(a * b)


def rng(seed: int) -> Callable[[], float]:
    """시드 고정 난수(mulberry32): 프론트와 같은 수열이 나온다."""
    a = seed

    def next_() -> float:
        nonlocal a
        a = _i32(a)
        a = _i32(a + 0x6D2B79F5)
        t = _imul(a ^ ((a & MASK) >> 15), 1 | a)
        t = _i32(_i32(t + _imul(t ^ ((t & MASK) >> 7), 61 | t)) ^ t)
        return ((t ^ ((t & MASK) >> 14)) & MASK) / 4294967296

    return next_


def weighted[T](r: Callable[[], float], items: list[tuple[T, float]]) -> T:
    total = sum(w for _, w in items)
    x = r() * total
    for v, w in items:
        x -= w
        if x <= 0:
            return v
    return items[-1][0]


@dataclass(frozen=True)
class Scenario:
    parts: list[BodyPart]
    syms: list[Symptom]
    work: YesNoUnknown
    type: WorkType | None
    # mock 사례는 실제 이용 비중이 큰 베트남어·영어로만 만든다(한국어 사례는 실제 전송으로만 들어온다).
    text: dict[str, str]


SCENARIOS = [
    Scenario(
        ["hand"],
        ["pain", "swelling"],
        "yes",
        "machine",
        {"en": "My finger got caught in the press machine, it is swollen.", "vi": "Ngón tay bị kẹp vào máy dập, bị sưng."},
    ),
    Scenario(
        ["back"], ["pain"], "yes", "lifting", {"en": "Back pain after lifting heavy parts.", "vi": "Đau lưng sau khi nâng hàng nặng."}
    ),
    Scenario(
        ["eye"],
        ["foreign", "pain"],
        "yes",
        "grinding",
        {"en": "Something went into my eye while grinding.", "vi": "Bụi vào mắt khi đang mài."},
    ),
    Scenario(["arm"], ["burn"], "yes", "welding", {"en": "Small burn on my arm from welding.", "vi": "Bị bỏng nhẹ ở tay khi hàn điện."}),
    Scenario(["whole"], ["fever", "cough"], "no", None, {"en": "Fever and cough for three days.", "vi": "Sốt và ho 3 ngày."}),
    Scenario(
        ["skin"],
        ["rash"],
        "unknown",
        "painting",
        {"en": "Itchy rash on my hands, maybe from paint.", "vi": "Ngứa, mẩn đỏ ở tay, có thể do sơn."},
    ),
    Scenario(["teeth"], ["pain"], "no", None, {"en": "Toothache for a week.", "vi": "Đau răng một tuần."}),
    Scenario(["leg"], ["pain", "cantmove"], "yes", "assembly", {"en": "Knee hurts, hard to walk.", "vi": "Đau đầu gối, khó đi lại."}),
    Scenario(
        ["abdomen"],
        ["pain", "nausea"],
        "no",
        None,
        {"en": "Stomach pain and vomiting since yesterday.", "vi": "Đau bụng và nôn từ hôm qua."},
    ),
    Scenario(["hand"], ["cut", "bleeding"], "yes", "grinding", {"en": "Cut my hand on a steel plate.", "vi": "Bị cắt tay vào tấm thép."}),
    Scenario(["head"], ["dizzy"], "unknown", None, {"en": "Dizzy often after night shift.", "vi": "Hay chóng mặt sau ca đêm."}),
    Scenario(
        ["ent"],
        ["cough", "pain"],
        "yes",
        "painting",
        {"en": "Sore throat and cough, smell of chemicals at work.", "vi": "Đau họng, ho, chỗ làm có mùi hóa chất."},
    ),
]

ONSET_POOL: list[Onset] = ["today", "yesterday", "days", "week"]
DISTRICT_W: list[tuple[District, float]] = [("buk", 30), ("dong", 22), ("ulju", 20), ("nam", 18), ("jung", 10)]
INDUSTRY_W: list[tuple[Industry, float]] = [("autoparts", 32), ("shipbuilding", 30), ("chemical", 14), ("construction", 14), ("other", 10)]
LANG_W: list[tuple[Lang, float]] = [("vi", 62), ("en", 38)]
INS_W: list[tuple[YesNoUnknown, float]] = [("yes", 55), ("no", 25), ("unknown", 20)]
REQ_W: list[tuple[RequestType, float]] = [("booking", 34), ("interpret", 24), ("policy", 24), ("referral", 10), ("other", 8)]
CONTACT_W: list[tuple[ContactMethod, float]] = [("phone", 35), ("zalo", 25), ("kakao", 20), ("sms", 15), ("visit", 5)]


def build_mock_cases(now: datetime) -> list[CenterCase]:
    r = rng(20261024)
    cases: list[CenterCase] = []
    for n in range(24):
        sc = SCENARIOS[n % len(SCENARIOS)]
        language = weighted(r, LANG_W)
        # 최근 14일 안, 일부는 운영 시간 외(야간·주말)
        created = now - timedelta(hours=n * 13 + int(r() * 10) + 2)
        intake = Intake(
            id=f"mock-in-{n}",
            language=language,
            body_parts=sc.parts,
            symptoms=sc.syms,
            free_text=sc.text[language],
            onset=ONSET_POOL[int(r() * len(ONSET_POOL))],
            work_related=sc.work,
            work_type=sc.type,
            industry=weighted(r, INDUSTRY_W),
            district=weighted(r, DISTRICT_W),
            created_at=clock.iso_utc(created),
        )
        insurance = weighted(r, INS_W)
        # 사례마다 하나씩 뽑는다(프론트와 같은 시드 순서)
        request_types = [weighted(r, REQ_W)]
        contact_method = weighted(r, CONTACT_W)
        ulsan90 = weighted(r, [("yes", 1), ("no", 1)]) if insurance == "no" else None
        coverage = route_coverage(CoverageInput(work_related=sc.work, insurance=insurance, ulsan90=ulsan90))
        summary = build_center_summary(
            CenterSummaryInput(
                intake=intake,
                request_types=request_types,
                coverage=coverage,
                insurance=insurance,
                contact_method=contact_method,
            )
        )
        urgency, reasons = rate_urgency(sc.work, insurance)
        status: CaseStatus
        if n < 5:
            status = "new"
        elif n < 12:
            status = weighted(r, [("progress", 2), ("new", 1)])
        else:
            status = weighted(r, [("done", 3), ("progress", 1)])
        cases.append(
            CenterCase(
                id=f"C-{1000 + 24 - n}",
                created_at=clock.iso_utc(created),
                language=language,
                request_types=request_types,
                urgency=urgency,
                urgency_reasons=reasons,
                district=intake.district,
                industry=intake.industry,
                status=status,
                summary_ko=summary.ko,
                original_native=summary.native,
                consented_items=["증상", "부위", "시작 시점", "경위", "자유 입력 메모"],
                coverage_path=coverage.path,
                contact_method=contact_method,
                contact=None if contact_method == "visit" else f"010-0000-00{10 + n}",
                after_hours=is_after_hours(created),
                work_related=sc.work,
                insurance=insurance,
                live=False,
            )
        )
    return cases


# ---------------------------------------------------------------------------
# 통계 원천: 익명 레코드(날짜·구군·업종·언어·보험·시간외)만 둔다. API로 원천을 내보내지 않는다.
# 날짜·구군·언어·시간외 비율은 센터 회신(2026-10-31, 동구 센터 의료 상담 329건)의 분포를 따른 합성값이다.
# 업종·보험·요청 종류·업무 관련은 회신에 없어 이전 가중치 그대로다.
# ---------------------------------------------------------------------------
STAT_COUNT = 329
# 최근 6개월 월별 건수(오래된 달부터, 마지막이 이번 달)
STAT_MONTH_W = [16, 25, 41, 85, 97, 65]
# 국적 → 언어: 러시아·카자흐스탄·우즈베키스탄·키르기스스탄·타지키스탄 → 러시아어, 인도네시아, 스리랑카 → 싱할라어, 필리핀 → 영어·필리핀어
STAT_LANG_W: list[tuple[Lang, float]] = [("ru", 44), ("id", 25), ("si", 15), ("en", 8), ("tl", 4), ("vi", 2), ("ko", 2)]
# 주소가 구까지 적힌 건만(동구 센터 회신이라 동구가 많다, 중구는 0건)
STAT_DISTRICT_W: list[tuple[District, float]] = [("dong", 196), ("buk", 20), ("ulju", 17), ("nam", 8)]
# 운영 시간 외 25건 + 주말 27건 = 52 / 329
STAT_AFTER_HOURS = 52 / 329


def stat_date(now: datetime, u: float) -> datetime:
    """난수 하나로 최근 6개월 중 한 날을 고른다. 달은 STAT_MONTH_W 비율, 날은 그 달 안에서 고르게(이번 달은 오늘까지)."""
    k = now.astimezone(clock.SEOUL)
    x = u * sum(STAT_MONTH_W)
    i = 0
    while i < len(STAT_MONTH_W) - 1 and x >= STAT_MONTH_W[i]:
        x -= STAT_MONTH_W[i]
        i += 1
    back = len(STAT_MONTH_W) - 1 - i
    year, month0 = divmod(k.year * 12 + k.month - 1 - back, 12)
    span = k.day if back == 0 else calendar.monthrange(year, month0 + 1)[1]
    day = 1 + int((x / STAT_MONTH_W[i]) * span)
    return k.replace(year=year, month=month0 + 1, day=day)


@dataclass(frozen=True)
class StatRecord:
    date: datetime
    district: District
    industry: Industry
    language: Lang
    insurance: YesNoUnknown
    after_hours: bool
    request_type: RequestType
    work_related: YesNoUnknown


def build_stat_records(now: datetime) -> list[StatRecord]:
    r = rng(77)
    out: list[StatRecord] = []
    for _ in range(STAT_COUNT):
        out.append(
            StatRecord(
                date=stat_date(now, r()),
                district=weighted(r, STAT_DISTRICT_W),
                industry=weighted(r, INDUSTRY_W),
                language=weighted(r, STAT_LANG_W),
                insurance=weighted(r, INS_W),
                after_hours=r() < STAT_AFTER_HOURS,
                request_type=weighted(r, REQ_W),
                work_related=weighted(r, [("yes", 48), ("no", 34), ("unknown", 18)]),
            )
        )
    return out
