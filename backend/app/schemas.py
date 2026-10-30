# Pydantic 모델 — frontend/src/domain/*.ts 타입과 1:1.
# JSON 필드명은 camelCase(프론트 타입 그대로), Python 코드 안에서는 snake_case를 쓴다.

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.vocab import Acuity, AgeGroup, BodyPart, Department, District, Industry, Lang, Mental, Onset, Sex, Symptom, WorkType, YesNoUnknown


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def absent_if_none(**constraints):
    """선택 필드. 값이 없으면 응답 JSON에 키를 넣지 않는다 — 프론트 타입에 아직 없는 필드를 더할 때 쓴다."""
    return Field(default=None, exclude_if=lambda v: v is None, **constraints)


# ---------------------------------------------------------------------------
# domain/triage.ts
# ---------------------------------------------------------------------------
class Intake(CamelModel):
    id: str
    language: Lang
    body_parts: list[BodyPart] = []
    symptoms: list[Symptom] = []
    free_text: str = ""
    onset: Onset | None = None
    work_related: YesNoUnknown | None = None
    work_type: WorkType | None = None
    industry: Industry | None = None
    district: District | None = None
    created_at: str
    # 응급도 모델 입력(backlog 10). 프론트 Intake 타입에는 아직 없다. 없으면 응답에 키를 넣지 않는다
    age_group: AgeGroup | None = absent_if_none()
    sex: Sex | None = absent_if_none()
    injury: bool | None = absent_if_none(strict=True)
    pain_score: int | None = absent_if_none(ge=0, le=10, strict=True)
    mental: Mental | None = absent_if_none()


EmergencyReason = Literal[
    "unconscious",
    "breathing",
    "chest",
    "heavyBleeding",
    "amputation",
    "fall",
    "seizure",
    "stroke",
    "severeBurn",
    "chemicalEye",
    "headInjury",
    "poisoning",
    "riskScore",
]


class DepartmentPair(CamelModel):
    primary: Department
    alt: Department


class ShapItem(CamelModel):
    # 응급도 피처 이름(modeling features/buttons.py FEATURE_NAMES), 입력값(모르면 null), 판정 클래스에 대한 기여도
    feature: str
    value: float | None
    contribution: float


class ModelPrediction(CamelModel):
    """modeling predict()의 출력(app/model.py). 응답에는 앞 네 필드만 내보낸다."""

    acuity: Acuity
    acuity_proba: dict[Acuity, float]
    department_proba: dict[Department, float]
    shap: list[ShapItem]
    # 진료과 앙상블 상위 2개(확신이 낮으면 모델 쪽 폴백 family·internal). 규칙표 분기를 대신할 때만 쓴다
    department_top2: list[Department] = Field(exclude=True, min_length=2, max_length=2)
    department_fallback: bool = Field(exclude=True)


class TriageResult(CamelModel):
    emergency: bool
    reasons: list[EmergencyReason]
    # 규칙과 보조 점수(모델이 있으면 응급도 모델) 각각의 판정(센터·평가 화면 표시용)
    by_rule: bool
    by_model: bool
    model_score: int
    department: DepartmentPair | None
    missing: list[Literal["bodyParts", "symptoms"]]
    # 서버 전용 선택 필드. 응급도·진료과 모델 결과(backlog 06), 모델이 없으면 키가 없다
    model: ModelPrediction | None = absent_if_none()


class Extraction(CamelModel):
    body_parts: list[BodyPart]
    symptoms: list[Symptom]
    onset: Onset | None
    work_related: YesNoUnknown | None
    work_type: WorkType | None


class ExtractRequest(CamelModel):
    intake: Intake


class ExtractResponse(CamelModel):
    extraction: Extraction
    intake: Intake
    # 추출로 채운 값이 있는지(프론트 Intake.tsx의 판단과 같다)
    filled: bool
    # 서버 전용 선택 필드. 추출에 LLM을 썼는지, 키워드 사전으로 대체했는지
    source: Literal["llm", "keywords"] | None = None


# ---------------------------------------------------------------------------
# domain/coverage.ts
# ---------------------------------------------------------------------------
CoveragePath = Literal["industrial", "nhis", "ulsanSupport", "center"]
DocId = Literal["arc", "insuranceCard", "accidentNote", "photos", "receipts", "meds"]


class Institution(CamelModel):
    id: Literal["kcomwel", "nhis", "center", "ulsan"]
    # 확인된 번호만 넣는다. 미확인이면 null
    phone: str | None


class CoverageInput(CamelModel):
    work_related: YesNoUnknown
    insurance: YesNoUnknown
    # 보험이 "아니요"일 때만 묻는다
    ulsan90: YesNoUnknown | None = None


