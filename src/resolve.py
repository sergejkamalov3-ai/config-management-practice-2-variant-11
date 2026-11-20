"""Рекурсивный BFS с исключениями и выбором ближайшей версии Maven."""
from levels import walk_levels
from maven import coordinate, runtime
from pom import key


def excluded(item, rules):
    """Проверить groupId/artifactId и шаблон * из exclusions."""
    return any(g in ("*", item["groupId"])
               and a in ("*", item["artifactId"]) for g, a in rules)


def dependency_graph(root, repository, limit):
    """Первое обнаружение в BFS выбирает ближайшую версию пакета."""
    graph = {root: []}
    group, artifact, version = root.split(":")
    selected = {(group, artifact, "jar", ""): root}
    visited = {(root, frozenset())}

    def expand(frontier, depth):
        following = []
        for name, exclusions in frontier:
            for item in repository.model(name)[2]:
                if not runtime(item) or excluded(item, exclusions):
                    continue
                ident = key(item)
                candidate = coordinate(item)
                chosen = selected.setdefault(ident, candidate)
                if chosen not in graph[name]:
                    graph[name].append(chosen)
                graph.setdefault(chosen, [])
                rules = exclusions | frozenset(item.get("exclusions", ()))
                state = (chosen, rules)
                if state not in visited:
                    visited.add(state)
                    following.append(state)
        return following

    walk_levels([(root, frozenset())], limit, expand)
    return graph
