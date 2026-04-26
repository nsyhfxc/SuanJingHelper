from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time


@dataclass(frozen=True)
class StressConfig:
    solution_path: Path
    standard_path: Path
    generator_path: Path
    output_dir: Path
    max_cases: int = 1000
    timeout_seconds: float = 3.0
    normalize_output: bool = True


class StressRunner:
    def __init__(self, config: StressConfig, log_callback) -> None:
        self.config = config
        self.log_callback = log_callback
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        self.config.output_dir.mkdir(exist_ok=True)
        build_dir = self.config.output_dir / ".build"
        build_dir.mkdir(exist_ok=True)

        started_at = time.strftime("%H:%M:%S")
        self._log("info", f">>> 对拍开始 {started_at}")

        try:
            cmd_gen = self._prepare_command(self.config.generator_path, "gen", build_dir)
            cmd_std = self._prepare_command(self.config.standard_path, "std", build_dir)
            cmd_sol = self._prepare_command(self.config.solution_path, "sol", build_dir)
        except RuntimeError as exc:
            self._log("error", f"准备失败：{exc}")
            return

        case_no = 1
        passed = 0
        while not self.stop_event.is_set():
            if self.config.max_cases > 0 and case_no > self.config.max_cases:
                self._log("success", f">>> 已完成 {passed} 组测试，未发现差异")
                return

            try:
                input_data = ""
                start = time.perf_counter()
                input_data = self._run_program(cmd_gen, None, "数据生成器")
                out_std = self._run_program(cmd_std, input_data, "标准程序")
                out_sol = self._run_program(cmd_sol, input_data, "待测程序")
                elapsed_ms = (time.perf_counter() - start) * 1000
            except subprocess.TimeoutExpired as exc:
                self._save_failure(input_data=input_data, std_output="", sol_output="")
                self._log("error", f"#{case_no} TLE：{exc.cmd}")
                return
            except RuntimeError as exc:
                self._log("error", f"#{case_no} 运行错误：{exc}")
                return

            left = _normalize_output(out_std) if self.config.normalize_output else out_std
            right = _normalize_output(out_sol) if self.config.normalize_output else out_sol

            if left == right:
                passed += 1
                self._log("success", f"#{case_no} PASS ({elapsed_ms:.0f} ms)")
                case_no += 1
                continue

            self._save_failure(input_data, out_std, out_sol)
            self._log("error", f"#{case_no} WA：标准输出与待测输出不一致")
            self._log("info", "失败现场已保存到 workspace/error.in、std.out、sol.out")
            return

        self._log("info", f">>> 已手动停止，共通过 {passed} 组")

    def _prepare_command(self, path: Path, role: str, build_dir: Path) -> list[str]:
        path = path.expanduser().resolve()
        if not path.exists():
            raise RuntimeError(f"{path} 不存在")

        suffix = path.suffix.lower()
        if suffix == ".cpp":
            compiler = shutil.which("g++")
            if not compiler:
                raise RuntimeError("未找到 g++，无法编译 C++ 文件")
            exe = build_dir / f"{role}.exe"
            result = subprocess.run(
                [compiler, str(path), "-o", str(exe), "-O2", "-std=c++17"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"{path.name} 编译失败：{result.stderr.strip()}")
            self._log("info", f"已编译 {path.name}")
            return [str(exe)]

        if suffix == ".py":
            if getattr(sys, "frozen", False):
                return [sys.executable, "--run-python-script", str(path)]
            return [sys.executable, str(path)]

        return [str(path)]

    def _run_program(self, command: list[str], input_text: str | None, label: str) -> str:
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or f"退出码 {result.returncode}"
            raise RuntimeError(f"{label}失败：{detail}")
        return result.stdout

    def _save_failure(self, input_data: str, std_output: str, sol_output: str) -> None:
        self.config.output_dir.mkdir(exist_ok=True)
        (self.config.output_dir / "error.in").write_text(input_data, encoding="utf-8")
        (self.config.output_dir / "std.out").write_text(std_output, encoding="utf-8")
        (self.config.output_dir / "sol.out").write_text(sol_output, encoding="utf-8")

    def _log(self, level: str, message: str) -> None:
        self.log_callback(level, message)


def _normalize_output(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines())
