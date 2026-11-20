"""Порядок загрузки: каждая зависимость предшествует потребителю."""
from graphlib import CycleError, TopologicalSorter


def load_order(graph):
    """Построить топологический порядок или показать конкретный цикл."""
    try:
        return list(TopologicalSorter(graph).static_order())
    except CycleError as error:
        cycle = " -> ".join(error.args[1])
        raise ValueError(f"Порядок загрузки невозможен: {cycle}") from error
