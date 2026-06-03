from config.settings import Settings


def test_settings_defaults():
    s = Settings()
    assert s.max_articles_per_run == 50
    assert s.minhash_threshold == 0.72
    assert s.high_severity_threshold == 0.7


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("MAX_ARTICLES_PER_RUN", "10")
    s = Settings()
    assert s.max_articles_per_run == 10
