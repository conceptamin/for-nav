# 의료진용 리포트(POST /api/report/clinician)와 센터 리포트(POST /api/report/center)의 문장 템플릿.
# frontend/src/domain/templates.ts와 1:1. 진단 표현을 쓰지 않고, 사실 요약만 한다.

from datetime import date, datetime

from app import clock
from app.rules.coverage import PATH_KO
from app.schemas import (
    CenterSummary,
    CenterSummaryInput,
    ClinicianReport,
    ContactMethod,
    Intake,
    Profile,
    ReportField,
    ReportRow,
    RequestType,
)
from app.templates.common import fill, join_terms, pick, tpl
from app.vocab import BODY_PARTS, DISTRICTS, INDUSTRIES, LANGUAGE_NAMES_KO, ONSETS, PACKS, SYMPTOMS, WORK_TYPES, Lang

# ---------------------------------------------------------------------------
# FR-60 의료진용 리포트
# ---------------------------------------------------------------------------
FIELD_LABEL_KO: dict[ReportField, str] = {
    "symptoms": "증상",
    "bodyParts": "부위",
    "onset": "시작 시점",
    "circumstance": "경위",
    "note": "환자 메모(원문)",
    "baseline": "기저 정보",
    "meds": "복용 중인 약",
}


def field_label(field: ReportField, lang: Lang) -> str:
    return FIELD_LABEL_KO[field] if lang == "ko" else tpl(lang)["fields"][field]


def _parse_birth(birth_date: str) -> date | None:
    try:
        return date.fromisoformat(birth_date)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(birth_date)
    except ValueError:
        return None
    return (dt.astimezone(clock.SEOUL) if dt.tzinfo else dt).date()


def age(birth_date: str) -> int | None:
    b = _parse_birth(birth_date)
    if b is None:
        return None
    today = clock.now().date()
    a = today.year - b.year
    if (today.month, today.day) < (b.month, b.day):
        a -= 1
    return a


def js_num(x: float) -> str:
    """JS 템플릿 문자열의 숫자 표기(170.0 → "170")와 맞춘다."""
    return str(int(x)) if float(x).is_integer() else repr(x)


DRINK_KO = {"none": "안 함", "sometimes": "가끔", "often": "자주"}
SMOKE_KO = {"no": "안 함", "yes": "함", "quit": "끊음"}
SEX_KO = {"male": "남", "female": "여"}


def baseline_text(p: Profile, key: Lang) -> str:
    parts: list[str] = []
    a = age(p.birth_date)
    if key == "ko":
        if a is not None:
            parts.append(f"{a}세 {SEX_KO[p.sex]}")
        if p.height:
            parts.append(f"키 {js_num(p.height)}cm")
        if p.weight:
            parts.append(f"체중 {js_num(p.weight)}kg")
        if p.drinking:
            parts.append(f"음주: {DRINK_KO[p.drinking]}")
        if p.smoking:
            parts.append(f"흡연: {SMOKE_KO[p.smoking]}")
        return " · ".join(parts)
    t = tpl(key)
    if a is not None:
        parts.append(fill(t["age"], {"age": str(a), "sex": PACKS[key]["terms"]["sexes"][p.sex]}))
    if p.height:
        parts.append(f"{t['height']} {js_num(p.height)}cm")
    if p.weight:
        parts.append(f"{t['weight']} {js_num(p.weight)}kg")
    if p.drinking:
        parts.append(f"{t['alcohol']}: {t['drinkingValue'][p.drinking]}")
    if p.smoking:
        parts.append(f"{t['smoking']}: {t['smokingValue'][p.smoking]}")
    return " · ".join(parts)


def _base36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if n == 0:
            return out


# 한국어 사용자에게 보일 때의 "모국어" 문구. 다른 언어는 vocab.PACKS 언어 묶음의 templates에 있다.
YES_NO_KO = {"yes": "예", "no": "아니요", "unknown": "모름"}


def build_clinician_report(
    intake: Intake, included: list[ReportField], profile: Profile | None, meds: str, note_translation: str | None = None
) -> ClinicianReport:
    """근로자가 제외한 항목은 아예 계산하지 않는다(LLM에도 보내지 않는 원칙과 동일).

    `note_translation`은 역번역 검사를 통과한 자유 입력 번역(templates/translate.py)이다. 없으면 프론트 템플릿과 같다.
    """
    lang = intake.language
    rows: list[ReportRow] = []

    def add(field: ReportField, value_ko: str, value_native: str) -> None:
        if field not in included or not value_ko.strip():
            return
        rows.append(
            ReportRow(
                field=field,
                label_ko=FIELD_LABEL_KO[field],
                value_ko=value_ko,
                label_native=field_label(field, lang),
                value_native=value_native,
            )
        )

    syms = [SYMPTOMS[s] for s in intake.symptoms]
    parts = [BODY_PARTS[p] for p in intake.body_parts]
    add("symptoms", join_terms(syms, "ko"), join_terms(syms, lang))
    add("bodyParts", join_terms(parts, "ko"), join_terms(parts, lang))
    if intake.onset:
        add("onset", ONSETS[intake.onset]["ko"], pick(ONSETS[intake.onset], lang))

    circ_ko: list[str] = []
    circ_native: list[str] = []
    if intake.work_related:
        circ_ko.append(f"업무 중 발생: {YES_NO_KO[intake.work_related]}")
        if lang != "ko":
            circ_native.append(f"{tpl(lang)['happenedAtWork']}: {tpl(lang)['yesNo'][intake.work_related]}")
    if intake.work_type:
        circ_ko.append(f"작업 유형: {WORK_TYPES[intake.work_type]['ko']}")
        if lang != "ko":
            circ_native.append(f"{tpl(lang)['workType']}: {pick(WORK_TYPES[intake.work_type], lang)}")
    if intake.industry:
        circ_ko.append(f"업종: {INDUSTRIES[intake.industry]['ko']}")
        if lang != "ko":
            circ_native.append(f"{tpl(lang)['industry']}: {pick(INDUSTRIES[intake.industry], lang)}")
    add("circumstance", " / ".join(circ_ko), " / ".join(circ_ko) if lang == "ko" else " / ".join(circ_native))
    # 번역이 없으면 원문 그대로 둔다. 한국어 입력은 번역이 필요 없다. 번역이 있어도 원문을 함께 남긴다.
    if note_translation:
        note_ko = f"{note_translation} (원문: {intake.free_text})"
    else:
        note_ko = intake.free_text if lang == "ko" else f"{intake.free_text} (원문, 번역 미연결)"
    add("note", note_ko if intake.free_text else "", intake.free_text)
    if profile:
        add("baseline", baseline_text(profile, "ko"), baseline_text(profile, lang))
    add("meds", meds, meds)

    now = clock.now()
    return ClinicianReport(
        id=f"rp-{_base36(clock.epoch_ms(now))}",
        intake_id=intake.id,
        language=lang,
        included=included,
        rows=rows,
        created_at=clock.iso_utc(now),
    )


