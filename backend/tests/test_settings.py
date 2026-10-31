# 설정값: 환경 변수 읽기, 기본값, 잘못된 값 거절, 실제 서버 프로세스에서 값이 반영되는지.

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.llm_providers.anthropic import AnthropicClient
from app.settings import DEFAULT_INFO_DATE, get_llm_client, load_settings, settings

BACKEND = Path(__file__).parent.parent


def test_defaults():
    s = load_settings({})
    assert s.center_hours.model_dump() == {"open_hour": 9, "close_hour": 18, "workdays": [1, 2, 3, 4, 5]}
    assert s.info_date == DEFAULT_INFO_DATE
    assert s.cors_origins == ("http://localhost:5180",)
    assert (s.llm_provider, s.llm_model, s.llm_api_key, s.llm_timeout_s, s.llm_attempts) == ("anthropic", "claude-haiku-5-5", "", 10.0, 2)


def test_test_run_uses_defaults():
    # 동기화 테스트는 기본 설정값으로 만든 parity.json과 비교하므로 테스트 프로세스는 기본값이어야 한다.
    assert settings == load_settings({})


def test_reads_env():
    s = load_settings({"CENTER_HOURS": " 10:00-17:00 ", "INFO_DATE": "2026-11-01", "CORS_ORIGINS": "http://a.test, http://b.test,"})
    assert (s.center_hours.open_hour, s.center_hours.close_hour) == (10, 17)
    assert s.info_date == "2026-11-01"
    assert s.cors_origins == ("http://a.test", "http://b.test")


def test_reads_llm_env():
    s = load_settings({"LLM_MODEL": "claude-sonnet-5-5", "LLM_API_KEY": " sk-test ", "LLM_TIMEOUT_S": "4.5", "LLM_ATTEMPTS": "3"})
    assert (s.llm_model, s.llm_api_key, s.llm_timeout_s, s.llm_attempts) == ("claude-sonnet-5-5", "sk-test", 4.5, 3)


def test_api_key_is_not_in_repr():
    assert "sk-test-secret" not in repr(load_settings({"LLM_API_KEY": "sk-test-secret"}))


def test_llm_client_only_with_key():
    assert get_llm_client(load_settings({})) is None
    assert get_llm_client(load_settings({"LLM_API_KEY": "  "})) is None
    client = get_llm_client(load_settings({"LLM_API_KEY": "sk-test", "LLM_MODEL": "claude-sonnet-5-5"}))
    assert isinstance(client, AnthropicClient)
    assert client.model == "claude-sonnet-5-5"


def test_llm_limit_env():
    """LLM 호출 제한(backlog 20). 기본은 꺼져 있고, 헤더 이름은 소문자로 맞춘다."""
    s = load_settings({})
    assert (s.llm_rate_per_min, s.llm_daily_limit, s.llm_client_ip_header) == (0, 0, "")
    s = load_settings({"LLM_RATE_PER_MIN": "60", "LLM_DAILY_LIMIT": "3000", "LLM_CLIENT_IP_HEADER": " CF-Connecting-IP "})
    assert (s.llm_rate_per_min, s.llm_daily_limit, s.llm_client_ip_header) == (60, 3000, "cf-connecting-ip")


@pytest.mark.parametrize(
    "env",
    [
        {"CENTER_HOURS": "9-18"},
        {"CENTER_HOURS": "09:30-18:00"},
        {"CENTER_HOURS": "18:00-09:00"},
        {"CENTER_HOURS": "09:00-25:00"},
        {"INFO_DATE": "2026-13-01"},
        {"INFO_DATE": "next week"},
        {"LLM_PROVIDER": "openai"},
        {"LLM_MODEL": " "},
        {"LLM_TIMEOUT_S": "0"},
        {"LLM_TIMEOUT_S": "ten"},
        {"LLM_ATTEMPTS": "0"},
        {"LLM_ATTEMPTS": "1.5"},
        {"LLM_RATE_PER_MIN": "-1"},
        {"LLM_RATE_PER_MIN": "ten"},
        {"LLM_DAILY_LIMIT": "-5"},
        {"LLM_DAILY_LIMIT": "1.5"},
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


def test_server_starts_without_llm_key():
    """LLM_API_KEY가 없는 프로세스에서 서버가 뜨고 get_llm_client()는 None이다."""
    script = """
import json
from fastapi.testclient import TestClient
from app.main import app
from app.settings import get_llm_client
print(json.dumps({"health": TestClient(app).get("/api/health").status_code, "client": get_llm_client() is None}))
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LLM_", "ANTHROPIC_"))}
    out = subprocess.run([sys.executable, "-c", script], cwd=BACKEND, env=env, capture_output=True, text=True, check=True)
    assert json.loads(out.stdout.strip().splitlines()[-1]) == {"health": 200, "client": True}


def test_center_auth_defaults():
    # 센터 직원 로그인(backlog 17)은 기본으로 꺼져 있다.
    s = load_settings({})
    assert (s.center_auth, s.mail_provider, s.mail_api_key, s.mail_from) == ("off", "resend", "", "")
    assert (s.center_session_days, s.center_cookie_secure) == (30, True)


def test_center_auth_reads_env(tmp_path):
    s = load_settings(
        {
            "CENTER_AUTH": "email",
            "DB_PATH": str(tmp_path / "center.db"),
            "MAIL_API_KEY": " re_test ",
            "MAIL_FROM": "for-nav 센터 <no-reply@for-nav.com>",
            "CENTER_SESSION_DAYS": "7",
        }
    )
    assert (s.center_auth, s.mail_api_key, s.center_session_days) == ("email", "re_test", 7)
    assert "re_test" not in repr(s)


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"CENTER_AUTH": "password"}, "CENTER_AUTH"),
        ({"MAIL_PROVIDER": "smtp"}, "MAIL_PROVIDER"),
        ({"CENTER_SESSION_DAYS": "0"}, "CENTER_SESSION_DAYS"),
        ({"CENTER_COOKIE_SECURE": "yes"}, "CENTER_COOKIE_SECURE"),
        ({"CENTER_AUTH": "email"}, "DB_PATH"),
        ({"CENTER_AUTH": "email", "DB_PATH": "center.db", "MAIL_FROM": "a@b.c"}, "MAIL_API_KEY"),
        ({"CENTER_AUTH": "email", "DB_PATH": "center.db", "MAIL_PROVIDER": "console"}, "CENTER_COOKIE_SECURE=false"),
    ],
)
def test_center_auth_rejects(env, message):
    with pytest.raises(ValueError, match=message):
        load_settings(env)


def test_console_mail_only_for_local_http():
    s = load_settings({"CENTER_AUTH": "email", "DB_PATH": "center.db", "MAIL_PROVIDER": "console", "CENTER_COOKIE_SECURE": "false"})
    assert (s.mail_provider, s.center_cookie_secure) == ("console", False)
