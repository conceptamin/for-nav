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
from app.templates.common import join_terms, pick, tri
from app.vocab import BODY_PARTS, DISTRICTS, INDUSTRIES, LANGUAGE_NAMES_KO, ONSETS, SYMPTOMS, WORK_TYPES, Lang

# ---------------------------------------------------------------------------
# FR-60 의료진용 리포트
# ---------------------------------------------------------------------------
FIELD_LABEL: dict[ReportField, dict[str, str]] = {
    "symptoms": tri("증상", "Symptoms", "Triệu chứng"),
    "bodyParts": tri("부위", "Body part", "Vị trí"),
    "onset": tri("시작 시점", "Started", "Bắt đầu"),
    "circumstance": tri("경위", "How it happened", "Hoàn cảnh"),
    "note": tri("환자 메모(원문)", "My note (original)", "Ghi chú (nguyên văn)"),
    "baseline": tri("기저 정보", "Basic health info", "Thông tin sức khỏe cơ bản"),
    "meds": tri("복용 중인 약", "Medicines I take", "Thuốc đang dùng"),
}


def field_label(field: ReportField, lang: Lang) -> str:
    return pick(FIELD_LABEL[field], lang)


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


DRINK = {
    "none": tri("안 함", "none", "không"),
    "sometimes": tri("가끔", "sometimes", "thỉnh thoảng"),
    "often": tri("자주", "often", "thường xuyên"),
}
SMOKE = {"no": tri("안 함", "no", "không"), "yes": tri("함", "yes", "có"), "quit": tri("끊음", "quit", "đã bỏ")}
SEX = {"male": tri("남", "Male", "Nam"), "female": tri("여", "Female", "Nữ")}


def baseline_text(p: Profile, key: Lang) -> str:
    parts: list[str] = []
    a = age(p.birth_date)
    sex = SEX[p.sex]
    if a is not None:
        parts.append(f"{a}세 {sex['ko']}" if key == "ko" else f"{a} tuổi, {sex['vi']}" if key == "vi" else f"{a} y/o, {sex['en']}")
    if p.height:
        parts.append(f"{'키' if key == 'ko' else 'Chiều cao' if key == 'vi' else 'Height'} {js_num(p.height)}cm")
    if p.weight:
        parts.append(f"{'체중' if key == 'ko' else 'Cân nặng' if key == 'vi' else 'Weight'} {js_num(p.weight)}kg")
    if p.drinking:
        parts.append(f"{'음주' if key == 'ko' else 'Rượu bia' if key == 'vi' else 'Alcohol'}: {DRINK[p.drinking][key]}")
    if p.smoking:
        parts.append(f"{'흡연' if key == 'ko' else 'Hút thuốc' if key == 'vi' else 'Smoking'}: {SMOKE[p.smoking][key]}")
    return " · ".join(parts)


def _base36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = digits[r] + out
        if n == 0:
            return out


YES_NO_KO = {"yes": "예", "no": "아니요", "unknown": "모름"}
YES_NO_EN = {"yes": "yes", "no": "no", "unknown": "not sure"}
YES_NO_VI = {"yes": "có", "no": "không", "unknown": "không rõ"}


