"""Process-scoped activity protection and read-only telemetry for local recovery.

This helper does not change model, decoder, environment, or system preferences.
The activity token belongs to the collector process and ends when work exits.
"""

import ctypes
import os
import platform
import re
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone

# Values from the installed Apple SDK's Foundation/NSProcessInfo.h. No
# latency-critical or user-interactive scheduling is requested.
USER_INITIATED = 0x00FFFFFF


class _Activity:
    def __init__(self):
        if platform.system() != "Darwin":
            raise RuntimeError("The frozen local recovery requires macOS")
        self.foundation = ctypes.CDLL(
            "/System/Library/Frameworks/Foundation.framework/Foundation"
        )
        self.objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        self.objc.objc_getClass.argtypes = [ctypes.c_char_p]
        self.objc.objc_getClass.restype = ctypes.c_void_p
        self.objc.sel_registerName.argtypes = [ctypes.c_char_p]
        self.objc.sel_registerName.restype = ctypes.c_void_p
        self.address = ctypes.cast(self.objc.objc_msgSend, ctypes.c_void_p).value
        self.pool = self.send(self.objc.objc_getClass(b"NSAutoreleasePool"), b"new")
        self.process = self.send(self.objc.objc_getClass(b"NSProcessInfo"), b"processInfo")
        self.reason = self.send(self.objc.objc_getClass(b"NSString"), b"alloc")
        self.reason = self.send(
            self.reason, b"initWithUTF8String:",
            (ctypes.c_char_p,), (b"User-requested bounded frozen research collection",),
        )
        self.token = None

    def send(self, receiver, name, argument_types=(), values=(), return_type=ctypes.c_void_p):
        # Typed ABI is necessary for objc_msgSend on Apple silicon.
        function = ctypes.CFUNCTYPE(
            return_type, ctypes.c_void_p, ctypes.c_void_p, *argument_types
        )(self.address)
        return function(receiver, self.objc.sel_registerName(name), *values)

    def begin(self):
        self.token = self.send(
            self.process, b"beginActivityWithOptions:reason:",
            (ctypes.c_uint64, ctypes.c_void_p), (USER_INITIATED, self.reason),
        )
        if not self.token:
            raise RuntimeError("macOS did not return a user-initiated activity token")
        self.send(self.token, b"retain")

    def end(self):
        if self.token:
            self.send(self.process, b"endActivity:", (ctypes.c_void_p,), (self.token,), None)
            self.send(self.token, b"release", return_type=None)
            self.token = None
        self.send(self.reason, b"release", return_type=None)
        self.send(self.pool, b"drain", return_type=None)


@contextmanager
def user_activity():
    """Mark this finite, explicitly requested collection as active macOS work."""
    activity = _Activity()
    try:
        activity.begin()
        yield {"pid": os.getpid(), "activity_options": USER_INITIATED,
               "user_initiated_activity": True, "latency_critical": False}
    finally:
        activity.end()


def _command(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=5,
                                env=dict(os.environ, LC_ALL="C"))
        if result.returncode:
            return {"unavailable": result.stderr.strip() or result.stdout.strip()}
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"unavailable": type(error).__name__}


def runtime_snapshot():
    """Sample host conditions without touching Docker APIs or changing settings."""
    vm = _command(["/usr/bin/vm_stat"])
    counters = ({key: int(value) for key, value in
                 re.findall(r"^([^:\n]+):\s+(\d+)\.", vm, re.M)}
                if isinstance(vm, str) else vm)
    process_text = _command(["/bin/ps", "-axo", "pid,pcpu,rss,state,comm"])
    virtual_machines = []
    if isinstance(process_text, str):
        for line in process_text.splitlines()[1:]:
            parts = line.split(None, 4)
            if len(parts) == 5 and parts[-1].endswith("com.apple.Virtualization.VirtualMachine"):
                virtual_machines.append({"pid": int(parts[0]), "cpu_percent": float(parts[1]),
                                         "rss_kib": int(parts[2]), "state": parts[3]})
    return {
        "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(), "memory_pressure": _command(["/usr/bin/memory_pressure", "-Q"]),
        "swap_usage": _command(["/usr/sbin/sysctl", "vm.swapusage"]),
        "vm_counters": counters, "power": _command(["/usr/bin/pmset", "-g", "batt"]),
        "thermal": _command(["/usr/bin/pmset", "-g", "therm"]),
        "virtual_machines": virtual_machines,
        "process_inventory_available": isinstance(process_text, str),
    }
