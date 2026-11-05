import pytest

from tests.conftest import build_settings


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@host:5432/db?sslmode=require",
        "postgres://u:p@host:5432/db?sslmode=require",
        "postgresql+psycopg://u:p@host:5432/db?sslmode=require",
    ],
)
def test_hosted_database_urls_use_the_installed_driver(url: str) -> None:
    settings = build_settings(database_url=url)
    assert settings.database_url.get_secret_value() == (
        "postgresql+psycopg://u:p@host:5432/db?sslmode=require"
    )
