# 예약·접수 도우미(POST /api/visit-helper)의 문장 템플릿. frontend/src/domain/templates.ts와 1:1.
# 실서비스에서는 LLM이 템플릿 슬롯을 채우고, 실패하면 이 기본 템플릿을 그대로 쓴다.
# 진단 표현(병명·골절 등)을 쓰지 않는다. 문구를 바꿀 때는 프론트와 함께 바꾼다.

from app.schemas import CallScript, DeskSheet, Faq, Intake, KoNative, Line, Tri
from app.templates.common import join_pron, join_terms, pick, tri
from app.vocab import BODY_PARTS, DEPARTMENTS, ONSETS, SYMPTOMS, Department, Lang, Term, josa, pron, term

# ---------------------------------------------------------------------------
# 공통 문장
# ---------------------------------------------------------------------------
PHRASES: dict[str, Term] = {
    "firstVisit": term("처음 왔습니다.", "This is my first visit.", "Tôi đến lần đầu.", "cheo-eum wat-seum-ni-da", "chơ-ưm oát-xưm-ni-đa"),
    "revisit": term(
        "전에 온 적이 있습니다.",
        "I have been here before.",
        "Tôi đã từng đến đây.",
        "jeo-ne on jeo-gi it-seum-ni-da",
        "chơ-nê ôn chơ-ghi ít-xưm-ni-đa",
    ),
    "workYes": term(
        "일하다가 생겼습니다.",
        "It happened while I was working.",
        "Bị trong lúc đang làm việc.",
        "il-ha-da-ga saeng-gyeot-seum-ni-da",
        "in-ha-đa-ga xeng-ghiớt-xưm-ni-đa",
    ),
    "workNo": term(
        "일과 관계없이 생겼습니다.",
        "It is not related to work.",
        "Không liên quan đến công việc.",
        "il-gwa gwan-gye-eop-si saeng-gyeot-seum-ni-da",
        "in-goa coan-ghiê-ớp-xi xeng-ghiớt-xưm-ni-đa",
    ),
    "korean": term(
        "한국어가 서툽니다. 천천히 말씀해 주세요.",
        "My Korean is limited. Please speak slowly.",
        "Tôi nói tiếng Hàn chưa giỏi. Xin hãy nói chậm.",
        "han-gu-geo-ga seo-tum-ni-da. cheon-cheon-hi mal-sseum-hae ju-se-yo",
        "han-cu-gơ-ga xơ-thum-ni-đa. chơn-chơn-hi man-xưm-he chu-xê-iô",
    ),
    "hello": term(
        "안녕하세요. 진료 예약을 하고 싶습니다.",
        "Hello. I would like to make an appointment.",
        "Xin chào. Tôi muốn đặt lịch khám.",
        "an-nyeong-ha-se-yo. jil-lyo ye-ya-geul ha-go sip-seum-ni-da",
        "an-niơng-ha-xê-iô. chin-liô iê-ia-gưn ha-cô xíp-xưm-ni-đa",
    ),
    "arc": term(
        "외국인등록증이 있습니다.",
        "I have an alien registration card (ARC).",
        "Tôi có thẻ đăng ký người nước ngoài (ARC).",
        "oe-gu-gin-deung-nok-jeung-i it-seum-ni-da",
        "uê-cu-ghin-tưng-nốc-chưng-i ít-xưm-ni-đa",
    ),
}


def phrase_line(t: Term, lang: Lang) -> Line:
    return Line(ko=t["ko"], native=pick(t, lang), pron=pron(t, lang))


def symptom_line(intake: Intake, lang: Lang) -> Line | None:
    if not intake.body_parts or not intake.symptoms:
        return None
    parts = [BODY_PARTS[p] for p in intake.body_parts]
    syms = [SYMPTOMS[s] for s in intake.symptoms]
    sym_ko = join_terms(syms, "ko")
    with_josa = josa(sym_ko, "이", "가")
    josa_pron = "i" if with_josa.endswith("이") else "ga"
    ko = f"{join_terms(parts, 'ko')}에 {with_josa} 있어서 진료받고 싶습니다."
    native = {
        "ko": ko,
        "vi": f"Tôi bị {join_terms(syms, 'vi').lower()} ở {join_terms(parts, 'vi').lower()}, muốn được khám.",
        "en": f"I have {join_terms(syms, 'en').lower()} in my {join_terms(parts, 'en').lower()} and would like to see a doctor.",
    }[lang]
    if lang == "ko":
        return Line(ko=ko, native=native, pron="")
    tail = "ít-xơ-xơ chin-liô-bát-cô xíp-xưm-ni-đa" if lang == "vi" else "it-seo-seo jil-lyo-bat-go sip-seum-ni-da"
    return Line(ko=ko, native=native, pron=f"{join_pron(parts, lang)}-e {join_pron(syms, lang)}-{josa_pron} {tail}")


