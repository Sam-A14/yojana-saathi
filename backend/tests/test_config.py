import pytest

from app.config import DEFAULT_LLM_MODEL, Settings, to_driver_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        (
            "postgresql://u:p@ep-x.neon.tech/db?sslmode=require",
            "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require",
        ),
        # Already in driver form: left alone.
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_to_driver_url(given: str, expected: str) -> None:
    assert to_driver_url(given) == expected


def test_database_url_is_optional_but_required_when_used() -> None:
    settings = Settings(database_url=None, _env_file=None)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        _ = settings.sqlalchemy_database_url


def test_default_model_is_the_one_confirmed_by_extraction_run_5() -> None:
    assert DEFAULT_LLM_MODEL == "gemini-3.6-flash"
    assert Settings(_env_file=None).llm_model == "gemini-3.6-flash"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_model_falls_back_to_the_default(blank: str) -> None:
    assert Settings(llm_model=blank, _env_file=None).llm_model == DEFAULT_LLM_MODEL


def test_empty_llm_model_environment_variable_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    # What an unset GitHub repository variable looks like to the job: the variable exists, empty.
    monkeypatch.setenv("LLM_MODEL", "")
    assert Settings(_env_file=None).llm_model == DEFAULT_LLM_MODEL


def test_a_real_model_name_is_kept_and_trimmed() -> None:
    assert Settings(llm_model=" gemini-x ", _env_file=None).llm_model == "gemini-x"
