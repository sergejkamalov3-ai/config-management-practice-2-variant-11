"""Построение графа по уровням и чтение учебного репозитория."""
import re
from pathlib import Path

import yaml

from levels import walk_levels


def test_repository(path):
    """Проверить и прочитать списки смежности для пакетов A–Z."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Репозиторий должен содержать словарь")
    for key, nodes in data.items():
        if not isinstance(key, str) or not re.fullmatch("[A-Z]+", key):
            raise ValueError(f"Недопустимое имя пакета: {key}")
        if not isinstance(nodes, list) or not all(
                isinstance(n, str) and n in data for n in nodes):
            raise ValueError(f"Некорректные зависимости пакета {key}")

    def children(key):
        if key not in data:
            raise ValueError(f"В репозитории нет пакета {key}")
        return data[key]

    return children


def bfs(root, children, limit):
    """Обойти уровни BFS рекурсивно, сохраняя все обнаруженные рёбра."""
    graph = {root: []}

    def level(frontier, depth):
        following = []
        for node in frontier:
            graph[node] = list(dict.fromkeys(children(node)))
            for child in graph[node]:
                if child not in graph:
                    graph[child] = []
                    following.append(child)
        return following

    walk_levels([root], limit, level)
    return graph
