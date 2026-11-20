"""Вывод двух представлений одного ориентированного графа."""
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def render(graph, output):
    """Записать Mermaid и отрисовать те же узлы и рёбра в PNG."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    ids = {name: f"n{i}" for i, name in enumerate(graph)}
    mermaid = ["flowchart TD"]
    dot = ['digraph G {', 'bgcolor="white";', 'rankdir=TB;',
           'node [shape=box,style="rounded,filled",fillcolor="#e6f1fa"];']
    for name, node in ids.items():
        label = json.dumps(name)
        mermaid.append(f"    {node}[{label}]")
        dot.append(f"{node} [label={label}];")
    for name, edges in graph.items():
        for child in edges:
            mermaid.append(f"    {ids[name]} --> {ids[child]}")
            dot.append(f"{ids[name]} -> {ids[child]};")
    dot.append("}")
    with TemporaryDirectory(dir=path.parent) as folder:
        image = Path(folder) / "graph.png"
        try:
            result = subprocess.run(["dot", "-Tpng", "-o", str(image)],
                                    input="\n".join(dot), text=True,
                                    capture_output=True, check=False)
        except FileNotFoundError as error:
            raise ValueError("Для записи PNG установите Graphviz") from error
        if result.returncode:
            raise ValueError("Graphviz: " + result.stderr.strip())
        source = Path(folder) / "graph.mmd"
        source.write_text("\n".join(mermaid) + "\n", encoding="utf-8")
        source.replace(path.with_suffix(".mmd"))
        image.replace(path)
