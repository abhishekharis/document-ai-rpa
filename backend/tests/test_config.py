from pathlib import Path

from app.config import BACKEND_DIR, PROJECT_ROOT, Settings


def test_project_root_is_the_repository_root():
    assert BACKEND_DIR.name == "backend"
    assert PROJECT_ROOT == BACKEND_DIR.parent
    assert (PROJECT_ROOT / "docker-compose.yml").exists()


def test_root_env_file_is_loaded_with_priority():
    env_files = [Path(p) for p in Settings.model_config["env_file"]]
    assert env_files == [BACKEND_DIR / ".env", PROJECT_ROOT / ".env"]


def test_root_env_overrides_backend_env(tmp_path, monkeypatch):
    monkeypatch.delenv("RPA_API_KEY", raising=False)
    backend_env = tmp_path / "backend.env"
    root_env = tmp_path / "root.env"
    backend_env.write_text("RPA_API_KEY=from-backend\n")
    root_env.write_text("RPA_API_KEY=from-root\n")

    settings = Settings(_env_file=[str(backend_env), str(root_env)])

    assert settings.rpa_api_key == "from-root"


def test_development_allows_default_settings():
    Settings(_env_file=None, environment="development")


def test_production_rejects_default_rpa_key():
    import pytest
    with pytest.raises(ValueError, match="RPA_API_KEY"):
        Settings(_env_file=None, environment="production", cors_origins=["https://app.example.com"])


def test_production_rejects_localhost_cors():
    import pytest
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(_env_file=None, environment="production", rpa_api_key="x" * 32)


def test_production_accepts_safe_settings():
    settings = Settings(
        _env_file=None,
        environment="production",
        rpa_api_key="x" * 32,
        cors_origins=["https://app.example.com"],
    )
    assert settings.environment == "production"
