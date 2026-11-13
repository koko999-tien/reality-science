from app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.project_name == "REALITY SCIENCE API"
    assert s.jwt_algorithm == "HS256"
    assert s.access_token_expire_minutes == 60
