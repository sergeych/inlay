from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'tools/install_linux.py'


def run(prefix, bin_dir, *args):
    return subprocess.run([sys.executable, str(INSTALLER), '--prefix', str(prefix),
                           '--bin-dir', str(bin_dir), *args], capture_output=True, text=True)


def test_preserves_existing_launcher(tmp_path):
    bin_dir = tmp_path / 'bin'; bin_dir.mkdir()
    launcher = bin_dir / 'inlay'; launcher.write_bytes(b'keep my launcher\n')
    result = run(tmp_path / 'app', bin_dir)
    assert result.returncode == 1
    assert 'already exists' in result.stderr
    assert launcher.read_bytes() == b'keep my launcher\n'
    assert not (tmp_path / 'app').exists()


def test_force_does_not_take_over_unrelated_directory(tmp_path):
    prefix = tmp_path / 'app'; prefix.mkdir()
    original = prefix / 'important'; original.write_bytes(b'keep this')
    result = run(prefix, tmp_path / 'bin', '--force')
    assert result.returncode == 1
    assert 'not an Inlay installation' in result.stderr
    assert list(prefix.iterdir()) == [original]
    assert original.read_bytes() == b'keep this'
    assert not (tmp_path / 'bin').exists()


def test_missing_interpreter_leaves_no_installation(tmp_path):
    result = run(tmp_path / 'app', tmp_path / 'bin', '--python', str(tmp_path / 'missing-python'))
    assert result.returncode == 1
    assert not (tmp_path / 'app').exists()
    assert not (tmp_path / 'bin').exists()
