# download.py의 해시 검증과 저장 규칙. 네트워크는 쓰지 않는다(_fetch를 바꿔 끼운다).

import io
import re
import zipfile
from pathlib import Path

import pytest

from fornav_modeling.data import download
from fornav_modeling.data.download import DownloadError, RawFile, Source, sha256_bytes

DATA_README = Path(__file__).resolve().parents[1] / "data" / "README.md"

URL_SOURCE = Source(key="web", files=(RawFile(name="a.csv", sha256=sha256_bytes(b"a,b\n1,2\n"), url="https://example.org/a.csv"),))
ZIP_SOURCE = Source(
    key="kg",
    kaggle="owner/slug",
    kaggle_version=1,
    files=(RawFile(name="x.csv", sha256=sha256_bytes(b"x\n")), RawFile(name="y.csv", sha256=sha256_bytes(b"y\n"))),
)


def make_zip(path: Path, members: dict[str, bytes]) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    path.write_bytes(buffer.getvalue())
    return path


@pytest.fixture
def fetched(monkeypatch):
    """_fetch 대신 넘길 응답(url → bytes)과 호출 기록."""
    responses, calls = {}, []

    def fake_fetch(url, headers=None):
        calls.append(url)
        return responses[url]

    monkeypatch.setattr(download, "_fetch", fake_fetch)
    return responses, calls


def test_registry_has_two_sources_with_valid_hashes():
    assert [s.key for s in download.SOURCES] == ["kaggle_symptom", "hira"]
    for source in download.SOURCES:
        names = [f.name for f in source.files]
        assert len(names) == len(set(names))
        for file in source.files:
            assert re.fullmatch(r"[0-9a-f]{64}", file.sha256)
            assert file.url is not None or source.kaggle is not None


def test_data_readme_lists_every_hash():
    # 코드의 해시와 data/README.md가 어긋나지 않게 한다.
    readme = DATA_README.read_text()
    for source in download.SOURCES:
        for file in source.files:
            assert file.sha256 in readme, f"{source.key}/{file.name}"


def test_verify_reports_ok_missing_mismatch(tmp_path):
    source = Source(
        key="s",
        files=(RawFile("ok.csv", sha256_bytes(b"1")), RawFile("missing.csv", sha256_bytes(b"2")), RawFile("bad.csv", sha256_bytes(b"3"))),
    )
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "ok.csv").write_bytes(b"1")
    (tmp_path / "s" / "bad.csv").write_bytes(b"changed")
    result = download.verify(source, tmp_path)
    assert result["ok.csv"] == "ok"
    assert result["missing.csv"] == "missing"
    assert result["bad.csv"] == f"mismatch {sha256_bytes(b'changed')}"


def test_download_saves_then_skips_valid_files(tmp_path, fetched):
    responses, calls = fetched
    responses["https://example.org/a.csv"] = b"a,b\n1,2\n"
    assert download.download(URL_SOURCE, tmp_path) == ["a.csv"]
    assert (tmp_path / "web" / "a.csv").read_bytes() == b"a,b\n1,2\n"
    assert download.download(URL_SOURCE, tmp_path) == []
    assert len(calls) == 1


def test_download_rejects_hash_mismatch_without_writing(tmp_path, fetched):
    responses, _ = fetched
    responses["https://example.org/a.csv"] = b"tampered"
    with pytest.raises(DownloadError, match="sha256 불일치"):
        download.download(URL_SOURCE, tmp_path)
    assert not (tmp_path / "web" / "a.csv").exists()


def test_download_from_manual_kaggle_zip_keeps_only_listed_files(tmp_path, fetched):
    _, calls = fetched
    archive = make_zip(tmp_path / "archive.zip", {"x.csv": b"x\n", "y.csv": b"y\n", "extra.csv": b"z\n"})
    raw = tmp_path / "raw"
    assert sorted(download.download(ZIP_SOURCE, raw, kaggle_zip=archive)) == ["x.csv", "y.csv"]
    assert sorted(p.name for p in (raw / "kg").iterdir()) == ["x.csv", "y.csv"]
    assert calls == []


def test_download_fails_when_zip_misses_a_file(tmp_path, fetched):
    archive = make_zip(tmp_path / "archive.zip", {"x.csv": b"x\n"})
    with pytest.raises(DownloadError, match="y.csv"):
        download.download(ZIP_SOURCE, tmp_path / "raw", kaggle_zip=archive)
    assert not (tmp_path / "raw" / "kg").exists()


def test_kaggle_without_token_or_zip_explains_manual_path(tmp_path, monkeypatch, fetched):
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    monkeypatch.setattr(download, "KAGGLE_TOKEN_FILE", tmp_path / "no_token")
    with pytest.raises(DownloadError, match="--kaggle-zip"):
        download.download(ZIP_SOURCE, tmp_path / "raw")


def test_kaggle_api_uses_pinned_version_and_bearer_token(tmp_path, monkeypatch):
    seen = {}

    def fake_fetch(url, headers=None):
        seen["url"], seen["headers"] = url, headers
        return make_zip(tmp_path / "api.zip", {"x.csv": b"x\n", "y.csv": b"y\n"}).read_bytes()

    monkeypatch.setenv("KAGGLE_API_TOKEN", "token-123\n")
    monkeypatch.setattr(download, "_fetch", fake_fetch)
    download.download(ZIP_SOURCE, tmp_path / "raw")
    assert seen["url"] == "https://www.kaggle.com/api/v1/datasets/download/owner/slug?datasetVersionNumber=1"
    assert seen["headers"] == {"Authorization": "Bearer token-123"}