class CoverageResult(CamelModel):
    path: CoveragePath
    also_industrial: bool
    institutions: list[Institution]
    docs: list[DocId]
    info_date: str


class CenterHours(CamelModel):
    open_hour: int
    close_hour: int
    # 0=일요일 … 6=토요일(JS Date.getDay와 같은 번호)
    workdays: list[int]


class Meta(CamelModel):
    info_date: str
    center_hours: CenterHours


# ---------------------------------------------------------------------------
# domain/templates.ts
# ---------------------------------------------------------------------------
class Line(CamelModel):
    ko: str
    native: str
    pron: str


class KoNative(CamelModel):
    ko: str
    native: str


class DeskSheet(CamelModel):
    lines: list[Line]
    first_visit: bool
    work_related_ko: str
    docs_ko: list[KoNative]


class Faq(CamelModel):
    id: str
    # 질문. 한국어 사용자는 native가 ko와 같다
    q: KoNative
    answers: list[Line]


class CallScript(CamelModel):
    lines: list[Line]
    faq: list[Faq]


class VisitHelperRequest(CamelModel):
    intake: Intake
    department: Department
    first_visit: bool
    lang: Lang


class VisitHelperResponse(CamelModel):
    desk: DeskSheet
    call: CallScript
    # 서버 전용 선택 필드. LLM으로 채운 슬롯 이름 목록(templates/llm_slots.py), 없으면 빈 배열
    llm_slots: list[str] | None = absent_if_none()


class Profile(CamelModel):
    birth_date: str
    sex: Literal["male", "female"]
    height: float | None = None
    weight: float | None = None
    drinking: Literal["none", "sometimes", "often"] | None = None
    smoking: Literal["no", "yes", "quit"] | None = None


ReportField = Literal["symptoms", "bodyParts", "onset", "circumstance", "note", "baseline", "meds"]
REPORT_FIELDS: list[ReportField] = ["symptoms", "bodyParts", "onset", "circumstance", "note", "baseline", "meds"]


class ReportRow(CamelModel):
    field: ReportField
    label_ko: str
    value_ko: str
    label_native: str
    value_native: str


class ClinicianReport(CamelModel):
    id: str
    intake_id: str
    language: Lang
    included: list[ReportField]
    rows: list[ReportRow]
    created_at: str
    # 서버 전용 선택 필드. 템플릿 빌더는 비워 두고(동기화 테스트가 프론트 결과와 그대로 비교) 라우터가 채운다
    llm_slots: list[str] | None = absent_if_none()


class ClinicianReportRequest(CamelModel):
    intake: Intake
    included: list[ReportField]
    profile: Profile | None = None
    meds: str = ""


RequestType = Literal["booking", "interpret", "policy", "referral", "other"]
ContactMethod = Literal["phone", "sms", "kakao", "zalo", "visit"]


class CenterSummaryInput(CamelModel):
    intake: Intake
    emergency_flag: bool
    request_type: RequestType
    coverage: CoverageResult | None = None
    insurance: YesNoUnknown | None = None
    contact_method: ContactMethod | None = None


class CenterSummary(CamelModel):
    ko: str
    native: str


# ---------------------------------------------------------------------------
# domain/centerCase.ts
# ---------------------------------------------------------------------------
CaseStatus = Literal["new", "progress", "done"]
Urgency = Literal["high", "medium", "low"]


class CenterCase(CamelModel):
    id: str
    created_at: str
    language: Lang
    request_type: RequestType
    urgency: Urgency
    urgency_reasons: list[str]
    district: District | None
    industry: Industry | None
    status: CaseStatus
    summary_ko: str
    original_native: str
    # 근로자가 센터 전송에 동의한 항목(한국어 표시)
    consented_items: list[str]
    coverage_path: CoveragePath | None
    contact_method: ContactMethod | None
    contact: str | None
    after_hours: bool
    emergency_flag: bool
    work_related: YesNoUnknown | None
    insurance: YesNoUnknown | None
    # 데모에서 실제로 전송한 사례(mock과 구분)
    live: bool


class NewCaseRequest(CenterSummaryInput):
    contact: str | None = None
    consented_items: list[str] = []


class NewCaseResponse(CamelModel):
    case: CenterCase
    # 다음 운영일(Asia/Seoul, YYYY-MM-DD)
    next_open_date: str


class StatusPatch(CamelModel):
    status: CaseStatus


class StatCell(CamelModel):
    key: str
    # 5건 미만이면 null
    n: int | None


class CenterStats(CamelModel):
    total: int | None
    after_hours_rate: float | None
    work_related_rate: float | None
    no_insurance_rate: float | None
    by_industry: list[StatCell]
    by_language: list[StatCell]
    by_insurance: list[StatCell]
    by_after_hours: list[StatCell]
