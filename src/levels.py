"""Рекурсивный обход уровней с логарифмической глубиной стека."""


def walk_levels(frontier, limit, expand):
    """Обработать уровни по порядку через рекурсивное деление интервала."""
    def visit(start, stop, current):
        if not current or start == stop:
            return current
        if stop - start == 1:
            return expand(current, start)
        middle = (start + stop) // 2
        following = visit(start, middle, current)
        return visit(middle, stop, following)

    return visit(0, limit, frontier)
