from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def _health() -> dict:
    response = client.get("/health")
    assert response.status_code == 200
    return response.json()


def test_health_reports_ok_and_version() -> None:
    body = _health()
    assert body["status"] == "ok"
    assert body["version"] == app.version


def test_health_reports_the_deployed_commit(monkeypatch) -> None:
    """Render sets RENDER_GIT_COMMIT at runtime; /health has to actually read it.

    Settings are lru_cached, so the cache is cleared on both sides — otherwise this passes
    against a hardcoded value, or leaks a fake SHA into every test that follows.
    """
    monkeypatch.setenv("RENDER_GIT_COMMIT", "5ef953ecafe0000000000000000000000000000")
    get_settings.cache_clear()
    try:
        assert _health()["commit"] == "5ef953ecafe0000000000000000000000000000"
    finally:
        get_settings.cache_clear()


def test_health_reports_unknown_commit_off_platform(monkeypatch) -> None:
    """Local development sets no such variable, and the endpoint must not break or lie."""
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    get_settings.cache_clear()
    try:
        assert _health()["commit"] == "unknown"
    finally:
        get_settings.cache_clear()


def test_version_comes_from_package_metadata() -> None:
    """The reported version must track pyproject.toml, not a second hardcoded copy.

    Hardcoding it in main.py as well is what let the backend sit at 0.1.1 while the iOS app moved
    to 0.1.2, so this asserts they're the same value rather than merely well-formed.
    """
    import tomllib
    from pathlib import Path

    from app.main import _version

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text())["project"]["version"]

    assert _version() == declared, f"/health reports {_version()}, pyproject declares {declared}"
    assert _health()["version"] == declared


def test_version_falls_back_when_not_installed(monkeypatch) -> None:
    """A source checkout with nothing installed must not take the app down over a version string."""
    from importlib.metadata import PackageNotFoundError

    import app.main as main_module

    def _missing(_name: str) -> str:
        raise PackageNotFoundError("muvi-backend")

    monkeypatch.setattr(main_module, "installed_version", _missing)
    assert main_module._version() == "0.0.0+unknown"