# ---------------------------------------------------------------------------
# FR-70 센터 리포트
# ---------------------------------------------------------------------------
REQUEST_TYPE_KO: dict[RequestType, str] = {
    "booking": "예약 지원",
    "interpret": "통번역",
    "policy": "제도 상담",
    "referral": "기관 연계",
    "other": "기타",
}
CONTACT_METHOD_KO: dict[ContactMethod, str] = {
    "phone": "전화",
    "sms": "문자",
    "kakao": "카카오톡",
    "zalo": "Zalo",
    "visit": "센터 방문",
}
SUMMARY_KO = {
    "problem": "불편한 점",
    "happenedAtWork": "업무 중 발생",
    "area": "지역",
    "industry": "업종",
    "myNote": "내 메모",
    "request": "요청",
    "yesNo": YES_NO_KO,
}
INSURANCE_KO = {"yes": "있음", "no": "없음", "unknown": "모름"}


def build_center_summary(i: CenterSummaryInput, note_translation: str | None = None) -> CenterSummary:
    """사실 요약만 한다. 판단·추측 문장을 넣지 않는다.

    `note_translation`이 있으면 한국어 요약 끝에 번역 메모 한 문장을 더한다. 원문은 native의 메모 줄에 그대로 남는다.
    """
    intake = i.intake
    lang = intake.language
    parts = [BODY_PARTS[p] for p in intake.body_parts]
    syms = [SYMPTOMS[s] for s in intake.symptoms]
    ko: list[str] = []
    nv: list[str] = []
    where = [
        x
        for x in [
            DISTRICTS[intake.district]["ko"] if intake.district else None,
            f"{INDUSTRIES[intake.industry]['ko']} 업종" if intake.industry else None,
        ]
        if x
    ]
    where_ko = f"({', '.join(where)})" if where else ""
    ko.append(f"{LANGUAGE_NAMES_KO[lang]} 사용 근로자{where_ko}.")
    onset_ko = f", {ONSETS[intake.onset]['ko']} 시작" if intake.onset else ""
    if parts or syms:
        ko.append(f"{join_terms(parts, 'ko') or '부위 미입력'} {join_terms(syms, 'ko') or ''}{onset_ko}.")
    if intake.work_related:
        work_type_ko = f"({WORK_TYPES[intake.work_type]['ko']})" if intake.work_type else ""
        ko.append(f"업무 중 발생: {YES_NO_KO[intake.work_related]}{work_type_ko}.")
    if i.insurance:
        ko.append(f"건강보험증: {INSURANCE_KO[i.insurance]}.")
    if i.coverage:
        ko.append(f"제도 경로 결과: {PATH_KO[i.coverage.path]}.")
    ko.append(f"요청 유형: {', '.join(REQUEST_TYPE_KO[r] for r in i.request_types)}.")
    if i.contact_method:
        ko.append(f"연락 희망: {CONTACT_METHOD_KO[i.contact_method]}.")
    if note_translation:
        ko.append(f'근로자 메모(번역): "{note_translation}"')

    t = SUMMARY_KO if lang == "ko" else tpl(lang)
    if parts or syms:
        onset_nv = f" ({pick(ONSETS[intake.onset], lang)})" if intake.onset else ""
        nv.append(f"{t['problem']}: {join_terms(syms, lang)} — {join_terms(parts, lang)}{onset_nv}.")
    if intake.work_related:
        nv.append(f"{t['happenedAtWork']}: {t['yesNo'][intake.work_related]}.")
    if intake.district:
        nv.append(f"{t['area']}: {pick(DISTRICTS[intake.district], lang)}.")
    if intake.industry:
        nv.append(f"{t['industry']}: {pick(INDUSTRIES[intake.industry], lang)}.")
    if intake.free_text:
        nv.append(f'{t["myNote"]}: "{intake.free_text}"')
    nv.append(f"{t['request']}: {', '.join(request_type_native(r, lang) for r in i.request_types)}.")
    return CenterSummary(ko=" ".join(ko), native="\n".join(nv))


def request_type_native(t: RequestType, lang: Lang) -> str:
    return REQUEST_TYPE_KO[t] if lang == "ko" else tpl(lang)["requestTypes"][t]