def department_line(dept: Department, lang: Lang) -> Line:
    d = DEPARTMENTS[dept]
    ko = f"{d['ko']} 진료를 원합니다."
    return Line(
        ko=ko,
        native={"ko": ko, "vi": f"Tôi muốn khám {d['vi'].lower()}.", "en": f"I would like to see {d['en']}."}[lang],
        pron="" if lang == "ko" else f"{pron(d, lang)} {'chin-liô-rưn uôn-ham-ni-đa' if lang == 'vi' else 'jil-lyo-reul won-ham-ni-da'}",
    )


def onset_line(intake: Intake, lang: Lang) -> Line | None:
    if not intake.onset:
        return None
    o = ONSETS[intake.onset]
    ko = f"{o['ko']} 시작됐습니다."
    return Line(
        ko=ko,
        native={"ko": ko, "vi": f"Bắt đầu từ {o['vi'].lower()}.", "en": f"It started {o['en'].lower()}."}[lang],
        pron="" if lang == "ko" else f"{pron(o, lang)} {'xi-chác-toét-xưm-ni-đa' if lang == 'vi' else 'si-jak-dwaet-seum-ni-da'}",
    )


# ---------------------------------------------------------------------------
# FR-50 접수 창구 화면
# ---------------------------------------------------------------------------
DESK_DOCS = [
    tri("외국인등록증", "Alien registration card (ARC)", "Thẻ đăng ký người nước ngoài (ARC)"),
    tri("건강보험증(있는 경우)", "Health insurance card (if you have one)", "Thẻ bảo hiểm y tế (nếu có)"),
    tri("복용 중인 약(있는 경우)", "Medicines you are taking (if any)", "Thuốc đang dùng (nếu có)"),
]


def build_desk_sheet(intake: Intake, dept: Department, first_visit: bool, lang: Lang) -> DeskSheet:
    lines = [phrase_line(PHRASES["firstVisit"] if first_visit else PHRASES["revisit"], lang)]
    sym = symptom_line(intake, lang)
    if sym:
        lines.append(sym)
    lines.append(department_line(dept, lang))
    onset = onset_line(intake, lang)
    if onset:
        lines.append(onset)
    if intake.work_related == "yes":
        lines.append(phrase_line(PHRASES["workYes"], lang))
    if intake.work_related == "no":
        lines.append(phrase_line(PHRASES["workNo"], lang))
    # "한국어가 서툽니다"는 한국어 사용자에게는 넣지 않는다.
    if lang != "ko":
        lines.append(phrase_line(PHRASES["korean"], lang))
    work_related_ko = {"yes": "예(업무 중 발생)", "no": "아니요", "unknown": "모름"}[intake.work_related or "unknown"]
    return DeskSheet(
        lines=lines,
        first_visit=first_visit,
        work_related_ko=work_related_ko,
        docs_ko=[KoNative(ko=d["ko"], native=pick(d, lang)) for d in DESK_DOCS],
    )


# ---------------------------------------------------------------------------
# FR-51 전화 스크립트
# ---------------------------------------------------------------------------
def ans(ko: str, en: str, vi: str, roman: str, vi_pron: str, lang: Lang) -> Line:
    return Line(ko=ko, native={"ko": ko, "en": en, "vi": vi}[lang], pron={"ko": "", "en": roman, "vi": vi_pron}[lang])


