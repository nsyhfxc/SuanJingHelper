from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiffOptions:
    ignore_trailing_space: bool = False
    ignore_blank_lines: bool = False
    ignore_case: bool = False


@dataclass(frozen=True)
class DiffResult:
    diff_count: int
    left_lines: tuple[int, ...]
    right_lines: tuple[int, ...]

    @property
    def is_equal(self) -> bool:
        return self.diff_count == 0

    @property
    def first_left_line(self) -> int | None:
        return self.left_lines[0] if self.left_lines else None

    @property
    def first_right_line(self) -> int | None:
        return self.right_lines[0] if self.right_lines else None


def compare_texts(left_text: str, right_text: str, options: DiffOptions) -> DiffResult:
    left = _prepare_lines(left_text, options)
    right = _prepare_lines(right_text, options)
    max_len = max(len(left), len(right))
    left_diff: set[int] = set()
    right_diff: set[int] = set()
    diff_count = 0

    for index in range(max_len):
        left_item = left[index] if index < len(left) else None
        right_item = right[index] if index < len(right) else None
        left_value = left_item[1] if left_item else None
        right_value = right_item[1] if right_item else None

        if left_value == right_value:
            continue

        diff_count += 1
        if left_item:
            left_diff.add(left_item[0])
        if right_item:
            right_diff.add(right_item[0])

    return DiffResult(diff_count, tuple(sorted(left_diff)), tuple(sorted(right_diff)))


def _prepare_lines(text: str, options: DiffOptions) -> list[tuple[int, str]]:
    prepared: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        value = line.rstrip() if options.ignore_trailing_space else line
        if options.ignore_case:
            value = value.lower()
        if options.ignore_blank_lines and value.strip() == "":
            continue
        prepared.append((line_no, value))
    return prepared
