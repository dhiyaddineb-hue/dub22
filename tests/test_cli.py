import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dub22_cli", ROOT / "scripts" / "dub22.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CliTests(unittest.TestCase):
    def test_find_urls_recurses_and_deduplicates(self):
        payload = {
            "outputs": {
                "video": {"url": "https://cdn.example/video.mp4"},
                "audio": {"url": "https://cdn.example/audio.mp3"},
            },
            "duplicate": "https://cdn.example/video.mp4",
        }
        self.assertEqual(
            MODULE.find_urls(payload),
            ["https://cdn.example/video.mp4", "https://cdn.example/audio.mp3"],
        )

    def test_parser_defaults_to_arabic_and_dubbing_v2(self):
        args = MODULE.build_parser().parse_args(["run", "--input", "input.mp4"])
        self.assertEqual(args.target_language, "ar")
        self.assertEqual(args.model_id, "dubbing_v2")
        self.assertEqual(args.cloning_strength, 7)


if __name__ == "__main__":
    unittest.main()
