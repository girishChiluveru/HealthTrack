import logging

PATH_ARGUMENT_INDEX = 2


class RedactQueryString(logging.Filter):
    """Remove query strings from access log lines.

    Symptom filters travel in the URL, so the full path would put health data in the logs.
    Uvicorn formats these lines from the arguments
    (client address, method, path with query, HTTP version, status).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) > PATH_ARGUMENT_INDEX:
            path = str(args[PATH_ARGUMENT_INDEX]).split("?", 1)[0]
            record.args = (*args[:PATH_ARGUMENT_INDEX], path, *args[PATH_ARGUMENT_INDEX + 1 :])
        return True


redact_query_string = RedactQueryString()


def install_log_filters() -> None:
    # Adding the same filter object again has no effect, so repeated app creation is safe.
    logging.getLogger("uvicorn.access").addFilter(redact_query_string)
