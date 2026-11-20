"""Точка входа визуализатора."""
import argparse
import sys

import yaml

from config import load


def run(cfg):
    """Показать эффективные настройки."""
    for key, value in cfg.items():
        print(f"{key} = {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="путь к YAML")
    try:
        run(load(parser.parse_args().config))
    except (ValueError, OSError, yaml.YAMLError) as error:
        sys.exit(f"Ошибка: {error}")
