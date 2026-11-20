import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from graph import bfs, test_repository
from order import load_order


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.children = test_repository(ROOT / "examples/graph.yaml")

    def test_breadth(self):
        seen = []

        def fetch(key):
            seen.append(key)
            return self.children(key)

        graph = bfs("A", fetch, 5)
        self.assertEqual(seen, ["A", "B", "C", "D"])
        self.assertEqual(graph["C"], ["D"])
        self.assertEqual(load_order(graph), ["D", "B", "C", "A"])

    def test_boundaries(self):
        self.assertEqual(bfs("A", self.children, 0), {"A": []})
        graph = bfs("A", self.children, 1)
        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": []})

    def test_cycle(self):
        graph = bfs("X", self.children, 10)
        self.assertEqual(graph["Z"], ["X"])
        with self.assertRaisesRegex(ValueError, "X -> Y -> Z -> X"):
            load_order(graph)

    def test_leaf(self):
        self.assertEqual(load_order(bfs("L", self.children, 5)), ["L"])
