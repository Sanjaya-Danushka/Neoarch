import pytest
from neoarch.backend.workers import CommandWorker, PackageLoaderWorker


def test_command_worker_output_and_finish():
    w = CommandWorker(['sh', '-c', "printf 'hello\\n'"])
    outputs = []
    errors = []
    finished = {'v': False}
    w.output.connect(lambda s: outputs.append(s))
    w.error.connect(lambda s: errors.append(s))
    w.finished.connect(lambda: finished.__setitem__('v', True))
    w.run()
    assert 'hello' in outputs
    assert finished['v'] is True
    assert len(errors) == 0


def test_command_worker_error_on_nonzero():
    w = CommandWorker(['sh', '-c', "echo error 1>&2; exit 5"])
    outputs = []
    errors = []
    finished = {'v': False}
    w.output.connect(lambda s: outputs.append(s))
    w.error.connect(lambda s: errors.append(s))
    w.finished.connect(lambda: finished.__setitem__('v', True))
    w.run()
    assert finished['v'] is True
    assert len(errors) >= 1
    assert 'error' in ''.join(errors).lower()


def test_command_worker_handles_crlf_lines():
    """PTY output is CRLF-terminated; full lines must not be dropped."""
    w = CommandWorker(['sh', '-c', "printf 'alpha\\r\\nbeta\\r\\n'"])
    outputs = []
    w.output.connect(lambda s: outputs.append(s))
    w.run()
    assert 'alpha' in outputs
    assert 'beta' in outputs


def test_command_worker_progress_updates_via_line_update():
    """Carriage-return progress rewrites should emit the final state."""
    w = CommandWorker(['sh', '-c', "printf 'a\\rb\\rc\\n'"])
    outputs = []
    w.output.connect(lambda s: outputs.append(s))
    w.run()
    assert outputs == ['c']


def test_command_worker_streams_stderr_live():
    """Download progress written to stderr (curl/makepkg) must appear as output."""
    w = CommandWorker(['sh', '-c', "printf '%b' 'fetching...\\r100% done\\n' 1>&2"])
    outputs = []
    w.output.connect(lambda s: outputs.append(s))
    w.run()
    assert any('100% done' in s for s in outputs)


def test_package_loader_emits_packages_loaded():
    w = PackageLoaderWorker(['sh', '-c', "printf 'pkg 1.0\\n'"])
    received = []
    errors = []
    finished = {'v': False}
    w.packages_loaded.connect(lambda pkgs: received.append(pkgs))
    w.error_occurred.connect(lambda e: errors.append(e))
    w.finished.connect(lambda: finished.__setitem__('v', True))
    w.run()
    assert finished['v'] is True
    assert len(errors) == 0
    assert received and isinstance(received[0], list)
    assert received[0][0]['name'] == 'pkg'
    assert received[0][0]['version'] == '1.0'
