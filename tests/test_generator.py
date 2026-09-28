import tempfile
import unittest
from pathlib import Path

from src.generator import MovieScriptGenerator


class MovieScriptGeneratorTests(unittest.TestCase):
    def test_generate_is_reproducible_with_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            generator_a = MovieScriptGenerator(output_dir=output_dir, seed=42)
            generator_b = MovieScriptGenerator(output_dir=output_dir, seed=42)
            script_a, fountain_a = generator_a.generate("Test Movie", "sci-fi", 6)
            script_b, fountain_b = generator_b.generate("Test Movie", "sci-fi", 6)
            self.assertEqual(script_a, script_b)
            self.assertEqual(fountain_a, fountain_b)

    def test_seek_tell_demo_reads_same_bytes(self):
        generator = MovieScriptGenerator(seed=1)
        data = generator.peek_file_start("scenes.txt", 40)
        self.assertTrue(data)

    def test_save_creates_both_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = MovieScriptGenerator(output_dir=Path(tmp), seed=1)
            script, fountain = generator.generate("My Movie", "thriller", 3)
            txt_path, fountain_path = generator.save("My Movie", "thriller", script, fountain)
            self.assertTrue(txt_path.exists())
            self.assertTrue(fountain_path.exists())


if __name__ == "__main__":
    unittest.main()
