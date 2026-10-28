# 외부 원본 데이터를 data/raw/<출처>/에 내려받고 sha256을 검증한다.
#   uv run python scripts/download_data.py                 없거나 해시가 다른 파일만 내려받은 뒤 검증
#   uv run python scripts/download_data.py --verify        내려받지 않고 해시만 검증
#   uv run python scripts/download_data.py --source hira   출처 하나만 (여러 번 줄 수 있다)
#   uv run python scripts/download_data.py --kaggle-zip ~/Downloads/archive.zip   Kaggle zip을 수동으로 받았을 때

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # package = false라 설치되지 않으므로 src를 직접 찾는다

from fornav_modeling.data import download  # noqa: E402

parser = argparse.ArgumentParser(description="외부 원본 데이터를 내려받고 sha256을 검증한다")
parser.add_argument("--verify", action="store_true", help="내려받지 않고 해시만 검증한다")
parser.add_argument("--source", action="append", choices=[s.key for s in download.SOURCES], help="기본값: 전부")
parser.add_argument("--kaggle-zip", type=Path, help="수동으로 내려받은 Kaggle zip 경로")
args = parser.parse_args()

failed = False
for source in [download.get_source(key) for key in args.source] if args.source else download.SOURCES:
    if not args.verify:
        saved = download.download(source, ROOT / "data" / "raw", kaggle_zip=args.kaggle_zip)
        print(f"{source.key}: 내려받음 {len(saved)}개 {saved}")
    for name, status in download.verify(source, ROOT / "data" / "raw").items():
        print(f"  {status:8} {source.key}/{name}")
        failed |= status != "ok"

sys.exit(1 if failed else 0)
