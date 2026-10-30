# 증상 분류(POST /api/triage)와 자유 입력 추출(POST /api/extract). frontend/src/domain/triage.ts와 1:1.
# - 응급 감지: 키워드 규칙 OR 보조 점수(모델이 있으면 응급도 모델, backlog 06). 둘 중 하나라도 응급이면 응급.
# - 증상 추출: LLM 자리. 목업에서는 다국어 키워드 사전으로 추출하고, 못 찾은 항목은 버튼으로 다시 묻는다.
# - 진료과 추천: 결정적 규칙표. 같은 입력이면 같은 결과. 모델이 있으면 규칙표의 막연한 분기(GENERIC)만 모델 상위 2개로 바꾼다.

from collections.abc import Callable

from app.schemas import DepartmentPair, EmergencyReason, Extraction, Intake, ModelPrediction, TriageResult
from app.vocab import PACKS, BodyPart, LangPack, Onset, Symptom, WorkType, YesNoUnknown

# ---------------------------------------------------------------------------
# 응급 키워드 규칙. 한국어는 여기에, 다른 언어는 vocab.PACKS 언어 묶음의 emergency에 있고 합쳐 쓴다. 소문자 부분 일치.
# ---------------------------------------------------------------------------
EMERGENCY_KEYWORDS_KO: dict[EmergencyReason, list[str]] = {
    "unconscious": ["의식", "기절", "쓰러"],
    "breathing": ["숨을 못", "숨이 안", "호흡곤란", "호흡 곤란"],
    "chest": ["가슴 통증", "가슴이 아", "가슴이 조"],
    "heavyBleeding": ["피가 멈추지", "피가 안 멈", "피가 많이", "출혈이 심"],
    "amputation": ["절단됐", "절단되", "잘렸", "잘려"],
    "fall": ["추락", "높은 곳에서 떨어"],
    "seizure": ["경련", "발작"],
    "stroke": ["마비", "말이 어눌", "한쪽이 저"],
    "severeBurn": ["큰 화상", "전신 화상", "감전"],
    "chemicalEye": ["눈에 화학", "눈에 약품", "눈에 약물"],
    "poisoning": ["가스를 마", "가스 마셨", "중독"],
}

# 머리 부상은 구토·어지러움이 함께 있을 때만 응급으로 본다.
HEAD_INJURY_KO = ["머리를 부딪", "머리를 다쳐", "머리를 맞"]
VOMIT_KO = ["토했", "구토"]

# 보조 점수에 쓰는 심각도 표현
SEVERITY_KO = ["심하", "심해", "너무", "매우"]


def _with_packs(ko: list[str], pick: Callable[[LangPack], list[str]]) -> list[str]:
    return [*ko, *(w for pack in PACKS.values() for w in pick(pack))]


EMERGENCY_KEYWORDS: dict[EmergencyReason, list[str]] = {
    reason: _with_packs(words, lambda p, r=reason: p["emergency"]["keywords"][r]) for reason, words in EMERGENCY_KEYWORDS_KO.items()
}
HEAD_INJURY = _with_packs(HEAD_INJURY_KO, lambda p: p["emergency"]["headInjury"])
VOMIT = _with_packs(VOMIT_KO, lambda p: p["emergency"]["vomit"])
SEVERITY = _with_packs(SEVERITY_KO, lambda p: p["emergency"]["severity"])


def includes_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def rule_reasons(intake: Intake) -> list[EmergencyReason]:
    """키워드 규칙 + 버튼 조합 규칙. 순서는 프론트 Set 삽입 순서와 같다."""
    text = intake.free_text.lower()
    reasons: dict[EmergencyReason, None] = {}
    for reason, words in EMERGENCY_KEYWORDS.items():
        if includes_any(text, words):
            reasons[reason] = None
    s = set(intake.symptoms)
    b = set(intake.body_parts)
    if "breath" in s:
        reasons["breathing"] = None
    if "chest" in b and "pain" in s:
        reasons["chest"] = None
    if "eye" in b and "chemical" in s:
        reasons["chemicalEye"] = None
    if includes_any(text, HEAD_INJURY) and ("nausea" in s or "dizzy" in s or includes_any(text, VOMIT)):
        reasons["headInjury"] = None
    return list(reasons)


