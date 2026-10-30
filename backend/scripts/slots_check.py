"""동기화 픽스처의 자유 입력을 실제 LLM으로 상황 줄 요약에 넣어 guard 검사 결과를 센다. CI에서 돌지 않는다.

    uv run --env-file .env python scripts/slots_check.py

같은 자유 입력은 처음 나온 픽스처 번호(parity.json의 extract 순서) 하나로 묶는다.
원문·요약은 찍지 않고 번호, 글자 수, 검사 결과만 찍는다. 마지막 줄은 통과·거부 사유별·호출 실패 건수다.
"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm import LLMUnavailableError, generate  # noqa: E402
from app.settings import get_llm_client, settings  # noqa: E402
from app.templates.guard import check_ko_sentence  # noqa: E402
from app.templates.llm_slots import SlotOutput, prompt_for  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "parity.json"


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

    result: Counter[str] = Counter()
    try:
        for text, n in first.items():
            try:
                out = await generate(client, prompt_for(text), SlotOutput, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts)
            except LLMUnavailableError:
                result["unavailable"] += 1
                print(json.dumps({"n": n, "result": "unavailable"}))
                continue
            failure = check_ko_sentence(out.ko) or "ok"
            result[failure] += 1
            print(json.dumps({"n": n, "len": len(out.ko.strip()), "result": failure}))
    finally:
        await client.aclose()
    print(json.dumps({"total": len(first), **result}))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
