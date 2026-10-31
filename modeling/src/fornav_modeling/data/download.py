# 외부 원본 데이터를 내려받고 sha256으로 검증한다. 출처 URL·라이선스·열 설명은 data/README.md에 있다.
# 해시는 여기 고정한다. 출처가 파일을 바꾸면 검증이 실패하고, 그때 새 파일을 확인한 뒤 해시와 data/README.md를 함께 고친다.
# 원본은 받은 바이트 그대로 저장한다(인코딩 변환·열 정리는 03, 05의 가공 단계에서 한다).

import hashlib
import io
import os
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

KAGGLE_API = "https://www.kaggle.com/api/v1/datasets/download"
KAGGLE_TOKEN_FILE = Path.home() / ".kaggle" / "access_token"


@dataclass(frozen=True)
class RawFile:
    name: str  # data/raw/<출처>/ 아래 저장할 파일 이름
    sha256: str
    url: str | None = None  # None이면 출처의 Kaggle zip 안에 같은 이름으로 들어 있다


@dataclass(frozen=True)
class Source:
    key: str  # data/raw/ 아래 폴더 이름
    files: tuple[RawFile, ...]
    kaggle: str | None = None  # "owner/slug"
    kaggle_version: int | None = None


SOURCES: tuple[Source, ...] = (
    Source(
        key="kaggle_symptom",
        kaggle="itachi9604/disease-symptom-description-dataset",
        kaggle_version=2,
        files=(
            RawFile(name="dataset.csv", sha256="ebbd391c4ba4d64f57a00eb3d0a55f0ca9b920b0c5de6b9af4234e72519c9618"),
            RawFile(name="Symptom-severity.csv", sha256="cb5a84b5ebde81bb18738b7e7733bcbc5abdc667b4376893fb1774d8c444bc8d"),
            RawFile(name="symptom_Description.csv", sha256="e0581662e815509596707ebb5b31efb44539562b451ecef8c1246aa713b7d832"),
            RawFile(name="symptom_precaution.csv", sha256="49371294708232b928f68fc60e9837e5cab8b90d450b7bd90f7305795bb6d311"),
        ),
    ),
    # 공공데이터포털 파일데이터. atchFileId는 연간 갱신 때 바뀐다(차기 등록 예정 2027-08-14).
    Source(
        key="hira",
        files=(
            RawFile(
                name="hospital_department_disease_2025.csv",
                sha256="cb3db8312d715a2af05fcef2fb184c4b15e76c02e07c4e3fca102044c06be00b",
                url="https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003676566&fileDetailSn=1&insertDataPrcus=N",
            ),
            RawFile(
                name="clinic_specialty_disease_2025.csv",
                sha256="50ea3afc9ccb8eca4ce83bc684bb15ba319ac39bf959af4ed8a83a3ecefbba2c",
                url="https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003678463&fileDetailSn=1&insertDataPrcus=N",
            ),
        ),
    ),
)


class DownloadError(RuntimeError):
    pass


def get_source(key: str) -> Source:
    for source in SOURCES:
        if source.key == key:
            return source
    raise KeyError(f"알 수 없는 출처: {key} (가능한 값: {', '.join(s.key for s in SOURCES)})")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(source: Source, raw_dir: Path) -> dict[str, str]:
    """파일 이름 → "ok" | "missing" | "mismatch <실제 sha256>". 내려받지 않는다."""
    results = {}
    for file in source.files:
        path = raw_dir / source.key / file.name
        if not path.exists():
            results[file.name] = "missing"
        else:
            actual = sha256_file(path)
            results[file.name] = "ok" if actual == file.sha256 else f"mismatch {actual}"
    return results


def download(source: Source, raw_dir: Path, kaggle_zip: Path | None = None) -> list[str]:
    """없거나 해시가 다른 파일만 내려받아 저장하고, 저장한 파일 이름을 돌려준다.
    받은 바이트의 해시가 다르면 저장하지 않고 DownloadError를 낸다. kaggle_zip은 수동으로 내려받은 zip 경로다."""
    status = verify(source, raw_dir)
    todo = [f for f in source.files if status[f.name] != "ok"]
    if not todo:
        return []

    contents: dict[str, bytes] = {}
    if any(f.url is None for f in todo):
        contents.update(_read_kaggle_zip(source, kaggle_zip))
    for file in todo:
        if file.url is not None:
            contents[file.name] = _fetch(file.url)

    # 모든 파일을 먼저 검증한 뒤 저장해, 일부만 바뀐 폴더가 남지 않게 한다.
    for file in todo:
        if file.name not in contents:
            raise DownloadError(f"{source.key}: zip에 {file.name}이 없다")
        actual = sha256_bytes(contents[file.name])
        if actual != file.sha256:
            raise DownloadError(f"{source.key}/{file.name}: sha256 불일치 (기대 {file.sha256}, 실제 {actual})")

    target = raw_dir / source.key
    target.mkdir(parents=True, exist_ok=True)
    for file in todo:
        (target / file.name).write_bytes(contents[file.name])
    return [f.name for f in todo]


def _read_kaggle_zip(source: Source, kaggle_zip: Path | None) -> dict[str, bytes]:
    if kaggle_zip is not None:
        data = kaggle_zip.read_bytes()
    else:
        token = _kaggle_token()
        if token is None:
            raise DownloadError(
                f"{source.key}: Kaggle 토큰이 없다. KAGGLE_API_TOKEN 환경변수나 {KAGGLE_TOKEN_FILE}에 토큰을 두거나, "
                f"https://www.kaggle.com/datasets/{source.kaggle} 에서 zip을 받아 --kaggle-zip으로 경로를 넘긴다"
            )
        url = f"{KAGGLE_API}/{source.kaggle}?datasetVersionNumber={source.kaggle_version}"
        data = _fetch(url, {"Authorization": f"Bearer {token}"})
    wanted = {f.name for f in source.files if f.url is None}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {name: zf.read(name) for name in zf.namelist() if name in wanted}


def _kaggle_token() -> str | None:
    if token := os.environ.get("KAGGLE_API_TOKEN"):
        return token.strip()
    if KAGGLE_TOKEN_FILE.exists():
        return KAGGLE_TOKEN_FILE.read_text().strip()
    return None


def _fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "for-nav-modeling", **(headers or {})})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()