def model_score(intake: Intake) -> int:
    """
    보조 점수: 실서비스에서는 자체 응급 감지 모델이 이 자리에 들어간다.
    목업에서는 재현율을 우선해 위험 신호를 가산하는 단순 점수로 대신한다.
    """
    text = intake.free_text.lower()
    s = set(intake.symptoms)
    b = set(intake.body_parts)
    score = 0
    if includes_any(text, SEVERITY):
        score += 1
    if "bleeding" in s:
        score += 1
    if "cut" in s and "bleeding" in s:
        score += 1
    if "burn" in s and ("whole" in b or "head" in b):
        score += 2
    if "head" in b and "dizzy" in s and "nausea" in s:
        score += 3
    if "cantmove" in s and ("back" in b or "whole" in b):
        score += 1
    if "chemical" in s:
        score += 1
    if "fever" in s and "dizzy" in s and "nausea" in s:
        score += 1
    return score


MODEL_THRESHOLD = 3

# ---------------------------------------------------------------------------
# 진료과 규칙표
# ---------------------------------------------------------------------------
MSK: list[BodyPart] = ["back", "arm", "hand", "leg", "foot"]


def recommend_department(body_parts: list[BodyPart], symptoms: list[Symptom]) -> DepartmentPair:
    return rule_department(body_parts, symptoms)[0]


def rule_department(body_parts: list[BodyPart], symptoms: list[Symptom]) -> tuple[DepartmentPair, bool]:
    """(규칙표 결과, 막연한 분기인지). 막연한 분기는 내과 묶음(배·가슴·온몸·발열·구토·어지러움)과 기본값이다.

    기본값은 부위가 하나라도 있으면 닿지 않는다(13개 부위가 모두 앞 분기에 있다). 그래서 내과 묶음까지 모델에 맡긴다(backlog 06).
    """
    b = set(body_parts)
    s = set(symptoms)
    msk = any(p in b for p in MSK)
    if "chemical" in s:
        return DepartmentPair(primary="occ", alt="derm" if "skin" in b else "internal"), False
    if "eye" in b or "foreign" in s:
        return DepartmentPair(primary="ophth", alt="family"), False
    if "teeth" in b:
        return DepartmentPair(primary="dental", alt="family"), False
    if "burn" in s:
        return DepartmentPair(primary="surgery", alt="derm"), False
    if "cut" in s or "bleeding" in s:
        return DepartmentPair(primary="surgery", alt="ortho" if msk else "family"), False
    if "skin" in b or "rash" in s:
        return DepartmentPair(primary="derm", alt="family"), False
    if "ent" in b or "cough" in s:
        return DepartmentPair(primary="ent", alt="internal"), False
    if msk:
        return DepartmentPair(primary="ortho", alt="neuro" if "numb" in s else "family"), False
    if "head" in b:
        return DepartmentPair(primary="neuro", alt="internal"), False
    if "abdomen" in b or "chest" in b or "whole" in b or "fever" in s or "nausea" in s or "dizzy" in s:
        return DepartmentPair(primary="internal", alt="family"), True
    return DepartmentPair(primary="family", alt="internal"), True


def department_for(intake: Intake, model: ModelPrediction | None) -> DepartmentPair:
    """규칙표가 명시적으로 정한 조합은 규칙표, 막연한 분기만 모델 앙상블 상위 2개다."""
    pair, generic = rule_department(intake.body_parts, intake.symptoms)
    if model is None or not generic:
        return pair
    primary, alt = model.department_top2
    return DepartmentPair(primary=primary, alt=alt)


