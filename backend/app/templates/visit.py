# 예약·접수 도우미(POST /api/visit-helper)의 문장 템플릿. frontend/src/domain/templates.ts와 1:1.
# 실서비스에서는 LLM이 템플릿 슬롯을 채우고, 실패하면 이 기본 템플릿을 그대로 쓴다.
# 진단 표현(병명·골절 등)을 쓰지 않는다. 문구를 바꿀 때는 프론트와 함께 바꾼다.
# 한국어 문장과 발음 표기는 여기에, 근로자 모국어 문장은 vocab.PACKS 언어 묶음의 templates에 있다.

from app.schemas import CallScript, DeskSheet, Faq, Intake, KoNative, Line
from app.templates.common import fill, join_pron, join_terms, tpl
from app.vocab import BODY_PARTS, DEPARTMENTS, ONSETS, SYMPTOMS, Department, KoTerm, Lang, josa, ko_term, pron

# ---------------------------------------------------------------------------
# 공통 문장
# ---------------------------------------------------------------------------
PHRASES: dict[str, KoTerm] = {
    "firstVisit": ko_term("처음 왔습니다.", "cheo-eum wat-seum-ni-da", "chơ-ưm oát-xưm-ni-đa"),
    "revisit": ko_term("전에 온 적이 있습니다.", "jeo-ne on jeo-gi it-seum-ni-da", "chơ-nê ôn chơ-ghi ít-xưm-ni-đa"),
    "workYes": ko_term("일하다가 생겼습니다.", "il-ha-da-ga saeng-gyeot-seum-ni-da", "in-ha-đa-ga xeng-ghiớt-xưm-ni-đa"),
    "workNo": ko_term(
        "일과 관계없이 생겼습니다.", "il-gwa gwan-gye-eop-si saeng-gyeot-seum-ni-da", "in-goa coan-ghiê-ớp-xi xeng-ghiớt-xưm-ni-đa"
    ),
    "korean": ko_term(
        "한국어가 서툽니다. 천천히 말씀해 주세요.",
        "han-gu-geo-ga seo-tum-ni-da. cheon-cheon-hi mal-sseum-hae ju-se-yo",
        "han-cu-gơ-ga xơ-thum-ni-đa. chơn-chơn-hi man-xưm-he chu-xê-iô",
    ),
    "hello": ko_term(
        "안녕하세요. 진료 예약을 하고 싶습니다.",
        "an-nyeong-ha-se-yo. jil-lyo ye-ya-geul ha-go sip-seum-ni-da",
        "an-niơng-ha-xê-iô. chin-liô iê-ia-gưn ha-cô xíp-xưm-ni-đa",
    ),
    "arc": ko_term("외국인등록증이 있습니다.", "oe-gu-gin-deung-nok-jeung-i it-seum-ni-da", "uê-cu-ghin-tưng-nốc-chưng-i ít-xưm-ni-đa"),
}


def ko_pron(p: KoTerm, lang: Lang) -> str:
    return "" if lang == "ko" else p["viPron"] if lang == "vi" else p["roman"]


def phrase_line(key: str, lang: Lang) -> Line:
    p = PHRASES[key]
    return Line(ko=p["ko"], native=p["ko"] if lang == "ko" else tpl(lang)["phrases"][key], pron=ko_pron(p, lang))


def symptom_line(intake: Intake, lang: Lang) -> Line | None:
    if not intake.body_parts or not intake.symptoms:
        return None
    parts = [BODY_PARTS[p] for p in intake.body_parts]
    syms = [SYMPTOMS[s] for s in intake.symptoms]
    sym_ko = join_terms(syms, "ko")
    with_josa = josa(sym_ko, "이", "가")
    josa_pron = "i" if with_josa.endswith("이") else "ga"
    ko = f"{join_terms(parts, 'ko')}에 {with_josa} 있어서 진료받고 싶습니다."
    if lang == "ko":
        return Line(ko=ko, native=ko, pron="")
    native = fill(tpl(lang)["symptom"], {"syms": join_terms(syms, lang), "parts": join_terms(parts, lang)})
    tail = "ít-xơ-xơ chin-liô-bát-cô xíp-xưm-ni-đa" if lang == "vi" else "it-seo-seo jil-lyo-bat-go sip-seum-ni-da"
    return Line(ko=ko, native=native, pron=f"{join_pron(parts, lang)}-e {join_pron(syms, lang)}-{josa_pron} {tail}")


def department_line(dept: Department, lang: Lang) -> Line:
    d = DEPARTMENTS[dept]
    ko = f"{d['ko']} 진료를 원합니다."
    return Line(
        ko=ko,
        native=ko if lang == "ko" else fill(tpl(lang)["department"], {"dept": d[lang]}),
        pron="" if lang == "ko" else f"{pron(d, lang)} {'chin-liô-rưn uôn-ham-ni-đa' if lang == 'vi' else 'jil-lyo-reul won-ham-ni-da'}",
    )


def onset_line(intake: Intake, lang: Lang) -> Line | None:
    if not intake.onset:
        return None
    o = ONSETS[intake.onset]
    ko = f"{o['ko']} 시작됐습니다."
    return Line(
        ko=ko,
        native=ko if lang == "ko" else fill(tpl(lang)["onset"], {"onset": o[lang]}),
        pron="" if lang == "ko" else f"{pron(o, lang)} {'xi-chác-toét-xưm-ni-đa' if lang == 'vi' else 'si-jak-dwaet-seum-ni-da'}",
    )


# ---------------------------------------------------------------------------
# FR-50 접수 창구 화면
# ---------------------------------------------------------------------------
DESK_DOCS_KO = {"arc": "외국인등록증", "insurance": "건강보험증(있는 경우)", "meds": "복용 중인 약(있는 경우)"}


