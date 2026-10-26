# 고정 어휘: 신체 부위·증상·진료과·업종·구군 등. frontend/src/domain/vocab.ts와 1:1.
# 모든 항목은 한국어(의료진·센터 표시), 영어·베트남어(근로자 표시), 발음 표기(전화 스크립트용)를 함께 가진다.
# 한국어를 고른 근로자는 한국어 표기를 그대로 보고, 발음 표기는 쓰지 않는다.

from typing import Literal, TypedDict

Lang = Literal["en", "vi", "ko"]
LANGS: list[Lang] = ["en", "vi", "ko"]


class Term(TypedDict):
    ko: str
    en: str
    vi: str
    # 영어 사용자용 로마자 발음
    roman: str
    # 베트남어 사용자용 발음 표기
    viPron: str


def term(ko: str, en: str, vi: str, roman: str, vi_pron: str) -> Term:
    return {"ko": ko, "en": en, "vi": vi, "roman": roman, "viPron": vi_pron}


def pron(t: Term, lang: Lang) -> str:
    """근로자 언어에 맞는 발음 표기. 한국어 사용자는 발음 표기가 필요 없어 빈 문자열을 돌려준다."""
    if lang == "ko":
        return ""
    return t["viPron"] if lang == "vi" else t["roman"]


BodyPart = Literal["head", "eye", "ent", "teeth", "chest", "abdomen", "back", "arm", "hand", "leg", "foot", "skin", "whole"]
BODY_PARTS: dict[BodyPart, Term] = {
    "head": term("머리", "Head", "Đầu", "meo-ri", "mơ-ri"),
    "eye": term("눈", "Eye", "Mắt", "nun", "nun"),
    "ent": term("귀·코·목", "Ear, nose, throat", "Tai, mũi, họng", "gwi, ko, mok", "guy, cô, mốc"),
    "teeth": term("이·잇몸", "Teeth, gums", "Răng, lợi", "i, in-mom", "i, in-môm"),
    "chest": term("가슴", "Chest", "Ngực", "ga-seum", "ca-xưm"),
    "abdomen": term("배", "Stomach", "Bụng", "bae", "be"),
    "back": term("허리·등", "Back, waist", "Lưng, eo", "heo-ri, deung", "hơ-ri, tưng"),
    "arm": term("팔·어깨", "Arm, shoulder", "Cánh tay, vai", "pal, eo-kkae", "pan, ơ-ke"),
    "hand": term("손·손가락", "Hand, finger", "Bàn tay, ngón tay", "son, son-ga-rak", "xôn, xôn-ca-rác"),
    "leg": term("다리·무릎", "Leg, knee", "Chân, đầu gối", "da-ri, mu-reup", "ta-ri, mu-rứp"),
    "foot": term("발·발목", "Foot, ankle", "Bàn chân, cổ chân", "bal, bal-mok", "pan, pan-mốc"),
    "skin": term("피부", "Skin", "Da", "pi-bu", "pi-bu"),
    "whole": term("온몸", "Whole body", "Toàn thân", "on-mom", "ôn-môm"),
}

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
SYMPTOMS: dict[Symptom, Term] = {
    "pain": term("통증", "Pain", "Đau", "tong-jeung", "thông-chưng"),
    "swelling": term("부기", "Swelling", "Sưng", "bu-gi", "bu-ghi"),
    "cut": term("베인 상처", "Cut, wound", "Vết cắt, vết thương", "be-in sang-cheo", "bê-in xang-chơ"),
    "bleeding": term("출혈", "Bleeding", "Chảy máu", "chul-hyeol", "chun-hiơn"),
    "burn": term("화상", "Burn", "Bỏng", "hwa-sang", "hoa-xang"),
    "numb": term("저림", "Numbness", "Tê", "jeo-rim", "chơ-rim"),
    "cantmove": term("움직이기 어려움", "Hard to move", "Khó cử động", "um-ji-gi-gi eo-ryeo-um", "um-chi-ghi-ghi ơ-riơ-um"),
    "fever": term("열", "Fever", "Sốt", "yeol", "iơn"),
    "cough": term("기침", "Cough", "Ho", "gi-chim", "ki-chim"),
    "dizzy": term("어지러움", "Dizziness", "Chóng mặt", "eo-ji-reo-um", "ơ-chi-rơ-um"),
    "rash": term("발진·가려움", "Rash, itching", "Phát ban, ngứa", "bal-jin, ga-ryeo-um", "pan-chin, ca-riơ-um"),
    "nausea": term("구토·메스꺼움", "Nausea, vomiting", "Buồn nôn, nôn", "gu-to, me-seu-kkeo-um", "cu-thô, mê-xư-cơ-um"),
    "breath": term("호흡 곤란", "Hard to breathe", "Khó thở", "ho-heup gol-lan", "hô-hứp côn-lan"),
    "chemical": term("화학물질 노출", "Chemical exposure", "Tiếp xúc hóa chất", "hwa-hak-mul-jil no-chul", "hoa-hác-mun-chin nô-chun"),
    "foreign": term("눈의 이물감", "Something in the eye", "Dị vật trong mắt", "nu-ne i-mul-gam", "nu-nê i-mun-cam"),
}

