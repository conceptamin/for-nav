# 템플릿 공통 도우미. frontend/src/domain/templates.ts 상단과 1:1.

import re
from typing import Any

from app.vocab import PACKS, Lang, Term, pron


def pick(t: Term, lang: Lang) -> str:
    return t[lang]


def tpl(lang: Lang) -> dict[str, Any]:
    """한국어를 뺀 근로자 언어의 문장 틀(vocab.PACKS 언어 묶음의 templates)"""
    return PACKS[lang]["templates"]


def join_terms(terms: list[Term], key: Lang) -> str:
    return ", ".join(t[key] for t in terms)


def join_pron(terms: list[Term], lang: Lang) -> str:
    return ", ".join(pron(t, lang) for t in terms)


_SLOT = re.compile(r"\{(\w+)(:lower)?\}", re.ASCII)


def fill(frame: str, values: dict[str, str]) -> str:
    """문장 틀의 `{이름}`을 값으로, `{이름:lower}`를 소문자 값으로 채운다."""

    def sub(m: re.Match[str]) -> str:
        v = values.get(m.group(1), "")
        return v.lower() if m.group(2) else v

    return _SLOT.sub(sub, frame)
