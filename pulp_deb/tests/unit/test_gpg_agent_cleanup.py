import types
import subprocess
import pytest
from unittest.mock import MagicMock

from pulp_deb.app.tasks.synchronizing import DebUpdateReleaseFileAttributes


@pytest.fixture
def remote_with_key():
    r = MagicMock()
    r.gpgkey = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...\n-----END PGP PUBLIC KEY BLOCK-----"
    return r


@pytest.fixture
def remote_without_key():
    r = MagicMock()
    r.gpgkey = None
    return r


@pytest.fixture
def noop_stage_init(monkeypatch):
    # Avoid pulling in pulp internals
    monkeypatch.setattr(
        "pulp_deb.app.tasks.synchronizing.Stage.__init__",
        lambda self, *a, **k: None,
    )


@pytest.fixture
def force_tmp_cwd(monkeypatch):
    # Make sure gnupghome is in '/tmp'
    monkeypatch.setattr("pulp_deb.app.tasks.synchronizing.os.getcwd", lambda: "/tmp")


def gpg_factory(
    monkeypatch,
    *,
    homedir_from_kwargs: bool = True,
    homedir_value: str | None = "/tmp/gpg-home",
    import_keys_side_effect=None,
    import_keys_return=types.SimpleNamespace(count=1),
):
    """Patch gnupg.GPG with a MagicMock factory."""
    created = []

    def factory(**kwargs):
        g = MagicMock()
        g.gnupghome = kwargs["gnupghome"] if homedir_from_kwargs else homedir_value
        if import_keys_side_effect is not None:
            g.import_keys.side_effect = import_keys_side_effect
        else:
            g.import_keys.return_value = import_keys_return
        created.append(g)
        return g

    monkeypatch.setattr("pulp_deb.app.tasks.synchronizing.gnupg.GPG", factory)
    return created


def capture_run(monkeypatch, side_effect=None):
    """Capture subprocess.run calls; optional side_effect to raise."""
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if side_effect:
            raise side_effect
    monkeypatch.setattr("pulp_deb.app.tasks.synchronizing.subprocess.run", fake_run)
    return calls


def test_kills_gpg_agent_when_key_set(noop_stage_init, force_tmp_cwd, remote_with_key, monkeypatch):
    """With a gpgkey the agent is killed using the same /tmp homedir and expected kwargs."""
    created = gpg_factory(monkeypatch)
    calls = capture_run(monkeypatch)

    DebUpdateReleaseFileAttributes(remote_with_key)

    assert created[0].gnupghome == "/tmp/gpg-home"
    # gpgconf --kill gpg-agent was called with the same homedir
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd == ["/usr/bin/gpgconf", "--homedir", "/tmp/gpg-home", "--kill", "gpg-agent"]
    assert kwargs.get("check") is False
    assert kwargs.get("stdout") is subprocess.DEVNULL
    assert kwargs.get("stderr") is subprocess.DEVNULL

    created[0].import_keys.assert_called_once_with(remote_with_key.gpgkey)


def test_does_not_kill_gpg_agent_without_key(noop_stage_init, remote_without_key, monkeypatch):
    """Without a gpgkey no GPG construction and no gpgconf kill should occur."""
    # Ensure we don't construct GPG at all
    monkeypatch.setattr(
        "pulp_deb.app.tasks.synchronizing.gnupg.GPG",
        lambda **_: pytest.fail("GPG should not be constructed without a key"),
    )
    calls = capture_run(monkeypatch)

    DebUpdateReleaseFileAttributes(remote_without_key)
    assert calls == []


def test_cleanup_runs_even_if_init_raises(
    noop_stage_init,
    force_tmp_cwd,
    remote_with_key,
    monkeypatch,
):
    """Even if __init__ raises the decorator's finally kills the gpg-agent for /tmp homedir."""
    gpg_factory(monkeypatch, import_keys_side_effect=RuntimeError("boom"))
    calls = capture_run(monkeypatch)

    with pytest.raises(RuntimeError, match="boom"):
        DebUpdateReleaseFileAttributes(remote_with_key)

    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd == ["/usr/bin/gpgconf", "--homedir", "/tmp/gpg-home", "--kill", "gpg-agent"]
    assert kwargs.get("check") is False
    assert kwargs.get("stdout") is subprocess.DEVNULL
    assert kwargs.get("stderr") is subprocess.DEVNULL


def test_no_cleanup_when_no_homedir(noop_stage_init, force_tmp_cwd, remote_with_key, monkeypatch):
    """If gpg has no gnugphome, decorator should skip subprocess.run entirely."""
    gpg_factory(monkeypatch, homedir_from_kwargs=False, homedir_value=None)
    calls = capture_run(monkeypatch)

    DebUpdateReleaseFileAttributes(remote_with_key)
    assert calls == []


@pytest.mark.parametrize(
    "side_effect",
    [FileNotFoundError("gpgconf not found"), Exception("cleanup boom")],
)
def test_cleanup_exceptions_swallowed_when_init_ok(
    noop_stage_init,
    force_tmp_cwd,
    remote_with_key,
    monkeypatch,
    side_effect,
):
    """If __init__ succeeds but cleanup raises error, the error is swallowed."""
    gpg_factory(monkeypatch)
    calls = capture_run(monkeypatch, side_effect=side_effect)

    DebUpdateReleaseFileAttributes(remote_with_key)
    assert len(calls) == 1


def test_cleanup_exception_does_not_mask_init_error(
    noop_stage_init,
    force_tmp_cwd,
    remote_with_key,
    monkeypatch,
):
    """If __init__ raises and cleanup also raises, original init error must win."""
    gpg_factory(monkeypatch, import_keys_side_effect=RuntimeError("init boom"))

    def fake_run(*args, **kwargs):
        raise OSError("cleanup boom")

    monkeypatch.setattr("pulp_deb.app.tasks.synchronizing.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="init boom"):
        DebUpdateReleaseFileAttributes(remote_with_key)
