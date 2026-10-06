from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_worldclass_files_exist():

    required = [
        "app/config.py",
        "app/routes/account.py",
        "app/routes/showcase.py",
        "app/templates/platform.html",
        "app/templates/about.html",
        "app/templates/feedback.html",
        "app/routes/feedback.py",
        "app/services/feedback_service.py",
        "app/models/feedback.py",
        "app/forms/feedback_forms.py",
        "migrations/versions/d7e4f1a2b3c4_add_internal_feedback.py",
        "app/templates/security.html",
        "app/templates/errors/404.html",
        "app/templates/errors/500.html",
        "docs/WORLDCLASS_ROADMAP.md",
        "tests/conftest.py",
        "tests/test_app.py",
        "tests/test_config.py",
    ]

    for item in required:
        assert (ROOT / item).exists(), item


def test_env_is_gitignored():

    gitignore = ROOT / ".gitignore"

    assert gitignore.exists()

    content = gitignore.read_text(
        encoding="utf-8"
    )

    assert ".env" in content


def test_venv_is_gitignored():

    gitignore = ROOT / ".gitignore"

    content = gitignore.read_text(
        encoding="utf-8"
    )

    assert "venv/" in content or ".venv/" in content