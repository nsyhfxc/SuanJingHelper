from __future__ import annotations

import json
from pathlib import Path

from .config import LEGACY_TEMPLATE_PATH, TEMPLATE_PATH

DEFAULT_TEMPLATES = {
    "快读快写 (Python)": "import sys\ninput = lambda: sys.stdin.readline().rstrip()\n# write = sys.stdout.write\n",
    "并查集 (DSU)": (
        "class DSU:\n"
        "    def __init__(self, n):\n"
        "        self.parent = list(range(n + 1))\n"
        "        self.size = [1] * (n + 1)\n"
        "\n"
        "    def find(self, x):\n"
        "        while self.parent[x] != x:\n"
        "            self.parent[x] = self.parent[self.parent[x]]\n"
        "            x = self.parent[x]\n"
        "        return x\n"
        "\n"
        "    def union(self, a, b):\n"
        "        ra, rb = self.find(a), self.find(b)\n"
        "        if ra == rb:\n"
        "            return False\n"
        "        if self.size[ra] < self.size[rb]:\n"
        "            ra, rb = rb, ra\n"
        "        self.parent[rb] = ra\n"
        "        self.size[ra] += self.size[rb]\n"
        "        return True\n"
    ),
    "Dijkstra (Python)": (
        "from heapq import heappop, heappush\n"
        "\n"
        "def dijkstra(graph, start):\n"
        "    dist = [10**30] * len(graph)\n"
        "    dist[start] = 0\n"
        "    heap = [(0, start)]\n"
        "    while heap:\n"
        "        d, u = heappop(heap)\n"
        "        if d != dist[u]:\n"
        "            continue\n"
        "        for v, w in graph[u]:\n"
        "            nd = d + w\n"
        "            if nd < dist[v]:\n"
        "                dist[v] = nd\n"
        "                heappush(heap, (nd, v))\n"
        "    return dist\n"
    ),
}


class TemplateStore:
    def __init__(self, path: Path = TEMPLATE_PATH) -> None:
        self.path = path

    def load(self) -> dict[str, str]:
        for candidate in (self.path, LEGACY_TEMPLATE_PATH):
            if not candidate.exists():
                continue
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                templates = DEFAULT_TEMPLATES.copy()
                templates.update({str(k): str(v) for k, v in data.items()})
                return templates or DEFAULT_TEMPLATES.copy()
        return DEFAULT_TEMPLATES.copy()

    def save(self, templates: dict[str, str]) -> None:
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(
            json.dumps(templates, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )


def unique_template_name(existing: dict[str, str], base: str = "新模板") -> str:
    if base not in existing:
        return base
    index = 2
    while f"{base}_{index}" in existing:
        index += 1
    return f"{base}_{index}"
