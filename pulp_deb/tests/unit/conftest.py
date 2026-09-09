import re
from pathlib import Path

import pytest

_SAVED_ARTIFACTS = []


@pytest.fixture
def save_artifact(request):
    """Returns a function that saves `content` to
    /tmp/pytest-artifacts/{test_name}.{param_case}[.{suffix}].{extension}, for inspecting
    test-generated artifacts (query dumps, etc.) after a run. Every saved path is printed in a
    summary at the end of the pytest session.
    """

    def _save(content: str, suffix: str | None = None, extension: str = "sql") -> Path:
        artifacts_dir = Path("/tmp/pytest-artifacts")
        artifacts_dir.mkdir(exist_ok=True)
        test_id = re.sub(r"\[(.+)\]$", r".\1", request.node.name)
        test_id = re.sub(r"[^\w.-]", "_", test_id)
        parts = [test_id, *([suffix] if suffix else []), extension]
        path = artifacts_dir / ".".join(parts)
        path.write_text(content)
        _SAVED_ARTIFACTS.append(path)
        return path

    return _save


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _SAVED_ARTIFACTS:
        return
    terminalreporter.write_sep("-", "saved artifacts")
    for path in _SAVED_ARTIFACTS:
        terminalreporter.write_line(str(path))
