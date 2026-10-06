from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_FILES = [
    "app/templates/platform.html",
    "app/templates/pricing.html",
    "app/templates/faq.html",
    "app/templates/about.html",
    "app/templates/support.html",
    "app/templates/feedback.html",
    "app/templates/security.html",
    "docs/PUBLIC_WEB_DOCUMENTATION.md",
]


def test_public_documentation_files_exist():
    for item in EXPECTED_FILES:
        assert (ROOT / item).exists(), item


def test_public_nav_uses_intended_public_information_architecture():
    content = (
        ROOT / "app/templates/includes/public_navbar.html"
    ).read_text(encoding="utf-8")

    assert "showcase.platform" in content
    assert "showcase.pricing" in content
    assert "showcase.faq" in content
    assert "showcase.about" in content
    assert "feedback.submit" in content

    # Support intentionally remains in the footer rather than the primary navbar.
    assert "showcase.support" not in content

    assert 'href="#pricing"' not in content
    assert 'href="#faq"' not in content


def test_security_txt_uses_security_policy_route():
    content = (
        ROOT / "app/__init__.py"
    ).read_text(encoding="utf-8")

    assert 'url_for("showcase.security", _external=True)' in content
    assert 'url_for("security_txt", _external=True)' in content


def test_support_and_security_are_documented_in_footer():
    content = (
        ROOT / "app/templates/includes/footer.html"
    ).read_text(encoding="utf-8")

    assert "showcase.security" in content
    assert "showcase.support" in content
    assert "feedback.submit" in content
    assert "showcase.about" in content
    assert "compliance.privacy" in content
    assert "compliance.terms" in content
    assert "compliance.ai_disclosure" in content
