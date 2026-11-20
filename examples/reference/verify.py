"""Сравнить результат программы с деревом и журналом настоящего Maven."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from resolve import dependency_graph
from maven import Maven
from order import load_order
from render import render

CENTRAL = "https://repo.maven.apache.org/maven2"


def collect(node, graph):
    """Преобразовать поддерево Maven JSON в список смежности."""
    key = ":".join(node[k] for k in ("groupId", "artifactId", "version"))
    graph[key] = [collect(child, graph) for child in node.get("children", [])]
    return key


def transfers(folder, graph):
    """Прочитать события завершения загрузки POM и JAR целевых пакетов."""
    names = {}
    for key in graph:
        group, artifact, version = key.split(":")
        path = f"{group.replace('.', '/')}/{artifact}/{version}"
        for ext in ("pom", "jar"):
            names[f"{path}/{artifact}-{version}.{ext}"] = (key, ext)
    events = []
    for line in (folder / "resolve.log").read_text().splitlines():
        url = re.search(r"Downloaded from [^:]+: (https?://\S+)", line)
        if url:
            for suffix, event in names.items():
                if url[1].endswith("/" + suffix):
                    events.append(event)
    return events


def verify(root, folder):
    """Сверить граф и сохранить оба порядка для проверки на защите."""
    reference = {}
    wrapper = json.loads((folder / "tree.json").read_text())
    selected, = wrapper["children"]
    if collect(selected, reference) != root:
        raise ValueError("Неверный корень эталонного поддерева")
    graph = dependency_graph(root, Maven(CENTRAL), 8)
    if {k: set(v) for k, v in graph.items()} != {
            k: set(v) for k, v in reference.items()}:
        raise ValueError(f"Различаются графы: {graph} / {reference}")
    render(graph, folder / "visualizer.png")
    events = transfers(folder, graph)
    order = load_order(graph)
    jars = [name for name, ext in events if ext == "jar"]
    if set(jars) != set(graph):
        raise ValueError(f"Неполный журнал скачивания JAR: {jars}")
    result = [root, "Графы совпали.", "Этап 4: " + " -> ".join(order),
              "Maven JAR: " + " -> ".join(jars),
              "Порядки " + ("совпали." if order == jars else "различаются."),
              "События Maven (в порядке завершения):"]
    result.extend(f"  {ext.upper()} {name}" for name, ext in events)
    output = "\n".join(result) + "\n"
    (folder / "comparison.txt").write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    verify(sys.argv[1], Path(sys.argv[2]))
