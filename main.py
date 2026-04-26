from __future__ import annotations

import os
import runpy
import sys


def _open_standard_stream(handle_id: int, mode: str):
    if os.name != "nt":
        return open(os.devnull, mode, encoding="utf-8")

    import ctypes
    import msvcrt

    handle = ctypes.windll.kernel32.GetStdHandle(handle_id)
    invalid_handle = ctypes.c_void_p(-1).value
    if handle in (0, invalid_handle):
        return open(os.devnull, mode, encoding="utf-8")

    access = os.O_RDONLY if "r" in mode else os.O_WRONLY
    fd = msvcrt.open_osfhandle(handle, os.O_TEXT | access)
    return os.fdopen(fd, mode, encoding="utf-8", errors="replace", buffering=1)


def _restore_standard_streams() -> None:
    if sys.stdin is None:
        sys.stdin = _open_standard_stream(-10, "r")
    if sys.stdout is None:
        sys.stdout = _open_standard_stream(-11, "w")
    if sys.stderr is None:
        sys.stderr = _open_standard_stream(-12, "w")


def _run_python_script() -> None:
    _restore_standard_streams()
    script_path = sys.argv[2]
    sys.argv = sys.argv[2:]
    script_dir = os.path.dirname(os.path.abspath(script_path))
    if script_dir and script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    runpy.run_path(script_path, run_name="__main__")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-python-script":
        _run_python_script()
    else:
        from cp_toolkit import CPToolkit

        CPToolkit().mainloop()
