import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize(
    "options",
    [
        {"cpu_threads": 0},
        {"port": 0},
        {"port": 65536},
        {"device": "mps"},
        {"max_length": 8193},
        {"head_length": 8188},
        {"max_pending_requests": 0},
    ],
)
def test_invalid_settings_fail_fast(options):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **options)


def test_environment_settings(monkeypatch):
    monkeypatch.setenv("CPU_THREADS", "8")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("DEVICE", "cuda:0")
    settings = Settings(_env_file=None)
    assert (settings.cpu_threads, settings.port, settings.device) == (8, 9000, "cuda:0")
