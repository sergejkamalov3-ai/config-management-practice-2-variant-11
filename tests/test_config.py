import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import load


class ConfigTest(unittest.TestCase):
    def test_invalid_fields(self):
        source = (ROOT / "examples/live.yaml").read_text()
        bad = dict(package="x", repository="abc", test_mode="yes",
                   version="", output="file.jpg", max_depth=-1)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "c.yaml"
            for key, value in bad.items():
                with self.subTest(field=key):
                    cfg = yaml.safe_load(source)
                    cfg[key] = value
                    path.write_text(yaml.safe_dump(cfg))
                    with self.assertRaisesRegex(ValueError, key):
                        load(path)
