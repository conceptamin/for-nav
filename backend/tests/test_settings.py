# 설정값: 환경 변수 읽기, 기본값, 잘못된 값 거절, 실제 서버 프로세스에서 값이 반영되는지.

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.settings import DEFAULT_INFO_DATE, load_settings, settings

BACKEND = Path(__file__).parent.parent


def test_defaults():
    s = load_settings({})
    assert s.center_hours.model_dump() == {"open_hour": 9, "close_hour": 18, "workdays": [1, 2, 3, 4, 5]}
    assert s.info_date == DEFAULT_INFO_DATE
    assert s.cors_origins == ("http://localhost:5180",)


def test_test_run_uses_defaults():
    # 동기화 테스트는 기본 설정값으로 만든 parity.json과 비교하므로 테스트 프로세스는 기본값이어야 한다.
    assert settings == load_settings({})


def test_reads_env():
    s = load_settings({"CENTER_HOURS": " 10:00-17:00 ", "INFO_DATE": "2026-11-01", "CORS_ORIGINS": "http://a.test, http://b.test,"})
    assert (s.center_hours.open_hour, s.center_hours.close_hour) == (10, 17)
    assert s.info_date == "2026-11-01"
    assert s.cors_origins == ("http://a.test", "http://b.test")


@pytest.mark.parametrize(
    "env",
    [
        {"CENTER_HOURS": "9-18"},
        {"CENTER_HOURS": "09:30-18:00"},
        {"CENTER_HOURS": "18:00-09:00"},
        {"CENTER_HOURS": "09:00-25:00"},
        {"INFO_DATE": "2026-13-01"},
        {"INFO_DATE": "next week"},
    ],
)
def test_rejects_bad_values(env):
    with pytest.raises(ValueError, match=next(iter(env))):
        load_settings(env)


def test_env_reaches_meta_and_after_hours():
    """CENTER_HOURS=10:00-17:00으로 띄운 프로세스에서 /api/meta와 운영 시간 외 판정이 그 값을 따른다."""
    script = """
import json
from datetime import datetime
from fastapi.testclient import TestClient
from app import clock
from app.main import app
from app.rules.coverage import is_after_hours
at = lambda h, m: datetime(2026, 10, 28, h, m, tzinfo=clock.SEOUL)  # 수요일
print(json.dumps({
    "meta": TestClient(app).get("/api/meta").json(),
    "afterHours": [is_after_hours(at(h, m)) for h, m in [(9, 30), (10, 0), (16, 59), (17, 0)]],
}))
"""
    env = {**os.environ, "CENTER_HOURS": "10:00-17:00", "INFO_DATE": "2026-11-01"}
    out = subprocess.run([sys.executable, "-c", script], cwd=BACKEND, env=env, capture_output=True, text=True, check=True)
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["meta"] == {"infoDate": "2026-11-01", "centerHours": {"openHour": 10, "closeHour": 17, "workdays": [1, 2, 3, 4, 5]}}
    assert got["afterHours"] == [True, False, False, True]
