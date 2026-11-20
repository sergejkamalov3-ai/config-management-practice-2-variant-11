import sys
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from graph import bfs
from maven import Maven
from render import render


class MavenTest(unittest.TestCase):
    def test_http_to_png(self):
        files = partial(SimpleHTTPRequestHandler,
                        directory=str(ROOT / "examples/poms"))
        with ThreadingHTTPServer(("127.0.0.1", 0), files) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                repo = Maven(f"http://127.0.0.1:{server.server_port}")
                direct = Maven(repo.base, all_direct=True)
                self.assertEqual(direct.children("junit:junit:4.13.2"), [
                    "org.hamcrest:hamcrest-core:1.3 (compile, jar)",
                    "org.hamcrest:hamcrest-library:1.3 (test, jar)",
                ])
                graph = bfs("junit:junit:4.13.2", repo.children, 5)
            finally:
                server.shutdown()
                thread.join()
        core = "org.hamcrest:hamcrest-core:1.3"
        self.assertEqual(graph, {"junit:junit:4.13.2": [core], core: []})
        with TemporaryDirectory() as folder:
            path = Path(folder) / "graph.png"
            render(graph, path)
            self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn("n0 --> n1", path.with_suffix(".mmd").read_text())
