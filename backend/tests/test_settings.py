import pytest

from app.settings import DEFAULT_HOST, DEFAULT_PORT, HOST_ENV, PORT_ENV, Settings, load_settings


def test_defaults_match_frontend_proxy_origin() -> None:
    assert load_settings({}) == Settings(host="127.0.0.1", port=8000)
    assert (DEFAULT_HOST, DEFAULT_PORT) == ("127.0.0.1", 8000)


def test_host_and_port_come_from_env() -> None:
    settings = load_settings({HOST_ENV: " 0.0.0.0 ", PORT_ENV: "9001"})

    assert settings == Settings(host="0.0.0.0", port=9001)


@pytest.mark.parametrize("port", ["", "0", "65536", "-1", "80.5", "http", "1e3"])
def test_invalid_port_is_rejected(port: str) -> None:
    with pytest.raises(ValueError, match=PORT_ENV):
        load_settings({PORT_ENV: port})


def test_empty_host_is_rejected() -> None:
    with pytest.raises(ValueError, match=HOST_ENV):
        load_settings({HOST_ENV: "  "})
