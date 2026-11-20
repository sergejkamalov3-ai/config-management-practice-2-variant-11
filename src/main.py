"""Точка входа визуализатора."""
import argparse
import sys

import yaml

from config import load
from maven import Maven


def run(cfg):
    """Напечатать прямые зависимости пакета."""
    name = f"{cfg['package']}:{cfg['version']}"
    print(*Maven(cfg["repository"]).children(name), sep="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="путь к YAML")
    try:
        run(load(parser.parse_args().config))
    except (ValueError, OSError, yaml.YAMLError) as error:
        sys.exit(f"Ошибка: {error}")
