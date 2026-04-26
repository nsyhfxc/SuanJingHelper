from __future__ import annotations

from dataclasses import dataclass
import random
import string

DATA_TYPES = [
    "整数数列",
    "随机排列",
    "矩阵/网格",
    "随机字符串",
    "简单图",
    "带权图",
    "普通树",
    "二叉树",
]


@dataclass(frozen=True)
class GenerateOptions:
    data_type: str
    cases: int
    min_size: int
    max_size: int
    min_value: int
    max_value: int
    min_weight: int
    max_weight: int
    include_case_count: bool = True
    seed: str = ""


def generate_data(options: GenerateOptions) -> str:
    validate_options(options)
    rng = random.Random(options.seed if options.seed else None)
    lines: list[str] = []

    if options.include_case_count:
        lines.append(str(options.cases))

    for _ in range(options.cases):
        lines.extend(_generate_case(options, rng))

    return "\n".join(lines)


def validate_options(options: GenerateOptions) -> None:
    if options.data_type not in DATA_TYPES:
        raise ValueError("未知的数据类型")
    if options.cases <= 0:
        raise ValueError("组数必须大于 0")
    if options.min_size <= 0 or options.max_size <= 0:
        raise ValueError("规模范围必须大于 0")
    if options.min_size > options.max_size:
        raise ValueError("规模下限不能大于上限")
    if options.min_value > options.max_value:
        raise ValueError("数值下限不能大于上限")
    if options.min_weight > options.max_weight:
        raise ValueError("权值下限不能大于上限")


def _generate_case(options: GenerateOptions, rng: random.Random) -> list[str]:
    kind = options.data_type
    n = rng.randint(options.min_size, options.max_size)

    if kind == "整数数列":
        return [
            str(n),
            " ".join(str(rng.randint(options.min_value, options.max_value)) for _ in range(n)),
        ]

    if kind == "随机排列":
        values = list(range(1, n + 1))
        rng.shuffle(values)
        return [str(n), " ".join(map(str, values))]

    if kind == "矩阵/网格":
        rows = rng.randint(options.min_size, options.max_size)
        cols = rng.randint(options.min_size, options.max_size)
        lines = [f"{rows} {cols}"]
        for _ in range(rows):
            lines.append(" ".join(str(rng.randint(options.min_value, options.max_value)) for _ in range(cols)))
        return lines

    if kind == "随机字符串":
        return ["".join(rng.choices(string.ascii_lowercase, k=n))]

    if kind in {"简单图", "带权图"}:
        max_edges = n * (n - 1) // 2
        if max_edges == 0:
            edge_count = 0
        else:
            edge_count = rng.randint(max(0, n - 1), min(max_edges, n + 5))
        edges = _random_edges(n, edge_count, rng)
        lines = [f"{n} {len(edges)}"]
        for u, v in edges:
            if kind == "带权图":
                lines.append(f"{u} {v} {rng.randint(options.min_weight, options.max_weight)}")
            else:
                lines.append(f"{u} {v}")
        return lines

    if kind in {"普通树", "二叉树"}:
        edges = []
        for child in range(2, n + 1):
            parent = child // 2 if kind == "二叉树" else rng.randint(1, child - 1)
            edges.append((parent, child))
        lines = [f"{n} {len(edges)}"]
        lines.extend(f"{u} {v}" for u, v in edges)
        return lines

    raise ValueError("未知的数据类型")


def _random_edges(n: int, edge_count: int, rng: random.Random) -> list[tuple[int, int]]:
    if n < 2 or edge_count <= 0:
        return []

    edge_set: set[tuple[int, int]] = set()
    while len(edge_set) < edge_count:
        u, v = rng.sample(range(1, n + 1), 2)
        edge_set.add((u, v) if u < v else (v, u))

    edges = list(edge_set)
    rng.shuffle(edges)
    return edges
