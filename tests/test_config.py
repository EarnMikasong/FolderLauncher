import json
import tempfile
import unittest
from pathlib import Path

from folder_launcher.config import ConfigStore, create_default_config


class ConfigStoreTests(unittest.TestCase):
    def test_first_load_creates_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = ConfigStore(path).load()

            self.assertTrue(path.exists())
            self.assertEqual([item.id for item in config.commands], ["claude", "agy"])
            self.assertEqual(len(config.folders), 9)

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ConfigStore(Path(directory) / "config.json")
            config = create_default_config()
            config.categories[0].name = "Claude 工作区"

            store.save(config)
            loaded = store.load()

            self.assertEqual(loaded.categories[0].name, "Claude 工作区")
            self.assertEqual(loaded.to_dict(), config.to_dict())

    def test_invalid_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = create_default_config().to_dict()
            config["folders"][0]["category_id"] = "missing"
            path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError):
                ConfigStore(path).load()


if __name__ == "__main__":
    unittest.main()
