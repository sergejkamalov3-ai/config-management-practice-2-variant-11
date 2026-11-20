"""Сверка исправлений с Maven на локальном HTTP-репозитории."""
import json
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from maven import Maven
from resolve import dependency_graph
from test_regressions import dependency, pom


def fixtures():
    """Пары наследования, конфликта и исключения с ожидаемыми узлами."""
    parent_ref = ("<parent><groupId>g</groupId><artifactId>parent</artifactId>"
                  "<version>1</version></parent>")
    exclusion = ("<exclusions><exclusion><groupId>g</groupId>"
                 "<artifactId>lib</artifactId></exclusion></exclusions>")
    docs = {
        "g:parent:1": pom(dependency("lib", "${v}"),
                          "<properties><v>1</v></properties>"),
        "g:child:1": pom(extra=parent_ref
                         + "<properties><v>2</v></properties>"),
        "g:conflict:1": pom(dependency("a") + dependency("lib", "2")),
        "g:excluded:1": pom(dependency("a", extra=exclusion)),
        "g:a:1": pom(dependency("lib")),
        "g:lib:1": pom(),
        "g:lib:2": pom(),
    }
    return docs


def write_repository(directory, docs):
    """Записать валидные POM и минимальные JAR для Maven."""
    for coordinate, xml in docs.items():
        group, artifact, version = coordinate.split(":")
        root = ET.fromstring(xml)
        for tag, value in (("modelVersion", "4.0.0"), ("groupId", group),
                           ("artifactId", artifact), ("version", version)):
            ET.SubElement(root, tag).text = value
        if artifact == "parent":
            ET.SubElement(root, "packaging").text = "pom"
        folder = directory / group / artifact / version
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{artifact}-{version}"
        ET.ElementTree(root).write(folder / (name + ".pom"))
        with ZipFile(folder / (name + ".jar"), "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")


def node_set(node):
    """Собрать выбранные Maven версии из дерева без omitted-узлов."""
    result = {":".join(node[k] for k in ("groupId", "artifactId", "version"))}
    for child in node.get("children", []):
        result.update(node_set(child))
    return result


def compare(name, repo, output):
    """Запустить штатный dependency:tree и проверить выбранные версии."""
    folder = output / name
    folder.mkdir(parents=True, exist_ok=True)
    xml = pom(dependency(name), "<modelVersion>4.0.0</modelVersion>"
              "<groupId>check</groupId><artifactId>wrapper</artifactId>"
              "<version>1</version><repositories><repository>"
              "<id>fixture</id><url>" + repo.base + "</url>"
              "</repository></repositories>")
    project = folder / "pom.xml"
    project.write_text(xml)
    tree = folder / "tree.json"
    cmd = ["mvn", "-B", "-ntp", "-f", str(project),
           "-Dmaven.repo.local=" + str(output / "cache"),
           "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree",
           "-Dscope=runtime", "-DoutputType=json", "-DoutputFile=" + str(tree)]
    result = subprocess.run(cmd, text=True, capture_output=True)
    (folder / "maven.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout[-3000:] + result.stderr[-1000:])
    root = f"g:{name}:1"
    actual = set(dependency_graph(root, repo, 8))
    expected = node_set(json.loads(tree.read_text())["children"][0])
    if actual != expected:
        raise AssertionError(f"{name}: {actual} != Maven {expected}")
    print(name, "совпадает с Maven:", sorted(actual), flush=True)


def main():
    """Запустить три сравнительных сценария без внешних учебных артефактов."""
    output = ROOT / "build/reference/regressions"
    repository_dir = output / "repository"
    write_repository(repository_dir, fixtures())
    handler = partial(SimpleHTTPRequestHandler, directory=str(repository_dir))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            repo = Maven(f"http://127.0.0.1:{server.server_port}")
            for name in ("child", "conflict", "excluded"):
                compare(name, repo, output)
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
