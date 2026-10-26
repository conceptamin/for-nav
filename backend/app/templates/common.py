# 템플릿 공통 도우미. frontend/src/domain/templates.ts 상단과 1:1.

from collections.abc import Mapping

from app.vocab import Lang, Term, pron

# 언어별 문장 {ko, en, vi}
type TriDict = Mapping[str, str]


def pick(t: TriDict | Term, lang: Lang) -> str:
    return t[lang]


def join_terms(terms: list[Term], key: Lang) -> str:
    return ", ".join(t[key] for t in terms)


def join_pron(terms: list[Term], lang: Lang) -> str:
    return ", ".join(pron(t, lang) for t in terms)


def tri(ko: str, en: str, vi: str) -> dict[str, str]:
    return {"ko": ko, "en": en, "vi": vi}
