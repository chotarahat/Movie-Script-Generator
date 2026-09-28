from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DEFAULT_TITLE = "Untitled Movie"


@dataclass(frozen=True)
class Character:
    name: str
    role: str
    trait: str


@dataclass(frozen=True)
class Scene:
    heading: str
    description: str


class MovieScriptGenerator:
    """Generate a randomized three-act screenplay from local data files."""

    def __init__(self, data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR, seed: int | None = None) -> None:
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.rng = random.Random(seed)

    def load_characters(self) -> list[Character]:
        path = self.data_dir / "characters.csv"
        characters: list[Character] = []
        with path.open("r", encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                name = (row.get("name") or "").strip()
                role = (row.get("role") or "").strip()
                trait = (row.get("trait") or "").strip()
                if name and role and trait:
                    characters.append(Character(name, role, trait))
        if not characters:
            raise ValueError(f"No valid characters found in {path}")
        return characters

    def load_scenes(self) -> list[Scene]:
        path = self.data_dir / "scenes.txt"
        scenes: list[Scene] = []
        with path.open("r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    heading, description = line.split("|", 1)
                else:
                    heading, description = line, ""
                scenes.append(Scene(heading.strip(), description.strip()))
        if not scenes:
            raise ValueError(f"No scenes found in {path}")
        return scenes

    def load_dialogue(self) -> list[str]:
        path = self.data_dir / "dialogue.txt"
        with path.open("r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip() and not line.startswith("#")]
        if not lines:
            raise ValueError(f"No dialogue found in {path}")
        return lines

    def load_genres(self) -> dict[str, dict[str, list[str]]]:
        path = self.data_dir / "genres.json"
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict) or not data:
            raise ValueError(f"No genres found in {path}")
        return data

    def peek_file_start(self, filename: str, n_bytes: int = 80) -> bytes:
        """Demonstrate tell/seek without loading the whole file."""
        path = self.data_dir / filename
        with path.open("rb") as file:
            first = file.read(n_bytes)
            position = file.tell()
            file.seek(0)
            again = file.read(n_bytes)
        if first != again:
            raise RuntimeError("seek/tell verification failed")
        return first

    def choose_characters(self, characters: list[Character], count: int = 3) -> list[Character]:
        count = min(max(count, 1), len(characters))
        return self.rng.sample(characters, count)

    def build_scene_lines(
        self,
        scene_number: int,
        act_name: str,
        scene: Scene,
        characters: list[Character],
        dialogue_pool: list[str],
        genre_pool: dict[str, list[str]],
    ) -> list[str]:
        lines: list[str] = []
        lines.append(act_name.upper())
        lines.append(f"SCENE {scene_number}")
        lines.append(scene.heading)
        lines.append("")
        if scene.description:
            lines.extend([scene.description, ""])

        beats = genre_pool["inciting"] + genre_pool["rising"] + genre_pool["climax"]
        lines.append(self.rng.choice(beats))
        lines.append("")

        speakers = self.choose_characters(characters, min(3, len(characters)))
        for character in speakers:
            lines.append(character.name.upper())
            lines.append(f"({character.trait})")
            lines.append(self.rng.choice(dialogue_pool))
            lines.append("")

        return lines

    def generate(self, title: str, genre: str, scene_count: int = 9) -> tuple[str, str]:
        characters = self.load_characters()
        scenes = self.load_scenes()
        dialogue_pool = self.load_dialogue()
        genres = self.load_genres()

        genre_key = genre.strip().lower()
        if genre_key not in genres:
            raise ValueError(f"Unknown genre '{genre}'. Choose from: {', '.join(sorted(genres))}")
        if scene_count < 3:
            raise ValueError("Scene count must be at least 3 so the three acts can be represented.")

        genre_pool = genres[genre_key]
        selected_scenes = self.rng.sample(scenes, min(scene_count, len(scenes)))
        while len(selected_scenes) < scene_count:
            selected_scenes.append(self.rng.choice(scenes))

        lines: list[str] = [f"TITLE: {title.strip() or DEFAULT_TITLE}", f"GENRE: {genre_key.title()}", ""]
        lines.extend(["FADE IN:", ""])

        act_sizes = self._split_into_three_acts(scene_count)
        scene_index = 0
        act_names = ["ACT I", "ACT II", "ACT III"]

        for act_name, size in zip(act_names, act_sizes):
            for _ in range(size):
                scene_index += 1
                scene = selected_scenes[scene_index - 1]
                lines.extend(
                    self.build_scene_lines(
                        scene_index,
                        act_name,
                        scene,
                        characters,
                        dialogue_pool,
                        genre_pool,
                    )
                )
                lines.extend(["CUT TO:", ""])

        lines.extend([genre_pool["ending"][self.rng.randrange(len(genre_pool["ending"]))], "", "FADE OUT."])
        plain_text = "\n".join(lines).strip() + "\n"

        fountain_text = self._to_fountain(title, genre_key, lines)
        return plain_text, fountain_text

    @staticmethod
    def _split_into_three_acts(scene_count: int) -> list[int]:
        base, remainder = divmod(scene_count, 3)
        parts = [base, base, base]
        for i in range(remainder):
            parts[i] += 1
        return parts

    @staticmethod
    def _to_fountain(title: str, genre: str, lines: list[str]) -> str:
        fountain = [f"Title: {title.strip() or DEFAULT_TITLE}", f"Genre: {genre.title()}", ""]
        for line in lines[3:]:
            if line.startswith("ACT ") or line.startswith("SCENE "):
                fountain.extend([line, ""])
            elif line.startswith("INT. ") or line.startswith("EXT. "):
                fountain.extend([line, ""])
            elif line.isupper() and line not in {"FADE IN:", "FADE OUT.", "CUT TO:"}:
                fountain.extend([line, ""])
            else:
                fountain.append(line)
        return "\n".join(fountain).strip() + "\n"

    def save(self, title: str, genre: str, plain_text: str, fountain_text: str) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c.lower() if c.isalnum() else "_" for c in title).strip("_") or "movie_script"
        txt_path = self.output_dir / f"{safe_title}.txt"
        fountain_path = self.output_dir / f"{safe_title}.fountain"
        txt_path.write_text(plain_text, encoding="utf-8")
        fountain_path.write_text(fountain_text, encoding="utf-8")
        return txt_path, fountain_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a randomized movie screenplay.")
    parser.add_argument("--title", help="Movie title")
    parser.add_argument("--genre", choices=["sci-fi", "horror", "comedy", "thriller"], help="Movie genre")
    parser.add_argument("--scenes", type=int, default=6, help="Number of scenes (minimum 3)")
    parser.add_argument("--seed", type=int, help="Seed for reproducible output")
    parser.add_argument("--demo-seek-tell", action="store_true", help="Show the seek/tell file-handling demo")
    return parser.parse_args()


def choose_from_menu(prompt: str, options: list[str]) -> str:
    print(prompt)
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")
    while True:
        answer = input("Choose an option: ").strip()
        try:
            index = int(answer)
            if 1 <= index <= len(options):
                return options[index - 1]
        except ValueError:
            pass
        print("Please enter a valid number.")


def main() -> None:
    args = parse_args()
    generator = MovieScriptGenerator(seed=args.seed)

    try:
        title = args.title or input("Movie title: ").strip() or DEFAULT_TITLE
        genre = args.genre or choose_from_menu("Choose a genre:", ["sci-fi", "horror", "comedy", "thriller"])
        scene_count = args.scenes

        if args.demo_seek_tell:
            raw_head = generator.peek_file_start("scenes.txt")
            print("seek/tell demo:", raw_head[:60], "...")

        plain_text, fountain_text = generator.generate(title, genre, scene_count)
        txt_path, fountain_path = generator.save(title, genre, plain_text, fountain_text)

        print("\nMovie script generated successfully.")
        print(f"TXT:     {txt_path.relative_to(ROOT)}")
        print(f"Fountain:{fountain_path.relative_to(ROOT)}")

    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
