"""Точка входа визуализатора."""
import argparse
import sys

import yaml

from config import load
from graph import bfs, test_repository
from maven import Maven


def run(cfg):
    """Выбрать источник данных и построить граф."""
    root = cfg["package"]
    if cfg["test_mode"]:
        children = test_repository(cfg["repository"])
        children(root)
    else:
        root += ":" + cfg["version"]
        children = Maven(cfg["repository"]).children
    graph = bfs(root, children, cfg["max_depth"])
    for node, edges in graph.items():
        print(node, "->", ", ".join(edges))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="путь к YAML")
    try:
        run(load(parser.parse_args().config))
    except (ValueError, OSError, yaml.YAMLError) as error:
        sys.exit(f"Ошибка: {error}")
