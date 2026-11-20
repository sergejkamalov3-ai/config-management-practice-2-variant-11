"""Проверки наследования, длинных цепочек и разрешения зависимостей."""
import sys
import unittest
from pathlib import Path
from xml.etree.ElementTree import fromstring

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import validate_url
from graph import bfs
from maven import Maven
from resolve import dependency_graph


def dependency(name, version="1", extra=""):
    """Сформировать независимый XML-пример зависимости."""
    return ("<dependency><groupId>g</groupId><artifactId>" + name
            + "</artifactId><version>" + version + "</version>"
            + extra + "</dependency>")


def pom(dependencies="", extra=""):
    """Создать документ POM для изолированной проверки."""
    return ("<project>" + extra + "<dependencies>" + dependencies
            + "</dependencies></project>")


def repository(documents):
    """Подставить XML-документы, сохранив настоящий разбор POM."""
    repo = Maven("https://example.org")
    repo.document = lambda name: fromstring(documents[name])
    return repo


class Regressions(unittest.TestCase):
    def test_port_validation(self):
        for url in ("https://example.org:abc", "https://example.org:99999",
                    "https://example.org:", "https://example.org:0",
                    "https://exa mple.org", "https://[bad"):
            with self.subTest(url=url), self.assertRaisesRegex(
                    ValueError, "repository"):
                validate_url(url)
        validate_url("http://localhost:8765/maven")
        validate_url("https://[::1]:443")

    def test_long_graph(self):
        graph = bfs("0", lambda n: [str(int(n) + 1)], 5000)
        self.assertEqual(len(graph), 5001)
        self.assertEqual(graph["4999"], ["5000"])
        self.assertEqual(graph["5000"], [])

    def test_parent_property_override(self):
        parent = "<properties><v>1</v></properties>"
        child = ("<parent><groupId>g</groupId><artifactId>parent</artifactId>"
                 "<version>1</version></parent>"
                 "<properties><v>2</v></properties>")
        repo = repository({
            "g:parent:1": pom(dependency("lib", "${v}"), parent),
            "g:child:1": pom(extra=child),
        })
        self.assertEqual(repo.children("g:child:1"), ["g:lib:2"])
        self.assertEqual(repo.children("g:parent:1"), ["g:lib:1"])

    def test_managed_property_override(self):
        managed = ("<dependencyManagement><dependencies>"
                   + dependency("lib", "${v}")
                   + "</dependencies></dependencyManagement>")
        parent = "<properties><v>1</v></properties>" + managed
        child = ("<parent><groupId>g</groupId><artifactId>parent</artifactId>"
                 "<version>1</version></parent>"
                 "<properties><v>2</v></properties>")
        declaration = dependency("lib").replace("<version>1</version>", "")
        repo = repository({"g:parent:1": pom(extra=parent),
                           "g:child:1": pom(declaration, child)})
        self.assertEqual(repo.children("g:child:1"), ["g:lib:2"])

    def test_nearest_version(self):
        repo = repository({
            "g:root:1": pom(dependency("a") + dependency("lib", "2")),
            "g:a:1": pom(dependency("lib")),
            "g:lib:2": pom(),
        })
        graph = dependency_graph("g:root:1", repo, 10)
        self.assertEqual(graph["g:a:1"], ["g:lib:2"])
        self.assertNotIn("g:lib:1", graph)

    def test_equal_depth_uses_first_declaration(self):
        repo = repository({
            "g:root:1": pom(dependency("a") + dependency("b")),
            "g:a:1": pom(dependency("lib", "2")),
            "g:b:1": pom(dependency("lib", "3")),
            "g:lib:2": pom(),
        })
        graph = dependency_graph("g:root:1", repo, 10)
        self.assertEqual(graph["g:b:1"], ["g:lib:2"])

    def test_exclusions_apply_to_the_path(self):
        excludes = ("<exclusions><exclusion><groupId>g</groupId>"
                    "<artifactId>lib</artifactId></exclusion></exclusions>")
        repo = repository({
            "g:root:1": pom(dependency("a", extra=excludes)
                            + dependency("b")),
            "g:a:1": pom(dependency("lib")),
            "g:b:1": pom(dependency("a")),
            "g:lib:1": pom(),
        })
        graph = dependency_graph("g:root:1", repo, 10)
        self.assertEqual(graph["g:a:1"], ["g:lib:1"])
        isolated = dependency_graph("g:root:1", repo, 2)
        self.assertNotIn("g:lib:1", isolated)

    def test_maven_cycle(self):
        repo = repository({"g:a:1": pom(dependency("b")),
                           "g:b:1": pom(dependency("a"))})
        graph = dependency_graph("g:a:1", repo, 5000)
        self.assertEqual(graph, {"g:a:1": ["g:b:1"], "g:b:1": ["g:a:1"]})

    def test_bom_cycle(self):
        def importing(name):
            return pom(extra="<dependencyManagement><dependencies>"
                       + dependency(name, extra="<type>pom</type>"
                                    "<scope>import</scope>")
                       + "</dependencies></dependencyManagement>")
        repo = repository({"g:a:1": importing("b"),
                           "g:b:1": importing("a")})
        with self.assertRaisesRegex(ValueError, "Цикл импортов"):
            repo.children("g:a:1")
