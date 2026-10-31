# 고정 어휘: 신체 부위·증상·진료과·업종·구군 등. frontend/src/domain/vocab.ts와 1:1.
# 여기에는 한국어(의료진·센터 표시)와 발음 표기(전화 스크립트용)를 두고, 근로자 모국어 표기는 vocab.PACKS 언어 묶음에서 합친다.
# 한국어를 고른 근로자는 한국어 표기를 그대로 보고, 발음 표기는 쓰지 않는다.

import json
from pathlib import Path
from typing import Any, Literal, TypedDict, get_args

# 순서는 프론트 LANGS와 같다(동기화 테스트 기대값의 순서).
Lang = Literal["en", "vi", "ko", "ne", "ru", "mn", "my", "si", "ar", "uz", "ja", "zh-CN", "zh-TW", "kk", "km", "ky", "th", "fr", "tl", "id"]
LANGS: list[Lang] = list(get_args(Lang))
# 한국어를 뺀 근로자 모국어. 언어마다 언어 묶음(PACKS)이 있다
NATIVE_LANGS: list[Lang] = [lang for lang in LANGS if lang != "ko"]


# 근로자 모국어 묶음(한국어 제외). 언어마다 어휘 표기(terms)·문장 틀(templates)을 가진다.
# 구조는 frontend/src/domain/lang/types.ts의 LangPack이다. lang/packs.json은 frontend/scripts/dump-lang-packs.ts로 만들고 손으로 고치지 않는다.
# 이 파일은 modeling 테스트가 파일로 직접 읽으므로 표준 라이브러리만 쓴다.
type LangPack = dict[str, Any]
PACKS: dict[str, LangPack] = json.loads((Path(__file__).parent / "lang" / "packs.json").read_text(encoding="utf-8"))


class KoTerm(TypedDict):
    ko: str
    # 로마자 발음. 베트남어를 뺀 모든 외국어 사용자에게 보인다
    roman: str
    # 베트남어 사용자용 발음 표기
    viPron: str


# 한국어·발음 표기에 모든 근로자 언어의 표기를 더한 어휘 항목(키: ko, roman, viPron과 Lang 값)
type Term = dict[str, str]


def ko_term(ko: str, roman: str, vi_pron: str) -> KoTerm:
    return {"ko": ko, "roman": roman, "viPron": vi_pron}


def with_native[K: str](base: dict[K, KoTerm], key: str) -> dict[K, Term]:
    """한국어 표에 각 언어 묶음(terms[key])의 표기를 합친다. 키 순서는 한국어 표를 따른다."""
    return {k: {**t, **{lang: PACKS[lang]["terms"][key][k] for lang in NATIVE_LANGS}} for k, t in base.items()}


def pron(t: Term, lang: Lang) -> str:
    """근로자 언어에 맞는 발음 표기. 한국어 사용자는 발음 표기가 필요 없어 빈 문자열을 돌려준다."""
    if lang == "ko":
        return ""
    return t["viPron"] if lang == "vi" else t["roman"]


BodyPart = Literal["head", "eye", "ent", "teeth", "chest", "abdomen", "back", "arm", "hand", "leg", "foot", "skin", "whole"]
_BODY_PARTS_KO: dict[BodyPart, KoTerm] = {
    "head": ko_term("머리", "meo-ri", "mơ-ri"),
    "eye": ko_term("눈", "nun", "nun"),
    "ent": ko_term("귀·코·목", "gwi, ko, mok", "guy, cô, mốc"),
    "teeth": ko_term("이·잇몸", "i, in-mom", "i, in-môm"),
    "chest": ko_term("가슴", "ga-seum", "ca-xưm"),
    "abdomen": ko_term("배", "bae", "be"),
    "back": ko_term("허리·등", "heo-ri, deung", "hơ-ri, tưng"),
    "arm": ko_term("팔·어깨", "pal, eo-kkae", "pan, ơ-ke"),
    "hand": ko_term("손·손가락", "son, son-ga-rak", "xôn, xôn-ca-rác"),
    "leg": ko_term("다리·무릎", "da-ri, mu-reup", "ta-ri, mu-rứp"),
    "foot": ko_term("발·발목", "bal, bal-mok", "pan, pan-mốc"),
    "skin": ko_term("피부", "pi-bu", "pi-bu"),
    "whole": ko_term("온몸", "on-mom", "ôn-môm"),
}
BODY_PARTS = with_native(_BODY_PARTS_KO, "bodyParts")

