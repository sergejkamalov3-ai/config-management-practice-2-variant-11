"""Чтение POM по HTTP стандартными средствами Python."""
import re
from functools import lru_cache
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from config import PART


def expand(value, properties):
    """Раскрыть переменные POM и диагностировать циклические ссылки."""
    seen = set()
    while "${" in value:
        if value in seen:
            raise ValueError(f"Цикл свойств POM: {value}")
        seen.add(value)

        def replace(match):
            name = match[1]
            if name not in properties:
                raise ValueError(f"Неизвестное свойство POM: {name}")
            return properties[name]

        value = re.sub(r"\$\{([^}]+)\}", replace, value)
    return value


class Maven:
    """Загрузка и кэширование метаданных выбранного репозитория."""

    def __init__(self, repository, *, all_direct=False):
        self.all_direct = all_direct
        self.base = repository.rstrip("/")
        self.active = set()

    def document(self, name):
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
    def model(self, name):
        if name in self.active:
            raise ValueError(f"Цикл родительских POM/BOM: {name}")
        self.active.add(name)
        try:
            return self.read_model(name)
        finally:
            self.active.remove(name)

    def read_model(self, name):
        root = self.document(name)
        props, managed, deps = {}, {}, {}
        parent = root.find("parent")
        if parent is not None:
            coord = ":".join(parent.findtext(k, "") for k in
                             ("groupId", "artifactId", "version"))
            props, managed, deps = (d.copy() for d in self.model(coord))
        for key, value in zip(("groupId", "artifactId", "version"),
                              name.split(":")):
            for prefix in ("project", "pom"):
                props[f"{prefix}.{key}"] = value
        props.update({p.tag: (p.text or "").strip()
                      for p in root.findall("properties/*")})
        section = "dependencyManagement/dependencies/dependency"
        for dep in root.findall(section):
            key, ver = coordinate(dep, props, managed)
            if dep.findtext("scope") == "import":
                for k, v in self.model(f"{key}:{ver}")[1].items():
                    managed.setdefault(k, v)
            else:
                managed[key] = ver
        for dep in root.findall("dependencies/dependency"):
            scope = expand(dep.findtext("scope", "compile"), props)
            optional = expand(dep.findtext("optional", "false"), props)
            key, ver = coordinate(dep, props, managed)
            kind = dep.findtext("type", "jar")
            classifier = dep.findtext("classifier", "")
            deps[key, kind, classifier] = (ver, scope, optional)
        return props, managed, deps

    def children(self, name):
        """Вернуть прямые зависимости в порядке объявления в POM."""
        result = []
        for (key, kind, classifier), fields in self.model(name)[2].items():
            version, scope, optional = fields
            if self.all_direct:
                details = [scope, kind]
                if classifier:
                    details.append(classifier)
                if optional == "true":
                    details.append("optional")
                result.append(f"{key}:{version} ({', '.join(details)})")
            elif scope in ("compile", "runtime") and optional != "true":
                result.append(f"{key}:{version}")
        return result


def coordinate(dep, props, managed):
    """Получить версию из объявления или dependencyManagement."""
    key = ":".join(expand(dep.findtext(k, ""), props)
                   for k in ("groupId", "artifactId"))
    version = expand(dep.findtext("version", managed.get(key, "")), props)
    if not version:
        raise ValueError(f"Не определена версия зависимости {key}")
    return key, version
