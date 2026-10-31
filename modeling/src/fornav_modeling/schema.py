# 모델 입력 필드와 열거값 — 모델링 안의 단일 출처.
# 값은 backend/app/vocab.py, backend/app/schemas.py의 Intake를 그대로 복사한다. 다국어 표기(Term)는 모델에 필요 없어 옮기지 않는다.
# 백엔드가 값을 바꾸면 tests/test_schema.py가 깨진다. 그때 백엔드가 아니라 이 파일을 맞춘다.
# 순서도 백엔드와 같게 둔다. 아래 튜플이 모델의 라벨·원-핫 순서가 된다.

from typing import Literal, NotRequired, TypedDict, get_args

Lang = Literal["en", "vi", "ko", "ne", "ru", "mn", "my", "si", "ar", "uz", "ja", "zh-CN", "zh-TW", "kk", "km", "ky", "th", "fr", "tl", "id"]

BodyPart = Literal["head", "eye", "ent", "teeth", "chest", "abdomen", "back", "arm", "hand", "leg", "foot", "skin", "whole"]

Symptom = Literal[
    "pain",
    "swelling",
    "cut",
    "bleeding",
    "burn",
    "numb",
    "cantmove",
    "fever",
    "cough",
    "dizzy",
    "rash",
    "nausea",
    "breath",
    "chemical",
    "foreign",
]

Department = Literal["ortho", "surgery", "internal", "ophth", "ent", "derm", "dental", "neuro", "family", "occ"]

# Intake 필드 타입에 필요한 나머지 열거값
Onset = Literal["today", "yesterday", "days", "week"]
Industry = Literal["shipbuilding", "autoparts", "chemical", "construction", "other"]
WorkType = Literal["welding", "lifting", "machine", "grinding", "painting", "assembly"]
District = Literal["jung", "nam", "dong", "buk", "ulju"]
YesNoUnknown = Literal["yes", "no", "unknown"]

LANGS: tuple[Lang, ...] = get_args(Lang)
BODY_PARTS: tuple[BodyPart, ...] = get_args(BodyPart)
SYMPTOMS: tuple[Symptom, ...] = get_args(Symptom)
DEPARTMENTS: tuple[Department, ...] = get_args(Department)
ONSETS: tuple[Onset, ...] = get_args(Onset)


class Intake(TypedDict):
    """백엔드 Intake의 Python 필드 이름(snake_case) 그대로. 기본값이 있는 필드는 빠져도 된다."""

    id: str
    language: Lang
    body_parts: NotRequired[list[BodyPart]]
    symptoms: NotRequired[list[Symptom]]
    free_text: NotRequired[str]
    onset: NotRequired[Onset | None]
    work_related: NotRequired[YesNoUnknown | None]
    work_type: NotRequired[WorkType | None]
    industry: NotRequired[Industry | None]
    district: NotRequired[District | None]
    created_at: str
    injury: NotRequired[bool | None]
