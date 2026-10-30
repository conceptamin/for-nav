# LLM이 쓴 한국어 문장을 내보내기 전 검사(README "진단 표현 금지"의 구체화).
# 하나라도 걸리면 부르는 쪽은 템플릿 원문을 쓴다. 번역(backlog 05)에도 같은 검사를 쓴다.
# 금지어를 더할 때는 tests/test_template_slots.py에 걸리는 예를 함께 더한다.

from typing import Literal

MAX_LEN = 60

# 병명·진단명. 증상 어휘(vocab.SYMPTOMS의 ko: 통증, 부기, 출혈, 화상 등)는 넣지 않는다.
DIAGNOSES = [
    "골절",
    "부러",
    "금이 갔",
    "염좌",
    "탈구",
    "인대",
    "파열",
    "디스크",
    "감염",
    "염증",
    "관절염",
    "장염",
    "위염",
    "폐렴",
    "독감",
    "코로나",
    "협심증",
    "심근경색",
    "심장마비",
    "뇌졸중",
    "뇌출혈",
    "맹장",
    "충수염",
    "알레르기",
    "천식",
    "당뇨",
    "고혈압",
    "중독",
    "질환",
    "증후군",
    "진단",
]
# 원인·결과 추측 표현.
GUESSES = ["로 보임", "로 보입니다", "로 보인다", "것 같", "듯", "가능성", "의심", "추정", "때문인"]
# 치료·행동 권고.
ADVICE = ["치료", "처방", "수술", "입원", "복용하", "하세요", "해야", "권장", "권고", "필요합니다"]
FORBIDDEN = [*DIAGNOSES, *GUESSES, *ADVICE]

GuardFailure = Literal["empty", "multiline", "too_long", "not_korean", "forbidden"]


def _is_hangul(ch: str) -> bool:
    return "가" <= ch <= "힣" or "ㄱ" <= ch <= "ㆎ"


def check_ko_sentence(text: str) -> GuardFailure | None:
    """슬롯 문장(한 줄, MAX_LEN 이내) 검사. 내보내도 되면 None, 아니면 걸린 이유. 이유에는 문장 원문을 넣지 않는다."""
    s = text.strip()
    if "\n" in s:
        return "multiline"
    if len(s) > MAX_LEN:
        return "too_long"
    return check_ko_text(s)


def check_ko_text(text: str) -> GuardFailure | None:
    """번역문 검사. 길이·줄 수는 원문을 따르므로 보지 않고 한국어 여부와 금지어만 본다."""
    s = text.strip()
    if not s:
        return "empty"
    # 장비 이름 같은 외국어 낱말은 허용하되, 글자의 절반 이상이 한글이어야 한다.
    letters = [ch for ch in s if ch.isalpha()]
    if sum(map(_is_hangul, letters)) * 2 < len(letters):
        return "not_korean"
    if any(w in s for w in FORBIDDEN):
        return "forbidden"
    return None