def build_desk_sheet(intake: Intake, dept: Department, first_visit: bool, lang: Lang) -> DeskSheet:
    lines = [phrase_line("firstVisit" if first_visit else "revisit", lang)]
    sym = symptom_line(intake, lang)
    if sym:
        lines.append(sym)
    lines.append(department_line(dept, lang))
    onset = onset_line(intake, lang)
    if onset:
        lines.append(onset)
    if intake.work_related == "yes":
        lines.append(phrase_line("workYes", lang))
    if intake.work_related == "no":
        lines.append(phrase_line("workNo", lang))
    # "한국어가 서툽니다"는 한국어 사용자에게는 넣지 않는다.
    if lang != "ko":
        lines.append(phrase_line("korean", lang))
    work_related_ko = {"yes": "예(업무 중 발생)", "no": "아니요", "unknown": "모름"}[intake.work_related or "unknown"]
    return DeskSheet(
        lines=lines,
        first_visit=first_visit,
        work_related_ko=work_related_ko,
        docs_ko=[KoNative(ko=ko, native=ko if lang == "ko" else tpl(lang)["docs"][k]) for k, ko in DESK_DOCS_KO.items()],
    )


# ---------------------------------------------------------------------------
# FR-51 전화 스크립트
# ---------------------------------------------------------------------------
FAQ_KO = {
    "first": "처음 오셨어요?",
    "when": "언제 오시겠어요?",
    "where": "어디가 아프세요?",
    "insurance": "건강보험 있으세요?",
    "help": "(못 알아들었을 때)",
}

ANSWERS: dict[str, KoTerm] = {
    "firstYes": ko_term("네, 처음입니다.", "ne, cheo-eum-im-ni-da", "nê, chơ-ưm-im-ni-đa"),
    "firstNo": ko_term(
        "아니요, 전에 간 적이 있습니다.", "a-ni-yo, jeo-ne gan jeo-gi it-seum-ni-da", "a-ni-iô, chơ-nê can chơ-ghi ít-xưm-ni-đa"
    ),
    "whenToday": ko_term("오늘 가고 싶습니다.", "o-neul ga-go sip-seum-ni-da", "ô-nưn ca-cô xíp-xưm-ni-đa"),
    "whenTomorrowAm": ko_term("내일 오전에 가고 싶습니다.", "nae-il o-jeo-ne ga-go sip-seum-ni-da", "ne-in ô-chơ-nê ca-cô xíp-xưm-ni-đa"),
    "whenTomorrowPm": ko_term("내일 오후에 가고 싶습니다.", "nae-il o-hu-e ga-go sip-seum-ni-da", "ne-in ô-hu-ê ca-cô xíp-xưm-ni-đa"),
    "whenEarliest": ko_term(
        "가장 빠른 시간에 가고 싶습니다.", "ga-jang ppa-reun si-ga-ne ga-go sip-seum-ni-da", "ca-chang ba-rưn xi-ca-nê ca-cô xíp-xưm-ni-đa"
    ),
    "insuranceYes": ko_term("네, 있습니다.", "ne, it-seum-ni-da", "nê, ít-xưm-ni-đa"),
    "insuranceNo": ko_term("없습니다.", "eop-seum-ni-da", "ớp-xưm-ni-đa"),
    "insuranceUnsure": ko_term("잘 모르겠습니다.", "jal mo-reu-get-seum-ni-da", "chan mô-rư-ghết-xưm-ni-đa"),
    "helpRepeat": ko_term("다시 한 번 말씀해 주세요.", "da-si han beon mal-sseum-hae ju-se-yo", "ta-xi han bơn man-xưm-he chu-xê-iô"),
    "helpText": ko_term("문자로 보내 주세요.", "mun-ja-ro bo-nae ju-se-yo", "mun-cha-rô pô-ne chu-xê-iô"),
}


def ans(key: str, lang: Lang) -> Line:
    a = ANSWERS[key]
    return Line(ko=a["ko"], native=a["ko"] if lang == "ko" else tpl(lang)["answers"][key], pron=ko_pron(a, lang))


def faq_q(faq_id: str, lang: Lang) -> KoNative:
    ko = FAQ_KO[faq_id]
    return KoNative(ko=ko, native=ko if lang == "ko" else tpl(lang)["faq"][faq_id])


def build_call_script(intake: Intake, dept: Department, lang: Lang) -> CallScript:
    lines = [phrase_line("hello", lang), department_line(dept, lang)]
    sym = symptom_line(intake, lang)
    if sym:
        lines.append(sym)
    if lang != "ko":
        lines.append(phrase_line("korean", lang))
    lines.append(phrase_line("arc", lang))

    faq = [
        Faq(id="first", q=faq_q("first", lang), answers=[ans("firstYes", lang), ans("firstNo", lang)]),
        Faq(
            id="when",
            q=faq_q("when", lang),
            answers=[ans("whenToday", lang), ans("whenTomorrowAm", lang), ans("whenTomorrowPm", lang), ans("whenEarliest", lang)],
        ),
        Faq(id="where", q=faq_q("where", lang), answers=[sym] if sym else []),
        Faq(
            id="insurance",
            q=faq_q("insurance", lang),
            answers=[ans("insuranceYes", lang), ans("insuranceNo", lang), ans("insuranceUnsure", lang)],
        ),
        Faq(id="help", q=faq_q("help", lang), answers=[ans("helpRepeat", lang), ans("helpText", lang)]),
    ]
    return CallScript(lines=lines, faq=faq)