def triage(intake: Intake, model: ModelPrediction | None = None) -> TriageResult:
    """규칙이 먼저다. 규칙이 응급이면 모델과 관계없이 응급이다.

    `model`은 응급도·진료과 모델 예측(app/model.py)이다. 있으면 보조 점수 대신 모델 응급도로 byModel을 정하고,
    없으면 프론트와 같다. modelScore는 모델 유무와 관계없이 보조 점수 그대로다.
    """
    reasons = rule_reasons(intake)
    by_rule = len(reasons) > 0
    score = model_score(intake)
    by_model = model.acuity == "emergency" if model else score >= MODEL_THRESHOLD
    if by_model and not reasons:
        reasons.append("riskScore")
    missing: list = []
    if not intake.body_parts:
        missing.append("bodyParts")
    if not intake.symptoms:
        missing.append("symptoms")
    return TriageResult(
        emergency=len(reasons) > 0,
        reasons=reasons,
        by_rule=by_rule,
        by_model=by_model,
        model_score=score,
        department=department_for(intake, model) if not missing else None,
        missing=missing,
        model=model,
    )


# ---------------------------------------------------------------------------
# 자유 입력 추출(LLM 자리). 찾지 못한 값은 null로 두고 추측하지 않는다.
# ---------------------------------------------------------------------------
BODY_WORDS: dict[BodyPart, list[str]] = {
    "head": ["머리", "head", "đầu"],
    "eye": ["눈", "eye", "mắt"],
    "ent": ["귀", "코", "목구멍", " ear", "nose", "throat", " tai", "mũi", "họng"],
    "teeth": ["이빨", "치아", "잇몸", "tooth", "teeth", "gum", "răng", "lợi"],
    "chest": ["가슴", "chest", "ngực"],
    "abdomen": ["배가", "복부", "stomach", "belly", "abdomen", "bụng"],
    "back": ["허리", "등이", "my back", "lower back", "waist", "lưng"],
    "arm": ["팔", "어깨", " arm", "shoulder", "cánh tay", "vai"],
    "hand": ["손", "hand", "finger", "wrist", "bàn tay", "ngón tay", "cổ tay"],
    "leg": ["다리", "무릎", "leg", "knee", "đầu gối", "chân"],
    "foot": ["발", "foot", "feet", "ankle", "toe", "bàn chân", "cổ chân"],
    "skin": ["피부", "skin", "da "],
    "whole": ["온몸", "전신", "whole body", "all over", "toàn thân", "khắp người"],
}

SYMPTOM_WORDS: dict[Symptom, list[str]] = {
    # 'painting'과 겹치지 않도록 영어 pain은 끝 경계를 붙인다.
    "pain": ["아파", "아프", "통증", "pain ", "pain,", "pain.", "painful", "hurt", "ache", "đau"],
    "swelling": ["붓", "부었", "swell", "swollen", "sưng"],
    "cut": ["베였", "베인", "찢어", "cut", "wound", "vết cắt", "bị cắt", "rách"],
    "bleeding": ["피가", "출혈", "bleed", "blood", "chảy máu", "máu"],
    "burn": ["화상", "데었", "burn", "bỏng"],
    "numb": ["저려", "저림", "numb", "tingl", "tê"],
    "cantmove": ["못 움직", "움직일 수 없", "can't move", "cannot move", "không cử động", "khó cử động"],
    "fever": ["열이", "열나", "fever", "sốt"],
    "cough": ["기침", "cough", " ho ", " ho,"],
    "dizzy": ["어지러", "dizzy", "chóng mặt", "choáng"],
    "rash": ["가려", "두드러기", "발진", "itch", "rash", "ngứa", "phát ban", "mẩn"],
    "nausea": ["토했", "구토", "메스꺼", "vomit", "nausea", "threw up", "buồn nôn", "nôn"],
    "breath": ["숨쉬기", "숨이 차", "breath", "khó thở"],
    "chemical": ["화학", "약품", "시너", "chemical", "solvent", "thinner", "hóa chất", "dung môi"],
    "foreign": ["눈에 뭐가", "이물", "something in my eye", "dust in my eye", "bụi vào mắt", "dị vật"],
}

