"""Слияние объявлений POM до подстановки свойств дочернего проекта."""
import re
from copy import deepcopy

FIELDS = ("groupId", "artifactId", "version", "type", "classifier",
          "scope", "optional")


def expand(value, properties):
    """Раскрыть вложенные свойства с диагностикой циклов."""
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

        updated = re.sub(r"\$\{([^}]+)\}", replace, value)
        if updated == value:
            raise ValueError(f"Некорректное свойство POM: {value}")
        value = updated
    return value


def declarations(root, path):
    """Прочитать поля и исключения без преждевременной интерполяции."""
    result = []
    for node in root.findall(path):
        item = {key: node.findtext(key) for key in FIELDS
                if node.find(key) is not None}
        item["exclusions"] = [
            (n.findtext("groupId", ""), n.findtext("artifactId", ""))
            for n in node.findall("exclusions/exclusion")
        ]
        result.append(item)
    return result


def interpolate(item, props):
    """Подставить свойства окончательной модели в объявление."""
    result = {k: expand(v, props) for k, v in item.items()
              if k != "exclusions"}
    result["exclusions"] = tuple(
        (expand(g, props), expand(a, props)) for g, a in item["exclusions"])
    return result


def key(item):
    """Ключ Maven для слияния деклараций и выбора версии."""
    return (item.get("groupId", ""), item.get("artifactId", ""),
            item.get("type", "jar"), item.get("classifier", ""))


def merge(layers, props):
    """Дочерние поля замещают родительские, остальные наследуются."""
    result = {}
    for layer in layers:
        local = {}
        for declaration in layer:
            item = interpolate(declaration, props)
            ident = key(item)
            inherited = result.get(ident, {})
            combined = dict(inherited, **item)
            combined["exclusions"] = tuple(dict.fromkeys(
                inherited.get("exclusions", ()) + item["exclusions"]))
            local[ident] = combined
        result = {**local, **{k: v for k, v in result.items()
                             if k not in local}}
    return result


def raw_model(root, parent):
    """Сохранить свойства и слои зависимостей родительской модели."""
    props, managed, deps = deepcopy(parent)
    props.update({p.tag: (p.text or "").strip()
                  for p in root.findall("properties/*")})
    managed.append(declarations(
        root, "dependencyManagement/dependencies/dependency"))
    deps.append(declarations(root, "dependencies/dependency"))
    return props, managed, deps
