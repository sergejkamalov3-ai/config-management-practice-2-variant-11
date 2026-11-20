"""Чтение POM по HTTP стандартными средствами Python."""
import re
from functools import lru_cache
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from config import PART
from pom import expand, key, merge, raw_model

CENTRAL = "https://repo.maven.apache.org/maven2"


class Maven:
    """Загрузка POM с наследованием, свойствами и импортами BOM."""

    def __init__(self, repository, *, all_direct=False):
        self.all_direct = all_direct
        self.base = repository.rstrip("/")
        self.active = set()

    def document(self, name):
        """Получить POM точной версии и убрать XML-пространство имён."""
        group, artifact, version = name.split(":")
        if not all(re.fullmatch(PART, x) for x in name.split(":")):
            raise ValueError(f"Нужна фиксированная координата Maven: {name}")
        folder = f"{group.replace('.', '/')}/{artifact}/{version}"
        url = f"{self.base}/{folder}/{artifact}-{version}.pom"
        try:
            with urlopen(url, timeout=15) as stream:
                root = ET.parse(stream).getroot()
        except (OSError, ET.ParseError) as error:
            raise ValueError(f"Ошибка чтения {url}: {error}") from error
        for tag in root.iter():
            tag.tag = tag.tag.split("}")[-1]
        return root

    @lru_cache(maxsize=None)
    def raw(self, name):
        """Собрать цепочку родителей до интерполяции зависимостей."""
        root = self.document(name)
        marker = ("parent", name)
        if marker in self.active:
            raise ValueError(f"Цикл родительских POM: {name}")
        self.active.add(marker)
        try:
            parent = ({}, [], [])
            node = root.find("parent")
            if node is not None:
                props = raw_model(root, parent)[0]
                coord = ":".join(expand(node.findtext(k, ""), props)
                                 for k in ("groupId", "artifactId", "version"))
                parent = self.raw(coord)
            return raw_model(root, parent)
        finally:
            self.active.remove(marker)

    @lru_cache(maxsize=None)
    def model(self, name):
        """Разрешить свойства в контексте дочернего проекта."""
        marker = ("bom", name)
        if marker in self.active:
            raise ValueError(f"Цикл импортов BOM: {name}")
        self.active.add(marker)
        try:
            props, layers, dependencies = self.raw(name)
            props = dict(props)
            for field, value in zip(("groupId", "artifactId", "version"),
                                    name.split(":")):
                props[f"project.{field}"] = value
                props[f"pom.{field}"] = value
            managed = self.management(layers, props)
            deps = merge(dependencies, props)
            result = []
            for ident, item in deps.items():
                result.append(dict(managed.get(ident, {}), **item))
            return props, managed, result
        finally:
            self.active.remove(marker)

    def management(self, layers, props):
        """Прямые managed-объявления имеют приоритет над импортами."""
        declared = merge(layers, props)
        result = {k: v for k, v in declared.items()
                  if v.get("scope") != "import"}
        for item in declared.values():
            if item.get("scope") == "import":
                if item.get("type") != "pom":
                    raise ValueError("Импорт BOM должен иметь type=pom")
                imported = self.model(coordinate(item))[1]
                for ident, value in imported.items():
                    result.setdefault(ident, value)
        return result

    def children(self, name):
        """Выдать все прямые объявления или обязательные runtime-связи."""
        result = []
        for item in self.model(name)[2]:
            if self.all_direct:
                details = [item.get("scope", "compile"),
                           item.get("type", "jar")]
                details.extend(filter(None, [item.get("classifier")]))
                if item.get("optional") == "true":
                    details.append("optional")
                result.append(f"{coordinate(item)} ({', '.join(details)})")
            elif runtime(item):
                result.append(coordinate(item))
        return result


def runtime(item):
    """Зависимости, которые передаются потребителю пакета."""
    return (item.get("scope", "compile") in ("compile", "runtime")
            and item.get("optional", "false") != "true")


def coordinate(item):
    """Потребовать фиксированную версию с понятной диагностикой."""
    fields = [item.get(k, "") for k in ("groupId", "artifactId", "version")]
    if not all(re.fullmatch(PART, value) for value in fields):
        raise ValueError("Нужна фиксированная координата Maven: "
                         + ":".join(fields))
    if key(item)[2:] != ("jar", ""):
        if item.get("type") != "pom" or item.get("classifier"):
            raise ValueError("Тип или classifier пока не поддерживается: "
                             + str(key(item)))
    return ":".join(fields)
