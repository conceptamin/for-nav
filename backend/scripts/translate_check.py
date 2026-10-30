"""동기화 픽스처의 자유 입력을 실제 LLM으로 번역·역번역 검사해 수락·거부 건수와 소요 시간을 센다. CI에서 돌지 않는다.

    uv run --env-file .env python scripts/translate_check.py

같은 자유 입력은 처음 나온 픽스처 번호(parity.json의 extract 순서) 하나로 묶고, 그 픽스처의 언어로 번역한다.
원문·번역은 찍지 않고 번호, 언어, 결과, 거부 사유, 소요 초만 찍는다. 마지막 줄은 결과·사유별 건수와 소요 시간이다.
"""

import asyncio
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_llm_client, settings  # noqa: E402
from app.templates.translate import translate_note  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "parity.json"


class Reasons(logging.Handler):
    """translate 모듈의 거부 로그("translation rejected=<사유>")에서 사유만 모은다."""

    def __init__(self) -> None:
        super().__init__()
        self.last: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        self.last = record.getMessage().removeprefix("translation rejected=")


async def main() -> int:
    client = get_llm_client()
    if client is None:
        print("LLM_API_KEY가 비어 있다. 키를 넣고 다시 실행한다.")
        return 1
    reasons = Reasons()
    logger = logging.getLogger("app.templates.translate")
    logger.addHandler(reasons)
    logger.setLevel(logging.INFO)

    first: dict[str, tuple[int, str]] = {}
    for n, case in enumerate(json.loads(FIXTURES.read_text())["extract"]):
        text = case["input"]["freeText"]
        if text.strip() and text not in first:
            first[text] = (n, case["input"]["language"])
    print(f"model={settings.llm_model} inputs={len(first)}")

    result: Counter[str] = Counter()
    seconds: list[float] = []
    try:
        for text, (n, lang) in first.items():
            reasons.last = None
            start = time.perf_counter()
            tr = await translate_note(text, lang, client, timeout_s=settings.llm_timeout_s, attempts=settings.llm_attempts)
            took = time.perf_counter() - start
            key = f"rejected:{reasons.last}" if tr.status == "rejected" else tr.status
            result[key] += 1
            if tr.status != "skipped" or lang != "ko":
                seconds.append(took)
            print(json.dumps({"n": n, "lang": lang, "result": key, "s": round(took, 2)}))
    finally:
        await client.aclose()
    timed = sorted(seconds)
    print(
        json.dumps(
            {
                "total": len(first),
                **result,
                "secondsAvg": round(sum(timed) / len(timed), 2) if timed else None,
                "secondsMax": round(timed[-1], 2) if timed else None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
