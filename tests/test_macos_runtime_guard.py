import importlib.util
from pathlib import Path

import pytest


def helper():
    path = Path(__file__).resolve().parents[1] / "scripts/macos_runtime_guard.py"
    spec = importlib.util.spec_from_file_location("runtime_guard_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("fail_in_work", [False, True])
def test_activity_ends_on_success_or_error(monkeypatch, fail_in_work):
    guard = helper()
    events = []

    class Activity:
        def begin(self):
            events.append("begin")

        def end(self):
            events.append("end")

    monkeypatch.setattr(guard, "_Activity", Activity)
    try:
        with guard.user_activity() as details:
            assert details["user_initiated_activity"]
            assert not details["latency_critical"]
            if fail_in_work:
                raise ValueError("work failed")
    except ValueError:
        assert fail_in_work
    assert events == ["begin", "end"]


def test_activity_begin_failure_still_releases_activity(monkeypatch):
    guard = helper()
    events = []

    class Activity:
        def begin(self):
            raise RuntimeError("no activity token")

        def end(self):
            events.append("end")

    monkeypatch.setattr(guard, "_Activity", Activity)
    with pytest.raises(RuntimeError, match="no activity token"):
        with guard.user_activity():
            pytest.fail("Work ran without an activity token")
    assert events == ["end"]


def test_snapshot_never_runs_docker_or_mutates_preferences(monkeypatch):
    guard = helper()
    commands = []

    def command(arguments):
        commands.append(arguments)
        if arguments[0] == "/bin/ps":
            return ("PID %CPU RSS STATE COMM\n"
                    "42 30.2 1048576 R /system/com.apple.Virtualization.VirtualMachine\n"
                    "43 1.0 10 S /private/unrelated-program")
        if arguments[0] == "/usr/bin/vm_stat":
            return "Swapins: 123.\nSwapouts: 456."
        return "fixture"

    monkeypatch.setattr(guard, "_command", command)
    snapshot = guard.runtime_snapshot()
    assert snapshot["vm_counters"] == {"Swapins": 123, "Swapouts": 456}
    assert snapshot["virtual_machines"] == [{"pid": 42, "cpu_percent": 30.2,
                                            "rss_kib": 1048576, "state": "R"}]
    assert all("docker" not in part for arguments in commands for part in arguments)
    assert [arguments for arguments in commands if "pmset" in arguments[0]] == [
        ["/usr/bin/pmset", "-g", "batt"], ["/usr/bin/pmset", "-g", "therm"]]
