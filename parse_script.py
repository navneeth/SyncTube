import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import hydra
from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from omegaconf import DictConfig, OmegaConf


@dataclass
class SceneElement:
    visuals: List[str] = field(default_factory=list)
    dialogues: List[str] = field(default_factory=list)


def ensure_file_exists(filepath: str) -> Path:
    """Convert string path to Path object and verify it exists"""
    path = Path(os.path.expanduser(filepath)).resolve()
    if not path.is_file():
        print(f"Error: Script file not found: {path}")
        exit(1)
    return path


def parse_script(input_path: Path) -> List[SceneElement]:
    """Parse script file into scenes with visuals and dialogues"""
    scenes = []
    current_scene = SceneElement()

    for line in input_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("[Visual]"):
            current_scene.visuals.append(stripped)
        elif stripped.startswith("[S1]") or stripped.startswith("[S2]"):
            current_scene.dialogues.append(stripped)

    scenes.append(current_scene)
    return scenes


def write_outputs(
    scenes: List[SceneElement], audio_path: Path, image_path: Path
) -> None:
    """Write parsed scenes to separate audio and image files"""
    # Create parent directories if needed
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.parent.mkdir(parents=True, exist_ok=True)

    # Write dialogue lines
    audio_path.write_text(
        "\n".join(dialogue for scene in scenes for dialogue in scene.dialogues),
        encoding="utf-8",
    )

    # Write visual descriptions
    image_path.write_text(
        "\n".join(visual for scene in scenes for visual in scene.visuals),
        encoding="utf-8",
    )


@hydra.main(version_base="1.3", config_path=".", config_name="config")
def main(cfg: DictConfig) -> None:
    # Verify input file exists
    input_path = ensure_file_exists(cfg.input_script)

    # Generate output paths
    script_name = input_path.stem
    output_dir = input_path.parent
    audio_path = output_dir / f"{script_name}_audio.txt"
    image_path = output_dir / f"{script_name}_imagegen.txt"

    # Process script and write outputs
    scenes = parse_script(input_path)
    write_outputs(scenes, audio_path, image_path)

    # Print success message
    print(
        f"""
Successfully processed script: {input_path}
Audio output: {audio_path}
Image output: {image_path}
    """.strip()
    )


if __name__ == "__main__":
    main()
