# 증상 분류(POST /api/triage)와 자유 입력 추출(POST /api/extract). frontend/src/domain/triage.ts와 1:1.
# - 응급 여부는 판정하지 않는다(backlog 26). 틀린 판정이 헛된 확신을 주지 않게, 119는 프론트가 판정 없이 늘 보이는 버튼으로만 안내한다.
# - 증상 추출: LLM 자리. 목업에서는 다국어 키워드 사전으로 추출하고, 못 찾은 항목은 버튼으로 다시 묻는다.
# - 진료과 추천: 결정적 규칙표. 같은 입력이면 같은 결과. 모델이 있으면 규칙표의 막연한 분기(GENERIC)만 모델 상위 2개로 바꾼다.

from app.schemas import DepartmentPair, Extraction, Intake, ModelPrediction, TriageResult
from app.vocab import BodyPart, Onset, Symptom, WorkType, YesNoUnknown


def includes_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


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


# 진료과를 모델에 맡기지 않고 규칙표로 고정하는 조합. 예전 응급 조합(가슴 통증, 숨참)이 막연한 분기로 떨어지는 경우다.
# 모델은 가슴 통증에 정형외과를 먼저 내기도 한다(backlog 06 결과, backlog 26).
def rule_fixed(intake: Intake) -> bool:
    s = set(intake.symptoms)
    return "breath" in s or ("chest" in intake.body_parts and "pain" in s)


def department_for(intake: Intake, model: ModelPrediction | None) -> DepartmentPair:
    """규칙표가 명시적으로 정한 조합은 규칙표, 막연한 분기만 모델 앙상블 상위 2개다. 고정 조합(rule_fixed)은 분기와 관계없이 규칙표다."""
    pair, generic = rule_department(intake.body_parts, intake.symptoms)
    if model is None or not generic or rule_fixed(intake):
        return pair
    primary, alt = model.department_top2
    return DepartmentPair(primary=primary, alt=alt)


def triage(intake: Intake, model: ModelPrediction | None = None) -> TriageResult:
    """진료과 추천. `model`은 진료과 모델 예측(app/model.py)이고, 없으면 프론트와 같다."""
    missing: list = []
    if not intake.body_parts:
        missing.append("bodyParts")
    if not intake.symptoms:
        missing.append("symptoms")
    return TriageResult(
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