def build_clinician_report(intake: Intake, included: list[ReportField], profile: Profile | None, meds: str) -> ClinicianReport:
    """근로자가 제외한 항목은 아예 계산하지 않는다(LLM에도 보내지 않는 원칙과 동일)."""
    lang = intake.language
    rows: list[ReportRow] = []

    def add(field: ReportField, value_ko: str, value_native: str) -> None:
        if field not in included or not value_ko.strip():
            return
        rows.append(
            ReportRow(
                field=field,
                label_ko=FIELD_LABEL[field]["ko"],
                value_ko=value_ko,
                label_native=pick(FIELD_LABEL[field], lang),
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
        circ_native.append(
            f"Xảy ra khi làm việc: {YES_NO_VI[intake.work_related]}"
            if lang == "vi"
            else f"Happened at work: {YES_NO_EN[intake.work_related]}"
        )
    if intake.work_type:
        circ_ko.append(f"작업 유형: {WORK_TYPES[intake.work_type]['ko']}")
        circ_native.append(f"{'Loại công việc' if lang == 'vi' else 'Type of work'}: {pick(WORK_TYPES[intake.work_type], lang)}")
    if intake.industry:
        circ_ko.append(f"업종: {INDUSTRIES[intake.industry]['ko']}")
        circ_native.append(f"{'Ngành' if lang == 'vi' else 'Industry'}: {pick(INDUSTRIES[intake.industry], lang)}")
    add("circumstance", " / ".join(circ_ko), " / ".join(circ_ko) if lang == "ko" else " / ".join(circ_native))
    # 자유 입력은 번역 LLM이 연결되기 전까지 원문 그대로 둔다. 한국어 입력은 번역이 필요 없다.
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
REQUEST_TYPE_NATIVE: dict[RequestType, dict[str, str]] = {
    "booking": tri("예약 지원", "Booking support", "Hỗ trợ đặt lịch"),
    "interpret": tri("통번역", "Interpretation", "Phiên dịch"),
    "policy": tri("제도 상담", "Insurance & support advice", "Tư vấn bảo hiểm, chế độ"),
    "referral": tri("기관 연계", "Referral to an agency", "Kết nối cơ quan"),
    "other": tri("기타", "Other", "Khác"),
}
INSURANCE_KO = {"yes": "있음", "no": "없음", "unknown": "모름"}


def build_center_summary(i: CenterSummaryInput) -> CenterSummary:
    """사실 요약만 한다. 판단·추측 문장을 넣지 않는다."""
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
    ko.append(f"응급 판정 이력: {'있음' if i.emergency_flag else '없음'}.")
    if i.insurance:
        ko.append(f"건강보험증: {INSURANCE_KO[i.insurance]}.")
    if i.coverage:
        ko.append(f"제도 경로 결과: {PATH_KO[i.coverage.path]}.")
    ko.append(f"요청 유형: {REQUEST_TYPE_KO[i.request_type]}.")
    if i.contact_method:
        ko.append(f"연락 희망: {CONTACT_METHOD_KO[i.contact_method]}.")

    def label(en: str, vi: str, ko_: str) -> str:
        return {"en": en, "vi": vi, "ko": ko_}[lang]

    if parts or syms:
        onset_nv = f" ({pick(ONSETS[intake.onset], lang)})" if intake.onset else ""
        nv.append(f"{label('Problem', 'Vấn đề', '불편한 점')}: {join_terms(syms, lang)} — {join_terms(parts, lang)}{onset_nv}.")
    if intake.work_related:
        answer = {"ko": YES_NO_KO, "en": YES_NO_EN, "vi": YES_NO_VI}[lang][intake.work_related]
        nv.append(f"{label('Happened at work', 'Xảy ra khi làm việc', '업무 중 발생')}: {answer}.")
    if intake.district:
        nv.append(f"{label('Area', 'Khu vực', '지역')}: {pick(DISTRICTS[intake.district], lang)}.")
    if intake.industry:
        nv.append(f"{label('Industry', 'Ngành', '업종')}: {pick(INDUSTRIES[intake.industry], lang)}.")
    if intake.free_text:
        nv.append(f'{label("My note", "Ghi chú", "내 메모")}: "{intake.free_text}"')
    nv.append(f"{label('Request', 'Yêu cầu', '요청')}: {pick(REQUEST_TYPE_NATIVE[i.request_type], lang)}.")
    return CenterSummary(ko=" ".join(ko), native="\n".join(nv))


def request_type_native(t: RequestType, lang: Lang) -> str:
    return pick(REQUEST_TYPE_NATIVE[t], lang)
