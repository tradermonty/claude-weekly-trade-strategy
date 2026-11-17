"""The unattended daily action plan run may write only its own scratch dir (#19).

It used to allow every path under /tmp. Git worktrees of this and other
repositories live under /private/tmp, and the runner's change detection only
watches its own checkout, so a write there went unnoticed.
"""
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "run_daily_action_plan.sh"

_spec = importlib.util.spec_from_file_location(
    "bps_scratch", ROOT / ".claude/skills/daily-action-plan/scripts/build_plan_state.py")
bps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bps)


def test_runner_grants_no_bare_tmp_root():
    text = RUNNER.read_text()
    edits = re.findall(r'"Edit\(([^)]*)\)"', text)
    assert edits, "the allowlist moved; update this test"
    for rule in edits:
        assert not re.match(r"^/+(private/)?tmp(/\*\*)?$", rule), rule
    dirs = re.search(r'DAP_ALLOWED_OUTPUT_DIRS="([^"]*)"', text).group(1)
    for entry in dirs.split(":"):
        assert entry not in ("/tmp", "/private/tmp"), dirs
    assert "Edit(/${DAP_SCRATCH}/**)" in text


@pytest.fixture
def allowed_env():
    old = os.environ.get("DAP_ALLOWED_OUTPUT_DIRS")
    yield
    if old is None:
        os.environ.pop("DAP_ALLOWED_OUTPUT_DIRS", None)
    else:
        os.environ["DAP_ALLOWED_OUTPUT_DIRS"] = old


def test_output_outside_reports_is_refused_even_under_an_allowed_root(allowed_env):
    """A checkout under an allowed root (a worktree in /tmp) stays protected."""
    os.environ["DAP_ALLOWED_OUTPUT_DIRS"] = str(ROOT.parent)
    assert not bps._output_path_allowed(str(ROOT / "trading" / "x.json"))
    assert not bps._output_path_allowed(str(ROOT / "pyproject.toml"))
    assert not bps._output_path_allowed(str(ROOT / "reports-old" / "x.json"))
    assert bps._output_path_allowed(str(ROOT / "reports" / "2026-11-17" / "x.json"))


def test_output_to_another_tmp_dir_is_refused(allowed_env):
    base = Path(tempfile.mkdtemp())
    try:
        scratch, other = base / "dap.abc", base / "wts-other"
        scratch.mkdir()
        other.mkdir()
        os.environ["DAP_ALLOWED_OUTPUT_DIRS"] = f"{scratch}{os.pathsep}{ROOT / 'reports'}"
        assert bps._output_path_allowed(str(scratch / "plan_state.json"))
        assert not bps._output_path_allowed(str(other / "x.json"))
    finally:
        shutil.rmtree(base, ignore_errors=True)


# --- the runner itself, with a stand-in claude CLI --------------------------

FAKE_CLAUDE = """#!/bin/bash
{
  echo "PROMPT=$2"
  echo "SCRATCH=$DAP_SCRATCH"
  echo "OUTDIRS=$DAP_ALLOWED_OUTPUT_DIRS"
  for a in "$@"; do echo "ARG=$a"; done
} > "$FAKE_RECORD"
echo '{}' > "$DAP_SCRATCH/plan_state.json" || exit 9
exit "${FAKE_EXIT:-0}"
"""

needs_bash = pytest.mark.skipif(shutil.which("bash") is None or sys.platform == "win32",
                                reason="needs bash")


def _write_exec(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def fake_project(tmp_path):
    """A copy of the runner in a throwaway project, so the run touches nothing real."""
    proj = tmp_path / "proj"
    _write_exec(proj / "scripts" / "run_daily_action_plan.sh", RUNNER.read_text())
    _write_exec(proj / ".claude/skills/daily-action-plan/scripts/build_plan_state.py",
                "print('OPEN')\n")
    _write_exec(tmp_path / "bin" / "claude", FAKE_CLAUDE)
    return proj, tmp_path


def _run(proj, tmp_path, fake_exit=0, tmpdir=None):
    record = tmp_path / "record.txt"
    tmpdir = str(tmpdir) if tmpdir else str(tmp_path / "tmp")
    Path(tmpdir).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, FMP_API_KEY="dummy", CLAUDE_BIN=str(tmp_path / "bin" / "claude"),
               FAKE_RECORD=str(record), FAKE_EXIT=str(fake_exit), TMPDIR=tmpdir)
    env.pop("DAP_ALLOWED_OUTPUT_DIRS", None)
    proc = subprocess.run(["bash", str(proj / "scripts" / "run_daily_action_plan.sh"),
                           "post-market"], env=env, capture_output=True, text=True,
                          timeout=60)
    lines = record.read_text().splitlines() if record.exists() else []
    return proc, lines, tmpdir


def _value(lines, key):
    return next(line.split("=", 1)[1] for line in lines if line.startswith(key + "="))


def _kept(proj):
    """The copy of the scratch JSON the runner keeps next to its log."""
    return list((proj / "logs").glob("dap-*-post-market.d/plan_state.json"))


@needs_bash
def test_runner_hands_claude_a_private_scratch_dir_and_removes_it(fake_project):
    proj, tmp_path = fake_project
    proc, lines, tmpdir = _run(proj, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    scratch = _value(lines, "SCRATCH")
    assert os.path.dirname(scratch) == os.path.realpath(tmpdir)
    assert os.path.basename(scratch).startswith("dap.")
    assert _value(lines, "PROMPT").endswith(f"--scratch-dir {scratch}")
    assert _value(lines, "OUTDIRS") == f"{scratch}:{proj}/reports"
    args = [line.split("=", 1)[1] for line in lines if line.startswith("ARG=")]
    edits = [a for a in args if a.startswith("Edit(")]
    assert f"Edit(/{scratch}/**)" in edits
    assert not any(re.match(r"^Edit\(/+(private/)?tmp/\*\*\)$", a) for a in edits), edits
    assert not os.path.exists(scratch), "scratch dir must be removed after the run"
    assert _kept(proj), "the scratch JSON must be kept next to the log"


@needs_bash
def test_runner_keeps_the_json_and_exit_code_when_claude_fails(fake_project):
    proj, tmp_path = fake_project
    proc, lines, tmpdir = _run(proj, tmp_path, fake_exit=3)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    scratch = _value(lines, "SCRATCH")
    assert scratch, "the runner must hand claude a scratch dir"
    assert not os.path.exists(scratch)
    assert list(Path(tmpdir).iterdir()) == []
    assert _kept(proj), "a failed run is exactly when the JSON is needed"


@needs_bash
def test_runner_accepts_tmpdir_with_trailing_slash(fake_project):
    proj, tmp_path = fake_project
    proc, lines, tmpdir = _run(proj, tmp_path, tmpdir=f"{tmp_path}/tmp2/")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert os.path.dirname(_value(lines, "SCRATCH")) == os.path.realpath(tmpdir)


@needs_bash
def test_runner_refuses_a_scratch_dir_inside_the_repository(fake_project):
    proj, tmp_path = fake_project
    proc, lines, _ = _run(proj, tmp_path, tmpdir=proj / "tmp")
    assert proc.returncode == 1
    assert lines == [], "claude must not be started"
    assert "inside the repository" in proc.stdout


@needs_bash
def test_runner_refuses_a_scratch_dir_with_whitespace(fake_project):
    proj, tmp_path = fake_project
    proc, lines, _ = _run(proj, tmp_path, tmpdir=tmp_path / "my tmp")
    assert proc.returncode == 1
    assert lines == []
    assert "whitespace" in proc.stdout
