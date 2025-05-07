import os
from pathlib import Path

import hydra
import requests
from dotenv import load_dotenv
from omegaconf import DictConfig

load_dotenv()  # Load .env file


class ImageGenerator:
    def generate(self, prompt):
        raise NotImplementedError


class ReveAIGenerator(ImageGenerator):
    def __init__(self):
        self.api_key = os.getenv("REVE_API_KEY")
        self.api_url = "https://reveapi.com/api/generate-image"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt):
        data = {
            "prompt": prompt,
            "style": "photorealistic",
            "width": 1024,
            "height": 1024,
        }
        try:
            response = requests.post(self.api_url, headers=self.headers, json=data)
            if response.status_code == 200:
                image_url = response.json().get("output")
                if image_url:
                    img_resp = requests.get(image_url)
                    if img_resp.status_code == 200:
                        return img_resp.content
            print(f"[ReveAI] Failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ReveAI] Error: {e}")
        return None


def load_prompts(filepath: Path):
    """Load visual prompts from file"""
    with open(filepath, "r", encoding="utf-8") as f:
        return [
            line.replace("[Visual]", "").strip()
            for line in f
            if line.startswith("[Visual]")
        ]


def save_images(generator, prompts, output_dir: Path):
    """Generate and save images from prompts"""
    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, prompt in enumerate(prompts, 1):
        print(f"[INFO] Generating image {idx:03d}: {prompt}")
        img_data = generator.generate(prompt)
        if img_data:
            img_path = output_dir / f"{idx:03d}.png"
            with open(img_path, "wb") as f:
                f.write(img_data)
            print(f"[SUCCESS] Saved: {img_path}")
        else:
            print(f"[FAIL] Could not generate image for: {prompt}")


@hydra.main(version_base="1.3", config_path=".", config_name="config")
def main(cfg: DictConfig) -> None:
    # Get input script directory
    script_dir = Path(os.path.expanduser(cfg.input_script)).parent

    # Look for script_imagegen.txt in the same directory
    imagegen_file = script_dir / "script_imagegen.txt"
    if not imagegen_file.exists():
        print(f"Error: Could not find {imagegen_file}")
        return

    # Setup output directory
    output_dir = script_dir / "generated_images"

    # Load prompts and generate images
    prompts = load_prompts(imagegen_file)
    generator = ReveAIGenerator()
    save_images(generator, prompts, output_dir)


if __name__ == "__main__":
    main()
