import logging

from fastapi import FastAPI

from app.log_filters import redact_query_string


def access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:5000", "GET", path, "1.1", 200),
        exc_info=None,
    )


def test_query_string_is_removed_from_access_log_lines() -> None:
    record = access_record("/api/symptoms?symptom=headache&start_date=2026-01-01")

    assert redact_query_string.filter(record) is True

    assert record.getMessage() == '127.0.0.1:5000 - "GET /api/symptoms HTTP/1.1" 200'


def test_path_without_query_string_is_unchanged() -> None:
    record = access_record("/api/health")

    redact_query_string.filter(record)

    assert record.getMessage() == '127.0.0.1:5000 - "GET /api/health HTTP/1.1" 200'


def test_record_without_arguments_is_left_alone() -> None:
    record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, "started", None, None)

    assert redact_query_string.filter(record) is True
    assert record.getMessage() == "started"


def test_creating_the_app_installs_the_filter_once(app: FastAPI) -> None:
    filters = logging.getLogger("uvicorn.access").filters

    assert filters.count(redact_query_string) == 1