ONSET_WORDS: dict[Onset, list[str]] = {
    "today": ["오늘", "방금", "today", "just now", "this morning", "tonight", "hôm nay", "vừa", "sáng nay", "tối nay"],
    "yesterday": ["어제", "yesterday", "last night", "hôm qua", "tối qua"],
    "days": ["며칠", "2일", "3일", "few days", "2 days", "3 days", "vài ngày", "2 ngày", "3 ngày"],
    "week": ["일주일", "한 달", "week", "month", "tuần", "tháng"],
}

WORK_WORDS = [
    "일하다",
    "작업",
    "공장",
    "회사에서",
    "at work",
    "while working",
    "factory",
    "machine",
    "đang làm",
    "lúc làm",
    "ở công ty",
    "nhà máy",
    "máy",
]
NOT_WORK_WORDS = ["집에서", "퇴근 후", "at home", "after work", "ở nhà", "sau giờ làm"]

WORK_TYPE_WORDS: dict[WorkType, list[str]] = {
    "welding": ["용접", "weld", "thợ hàn", "máy hàn", "hàn điện", "đang hàn"],
    "lifting": ["들다가", "무거운", "운반", "lift", "carry", "nâng", "khuân", "bê "],
    "machine": ["프레스", "기계", "press", "machine", "máy dập", "máy"],
    "grinding": ["연마", "그라인더", "grind", "grinder", "mài"],
    "painting": ["도장", "페인트", "paint", "sơn"],
    "assembly": ["조립", "assembl", "lắp ráp"],
}


def match_keys[K](text: str, words: dict[K, list[str]]) -> list[K]:
    return [k for k, ws in words.items() if includes_any(text, ws)]


def extract_from_text(free_text: str) -> Extraction:
    text = f" {free_text.lower()} "
    onsets = match_keys(text, ONSET_WORDS)
    work_related: YesNoUnknown | None = None
    # "ở nhà máy"(공장에서)가 "ở nhà"(집에서)로 잡히지 않도록 공장 표현을 먼저 지운다.
    if includes_any(text.replace("nhà máy", ""), NOT_WORK_WORDS):
        work_related = "no"
    elif includes_any(text, WORK_WORDS):
        work_related = "yes"
    work_types = match_keys(text, WORK_TYPE_WORDS)
    return Extraction(
        body_parts=match_keys(text, BODY_WORDS),
        symptoms=match_keys(text, SYMPTOM_WORDS),
        onset=onsets[0] if onsets else None,
        work_related=work_related,
        work_type=work_types[0] if work_types else None,
    )


def merge_extraction(intake: Intake, ex: Extraction) -> Intake:
    """버튼 입력을 우선하고, 빈 항목만 추출값으로 채운다."""
    return intake.model_copy(
        update={
            "body_parts": intake.body_parts or ex.body_parts,
            "symptoms": intake.symptoms or ex.symptoms,
            "onset": intake.onset if intake.onset is not None else ex.onset,
            "work_related": intake.work_related if intake.work_related is not None else ex.work_related,
            "work_type": intake.work_type if intake.work_type is not None else ex.work_type,
        }
    )


def filled_by_extraction(before: Intake, merged: Intake) -> bool:
    """추출로 채운 값이 있는지. 프론트 Intake.tsx의 판단과 같다."""
    return (
        (not before.body_parts and len(merged.body_parts) > 0)
        or (not before.symptoms and len(merged.symptoms) > 0)
        or merged.onset != before.onset
        or merged.work_related != before.work_related
        or merged.work_type != before.work_type
    )


REASON_KO: dict[EmergencyReason, str] = {
    "unconscious": "의식 저하·쓰러짐",
    "breathing": "호흡 곤란",
    "chest": "가슴 통증",
    "heavyBleeding": "지혈되지 않는 출혈",
    "amputation": "신체 절단 의심",
    "fall": "높은 곳에서 추락",
    "seizure": "경련",
    "stroke": "마비·말 어눌함",
    "severeBurn": "심한 화상·감전",
    "chemicalEye": "눈에 화학물질",
    "headInjury": "머리 부상 후 구토·어지러움",
    "poisoning": "가스·약물 중독 의심",
    "riskScore": "위험 신호 점수 높음",
}