def build_call_script(intake: Intake, dept: Department, lang: Lang) -> CallScript:
    lines = [phrase_line(PHRASES["hello"], lang), department_line(dept, lang)]
    sym = symptom_line(intake, lang)
    if sym:
        lines.append(sym)
    if lang != "ko":
        lines.append(phrase_line(PHRASES["korean"], lang))
    lines.append(phrase_line(PHRASES["arc"], lang))

    faq = [
        Faq(
            id="first",
            q=Tri(ko="처음 오셨어요?", en="Is this your first visit?", vi="Đây là lần đầu bạn đến phải không?"),
            answers=[
                ans("네, 처음입니다.", "Yes, it is my first time.", "Vâng, lần đầu.", "ne, cheo-eum-im-ni-da", "nê, chơ-ưm-im-ni-đa", lang),
                ans(
                    "아니요, 전에 간 적이 있습니다.",
                    "No, I have been before.",
                    "Không, tôi đã từng đến.",
                    "a-ni-yo, jeo-ne gan jeo-gi it-seum-ni-da",
                    "a-ni-iô, chơ-nê can chơ-ghi ít-xưm-ni-đa",
                    lang,
                ),
            ],
        ),
        Faq(
            id="when",
            q=Tri(ko="언제 오시겠어요?", en="When would you like to come?", vi="Bạn muốn đến khi nào?"),
            answers=[
                ans(
                    "오늘 가고 싶습니다.",
                    "Today, please.",
                    "Tôi muốn đến hôm nay.",
                    "o-neul ga-go sip-seum-ni-da",
                    "ô-nưn ca-cô xíp-xưm-ni-đa",
                    lang,
                ),
                ans(
                    "내일 오전에 가고 싶습니다.",
                    "Tomorrow morning, please.",
                    "Tôi muốn đến sáng mai.",
                    "nae-il o-jeo-ne ga-go sip-seum-ni-da",
                    "ne-in ô-chơ-nê ca-cô xíp-xưm-ni-đa",
                    lang,
                ),
                ans(
                    "내일 오후에 가고 싶습니다.",
                    "Tomorrow afternoon, please.",
                    "Tôi muốn đến chiều mai.",
                    "nae-il o-hu-e ga-go sip-seum-ni-da",
                    "ne-in ô-hu-ê ca-cô xíp-xưm-ni-đa",
                    lang,
                ),
                ans(
                    "가장 빠른 시간에 가고 싶습니다.",
                    "The earliest time available.",
                    "Thời gian sớm nhất có thể.",
                    "ga-jang ppa-reun si-ga-ne ga-go sip-seum-ni-da",
                    "ca-chang ba-rưn xi-ca-nê ca-cô xíp-xưm-ni-đa",
                    lang,
                ),
            ],
        ),
        Faq(
            id="where",
            q=Tri(ko="어디가 아프세요?", en="Where does it hurt?", vi="Bạn bị đau ở đâu?"),
            answers=[sym] if sym else [],
        ),
        Faq(
            id="insurance",
            q=Tri(ko="건강보험 있으세요?", en="Do you have health insurance?", vi="Bạn có bảo hiểm y tế không?"),
            answers=[
                ans("네, 있습니다.", "Yes, I do.", "Vâng, tôi có.", "ne, it-seum-ni-da", "nê, ít-xưm-ni-đa", lang),
                ans("없습니다.", "No, I do not.", "Tôi không có.", "eop-seum-ni-da", "ớp-xưm-ni-đa", lang),
                ans("잘 모르겠습니다.", "I am not sure.", "Tôi không rõ.", "jal mo-reu-get-seum-ni-da", "chan mô-rư-ghết-xưm-ni-đa", lang),
            ],
        ),
        Faq(
            id="help",
            q=Tri(ko="(못 알아들었을 때)", en="(When you did not understand)", vi="(Khi bạn không hiểu)"),
            answers=[
                ans(
                    "다시 한 번 말씀해 주세요.",
                    "Please say that again.",
                    "Xin nhắc lại một lần nữa.",
                    "da-si han beon mal-sseum-hae ju-se-yo",
                    "ta-xi han bơn man-xưm-he chu-xê-iô",
                    lang,
                ),
                ans(
                    "문자로 보내 주세요.",
                    "Please send it by text message.",
                    "Xin gửi tin nhắn cho tôi.",
                    "mun-ja-ro bo-nae ju-se-yo",
                    "mun-cha-rô pô-ne chu-xê-iô",
                    lang,
                ),
            ],
        ),
    ]
    return CallScript(lines=lines, faq=faq)