Department = Literal["ortho", "surgery", "internal", "ophth", "ent", "derm", "dental", "neuro", "family", "occ"]
DEPARTMENTS: dict[Department, Term] = {
    "ortho": term("정형외과", "Orthopaedics", "Chỉnh hình", "jeong-hyeong-oe-gwa", "chơng-hiơng-uê-qua"),
    "surgery": term("외과", "General surgery", "Ngoại khoa", "oe-gwa", "uê-qua"),
    "internal": term("내과", "Internal medicine", "Nội khoa", "nae-gwa", "ne-qua"),
    "ophth": term("안과", "Eye clinic", "Nhãn khoa", "an-gwa", "an-qua"),
    "ent": term("이비인후과", "ENT (ear, nose, throat)", "Tai mũi họng", "i-bi-in-hu-gwa", "i-bi-in-hu-qua"),
    "derm": term("피부과", "Dermatology (skin)", "Da liễu", "pi-bu-gwa", "pi-bu-qua"),
    "dental": term("치과", "Dentist", "Nha khoa", "chi-gwa", "chi-qua"),
    "neuro": term("신경과", "Neurology", "Thần kinh", "sin-gyeong-gwa", "xin-ghiơng-qua"),
    "family": term("가정의학과", "Family medicine", "Y học gia đình", "ga-jeong-ui-hak-gwa", "ca-chơng-ưi-hác-qua"),
    "occ": term(
        "직업환경의학과", "Occupational medicine", "Y học nghề nghiệp", "ji-geop-hwan-gyeong-ui-hak-gwa", "chi-gớp-hoan-ghiơng-ưi-hác-qua"
    ),
}

Onset = Literal["today", "yesterday", "days", "week"]
ONSETS: dict[Onset, Term] = {
    "today": term("오늘", "Today", "Hôm nay", "o-neul", "ô-nưn"),
    "yesterday": term("어제", "Yesterday", "Hôm qua", "eo-je", "ơ-chê"),
    "days": term("2~3일 전", "2–3 days ago", "2–3 ngày trước", "i-sam-il jeon", "i-xam-in chơn"),
    "week": term("일주일 이상 전", "Over a week ago", "Hơn một tuần trước", "il-ju-il i-sang jeon", "in-chu-in i-xang chơn"),
}

Industry = Literal["shipbuilding", "autoparts", "chemical", "construction", "other"]
INDUSTRIES: dict[Industry, Term] = {
    "shipbuilding": term("조선", "Shipbuilding", "Đóng tàu", "jo-seon", "chô-xơn"),
    "autoparts": term("자동차 부품", "Auto parts", "Phụ tùng ô tô", "ja-dong-cha bu-pum", "cha-đông-cha bu-pum"),
    "chemical": term("화학", "Chemical", "Hóa chất", "hwa-hak", "hoa-hác"),
    "construction": term("건설", "Construction", "Xây dựng", "geon-seol", "cơn-xơn"),
    "other": term("기타", "Other", "Khác", "gi-ta", "ki-tha"),
}

WorkType = Literal["welding", "lifting", "machine", "grinding", "painting", "assembly"]
WORK_TYPES: dict[WorkType, Term] = {
    "welding": term("용접", "Welding", "Hàn", "yong-jeop", "iông-chớp"),
    "lifting": term("중량물 운반", "Lifting, carrying", "Nâng, khuân vác", "jung-nyang-mul un-ban", "chung-niang-mun un-ban"),
    "machine": term("기계(프레스 등) 작업", "Machine work (press etc.)", "Vận hành máy (máy dập...)", "gi-gye jak-eop", "ki-ghiê chác-ớp"),
    "grinding": term("절단·연마", "Cutting, grinding", "Cắt, mài", "jeol-dan, yeon-ma", "chơn-tan, iơn-ma"),
    "painting": term("도장·화학물질 취급", "Painting, chemical handling", "Sơn, xử lý hóa chất", "do-jang", "tô-chang"),
    "assembly": term("조립", "Assembly", "Lắp ráp", "jo-rip", "chô-ríp"),
}

District = Literal["jung", "nam", "dong", "buk", "ulju"]
DISTRICTS: dict[District, Term] = {
    "jung": term("중구", "Jung-gu", "Jung-gu", "jung-gu", "chung-cu"),
    "nam": term("남구", "Nam-gu", "Nam-gu", "nam-gu", "nam-cu"),
    "dong": term("동구", "Dong-gu", "Dong-gu", "dong-gu", "tông-cu"),
    "buk": term("북구", "Buk-gu", "Buk-gu", "buk-gu", "búc-cu"),
    "ulju": term("울주군", "Ulju-gun", "Ulju-gun", "ul-ju-gun", "un-chu-cun"),
}

YesNoUnknown = Literal["yes", "no", "unknown"]

LANGUAGE_NAMES_KO: dict[Lang, str] = {"en": "영어", "vi": "베트남어", "ko": "한국어"}


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
