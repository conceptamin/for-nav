"""동기화 픽스처의 자유 입력을 실제 LLM에 넣어 키워드 추출과 비교한다. CI에서 돌지 않는다.

    uv run --env-file .env python scripts/extract_compare.py

같은 자유 입력은 처음 나온 픽스처 번호(parity.json의 extract 순서) 하나로 묶는다.
원문은 찍지 않고 번호와 열거값만 찍는다. 마지막 줄은 필드별·전체 일치 건수다.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rules.extract_llm import extract_with_llm  # noqa: E402
from app.rules.triage import extract_from_text  # noqa: E402
from app.settings import get_llm_client, settings  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "parity.json"
FIELDS = ["bodyParts", "symptoms", "onset", "workRelated", "workType"]


def short(ex: dict) -> dict:
    return {k: ex[k] for k in FIELDS}


async def main() -> int:
    client = get_llm_client()
    if client is None:
        print("LLM_API_KEY가 비어 있다. 키를 넣고 다시 실행한다.")
        return 1
    first: dict[str, int] = {}
    for n, case in enumerate(json.loads(FIXTURES.read_text())["extract"]):
        text = case["input"]["freeText"]
        if text.strip() and text not in first:
            first[text] = n
    print(f"model={settings.llm_model} inputs={len(first)}")

    same = {f: 0 for f in FIELDS}
    all_same = fallback = 0
    try:
        for text, n in first.items():
            kw = short(extract_from_text(text).model_dump(by_alias=True, mode="json"))
            ex, source = await extract_with_llm(text, client, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts)
            llm = short(ex.model_dump(by_alias=True, mode="json"))
            fallback += source != "llm"
            diff = [f for f in FIELDS if kw[f] != llm[f]]
            for f in FIELDS:
                same[f] += f not in diff
            all_same += not diff
            print(json.dumps({"n": n, "source": source, "diff": diff, "keywords": kw, "llm": llm}, ensure_ascii=False))
    finally:
        await client.aclose()
    print(
        json.dumps(
            {"allSame": f"{all_same}/{len(first)}", "fallback": fallback, "byField": {f: f"{v}/{len(first)}" for f, v in same.items()}}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