# 증상 한국어 표기는 "~이/가 있습니다" 문장에 들어가도록 명사형으로 둔다.
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
_SYMPTOMS_KO: dict[Symptom, KoTerm] = {
    "pain": ko_term("통증", "tong-jeung", "thông-chưng"),
    "swelling": ko_term("부기", "bu-gi", "bu-ghi"),
    "cut": ko_term("베인 상처", "be-in sang-cheo", "bê-in xang-chơ"),
    "bleeding": ko_term("출혈", "chul-hyeol", "chun-hiơn"),
    "burn": ko_term("화상", "hwa-sang", "hoa-xang"),
    "numb": ko_term("저림", "jeo-rim", "chơ-rim"),
    "cantmove": ko_term("움직이기 어려움", "um-ji-gi-gi eo-ryeo-um", "um-chi-ghi-ghi ơ-riơ-um"),
    "fever": ko_term("열", "yeol", "iơn"),
    "cough": ko_term("기침", "gi-chim", "ki-chim"),
    "dizzy": ko_term("어지러움", "eo-ji-reo-um", "ơ-chi-rơ-um"),
    "rash": ko_term("발진·가려움", "bal-jin, ga-ryeo-um", "pan-chin, ca-riơ-um"),
    "nausea": ko_term("구토·메스꺼움", "gu-to, me-seu-kkeo-um", "cu-thô, mê-xư-cơ-um"),
    "breath": ko_term("호흡 곤란", "ho-heup gol-lan", "hô-hứp côn-lan"),
    "chemical": ko_term("화학물질 노출", "hwa-hak-mul-jil no-chul", "hoa-hác-mun-chin nô-chun"),
    "foreign": ko_term("눈의 이물감", "nu-ne i-mul-gam", "nu-nê i-mun-cam"),
}
SYMPTOMS = with_native(_SYMPTOMS_KO, "symptoms")

Department = Literal["ortho", "surgery", "internal", "ophth", "ent", "derm", "dental", "neuro", "family", "occ"]
_DEPARTMENTS_KO: dict[Department, KoTerm] = {
    "ortho": ko_term("정형외과", "jeong-hyeong-oe-gwa", "chơng-hiơng-uê-qua"),
    "surgery": ko_term("외과", "oe-gwa", "uê-qua"),
    "internal": ko_term("내과", "nae-gwa", "ne-qua"),
    "ophth": ko_term("안과", "an-gwa", "an-qua"),
    "ent": ko_term("이비인후과", "i-bi-in-hu-gwa", "i-bi-in-hu-qua"),
    "derm": ko_term("피부과", "pi-bu-gwa", "pi-bu-qua"),
    "dental": ko_term("치과", "chi-gwa", "chi-qua"),
    "neuro": ko_term("신경과", "sin-gyeong-gwa", "xin-ghiơng-qua"),
    "family": ko_term("가정의학과", "ga-jeong-ui-hak-gwa", "ca-chơng-ưi-hác-qua"),
    "occ": ko_term("직업환경의학과", "ji-geop-hwan-gyeong-ui-hak-gwa", "chi-gớp-hoan-ghiơng-ưi-hác-qua"),
}
DEPARTMENTS = with_native(_DEPARTMENTS_KO, "departments")

Onset = Literal["today", "yesterday", "days", "week"]
_ONSETS_KO: dict[Onset, KoTerm] = {
    "today": ko_term("오늘", "o-neul", "ô-nưn"),
    "yesterday": ko_term("어제", "eo-je", "ơ-chê"),
    "days": ko_term("2~3일 전", "i-sam-il jeon", "i-xam-in chơn"),
    "week": ko_term("일주일 이상 전", "il-ju-il i-sang jeon", "in-chu-in i-xang chơn"),
}
ONSETS = with_native(_ONSETS_KO, "onsets")

Industry = Literal["shipbuilding", "autoparts", "chemical", "construction", "other"]
_INDUSTRIES_KO: dict[Industry, KoTerm] = {
    "shipbuilding": ko_term("조선", "jo-seon", "chô-xơn"),
    "autoparts": ko_term("자동차 부품", "ja-dong-cha bu-pum", "cha-đông-cha bu-pum"),
    "chemical": ko_term("화학", "hwa-hak", "hoa-hác"),
    "construction": ko_term("건설", "geon-seol", "cơn-xơn"),
    "other": ko_term("기타", "gi-ta", "ki-tha"),
}
INDUSTRIES = with_native(_INDUSTRIES_KO, "industries")

WorkType = Literal["welding", "lifting", "machine", "grinding", "painting", "assembly"]
_WORK_TYPES_KO: dict[WorkType, KoTerm] = {
    "welding": ko_term("용접", "yong-jeop", "iông-chớp"),
    "lifting": ko_term("중량물 운반", "jung-nyang-mul un-ban", "chung-niang-mun un-ban"),
    "machine": ko_term("기계(프레스 등) 작업", "gi-gye jak-eop", "ki-ghiê chác-ớp"),
    "grinding": ko_term("절단·연마", "jeol-dan, yeon-ma", "chơn-tan, iơn-ma"),
    "painting": ko_term("도장·화학물질 취급", "do-jang", "tô-chang"),
    "assembly": ko_term("조립", "jo-rip", "chô-ríp"),
}
WORK_TYPES = with_native(_WORK_TYPES_KO, "workTypes")

District = Literal["jung", "nam", "dong", "buk", "ulju"]
_DISTRICTS_KO: dict[District, KoTerm] = {
    "jung": ko_term("중구", "jung-gu", "chung-cu"),
    "nam": ko_term("남구", "nam-gu", "nam-cu"),
    "dong": ko_term("동구", "dong-gu", "tông-cu"),
    "buk": ko_term("북구", "buk-gu", "búc-cu"),
    "ulju": ko_term("울주군", "ul-ju-gun", "un-chu-cun"),
}
DISTRICTS = with_native(_DISTRICTS_KO, "districts")

YesNoUnknown = Literal["yes", "no", "unknown"]

LANGUAGE_NAMES_KO: dict[Lang, str] = {
    "en": "영어",
    "vi": "베트남어",
    "ko": "한국어",
    "ne": "네팔어",
    "ru": "러시아어",
    "mn": "몽골어",
    "my": "미얀마어",
    "si": "싱할라어",
    "ar": "아랍어",
    "uz": "우즈베크어",
    "ja": "일본어",
    "zh-CN": "중국어(간체)",
    "zh-TW": "중국어(번체)",
    "kk": "카자흐어",
    "km": "크메르어",
    "ky": "키르기스어",
    "th": "태국어",
    "fr": "프랑스어",
    "tl": "필리핀어",
    "id": "인도네시아어",
}


def josa(word: str, with_batchim: str, without_batchim: str) -> str:
    """한국어 단어 끝 받침 여부에 따라 조사를 고른다(이/가, 은/는 등)."""
    last = word.strip()[-1:]
    # 프론트는 빈 문자열이면 NaN 비교가 모두 거짓이 되어 받침 있는 쪽을 고른다. 같은 결과를 낸다.
    if not last:
        return word + with_batchim
    code = ord(last) - 0xAC00
    if code < 0 or code > 11171:
        return word + without_batchim
    return word + (without_batchim if code % 28 == 0 else with_batchim)
