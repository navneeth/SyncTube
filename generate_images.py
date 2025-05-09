import io
import json
import logging
import os
from pathlib import Path

import hydra
import numpy as np
import openai
import requests
import torch
from omegaconf import DictConfig
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check required dependencies
HAVE_DEPENDENCIES = True
MISSING_DEPS = []

try:
    from diffusers import (
        DPMSolverMultistepScheduler,
        EulerDiscreteScheduler,
        StableDiffusionPipeline,
    )
except ImportError as e:
    HAVE_DEPENDENCIES = False
    MISSING_DEPS.append(f"diffusers: {e}")

try:
    import numpy as np
except ImportError as e:
    HAVE_DEPENDENCIES = False
    MISSING_DEPS.append(f"numpy: {e}")

if not HAVE_DEPENDENCIES:
    logger.warning(f"Missing dependencies: {', '.join(MISSING_DEPS)}")

try:
    import torch
    from diffusers import (
        DPMSolverMultistepScheduler,
        EulerDiscreteScheduler,
        StableDiffusionPipeline,
    )

    HAVE_TORCH = True
except ImportError as e:
    logger.warning(f"Could not import torch/diffusers: {e}")
    HAVE_TORCH = False


class ImageGenerator:
    def generate(self, prompt, size):
        raise NotImplementedError


class ReveAIGenerator(ImageGenerator):
    def __init__(self):
        self.api_key = os.getenv("REVE_API_KEY")
        if not self.api_key:
            raise EnvironmentError("REVE_API_KEY not found in environment.")
        self.api_url = "https://reveapi.com/api/generate-image"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt, size):
        width, height = map(int, size.lower().split("x"))
        data = {
            "prompt": prompt,
            "style": "photorealistic",
            "width": width,
            "height": height,
        }
        try:
            response = requests.post(self.api_url, headers=self.headers, json=data)
            response.raise_for_status()
            if image_url := response.json().get("output"):
                img_resp = requests.get(image_url)
                if img_resp.status_code == 200:
                    return img_resp.content
            logger.warning(f"[ReveAI] No output from API for prompt: {prompt}")
        except Exception as e:
            logger.error(f"[ReveAI] Error generating image: {e}")
        return None


class DalleGenerator(ImageGenerator):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment.")
        openai.api_key = self.api_key

    def generate(self, prompt, size):
        try:
            # Use DALL-E 3 if available
            response = openai.Image.create(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size=size,
                # Only DALL-E 3 supports these:
                # quality="standard",
                # style="natural",
            )
            if response and response.data:
                image_url = response.data[0].url
                img_resp = requests.get(image_url)
                if img_resp.status_code == 200:
                    return img_resp.content
                logger.warning(
                    f"[DALL-E] Failed to download image: {img_resp.status_code}"
                )
            else:
                logger.warning(f"[DALL-E] No image data for prompt: {prompt}")
        except Exception as e:
            logger.error(f"[DALL-E] Error generating image: {str(e)}")
        return None


class HuggingFaceGenerator(ImageGenerator):
    def __init__(self):
        self.api_key = os.getenv("HF_API_KEY")
        if not self.api_key:
            raise EnvironmentError("HF_API_KEY not found in environment")
        # Updated model URL to use stable-diffusion-v1-4
        self.api_url = (
            "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4"
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt, size):
        width, height = map(int, size.lower().split("x"))
        data = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": 50,  # Increased for better quality
                "guidance_scale": 7.5,
                "negative_prompt": "blurry, bad quality, distorted, ugly, disfigured",
                "scheduler": "DPMSolverMultistep",  # Better scheduler
            },
        }
        try:
            response = requests.post(self.api_url, headers=self.headers, json=data)
            response.raise_for_status()

            if response.status_code == 200:
                # SD v1.4 returns a list of images
                images = response.json()
                if images and isinstance(images, list):
                    # Convert base64 to bytes
                    import base64

                    return base64.b64decode(images[0].split(",", 1)[1])
            logger.warning(f"[HuggingFace] No output from API for prompt: {prompt}")
        except Exception as e:
            logger.error(f"[HuggingFace] Error generating image: {e}")
            if hasattr(e, "response"):
                logger.error(f"Response: {e.response.text}")
        return None


class LocalStableDiffusionGenerator(ImageGenerator):
    def __init__(self):
        if not HAVE_DEPENDENCIES:
            raise ImportError(
                "Local generation requires additional dependencies. "
                f"Missing: {', '.join(MISSING_DEPS)}"
            )

        self.model_id = "CompVis/stable-diffusion-v1-4"
        self.device = "cpu"
        logger.info("[LocalSD] Using CPU. Generation will be slower.")

        # Load pipeline with CPU optimizations
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float32,
            safety_checker=None,
            use_safetensors=True,
            low_cpu_mem_usage=True,
        )

        # Use memory-efficient scheduler
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config,
            use_karras_sigmas=True,
            algorithm_type="dpmsolver++",
        )

        # Basic memory optimizations that work on CPU
        self.pipe.enable_attention_slicing(slice_size=1)
        self.pipe.enable_vae_slicing()

        # Move to CPU explicitly
        self.pipe = self.pipe.to(self.device)

    def generate(self, prompt, size):
        try:
            # Limit dimensions for CPU
            width, height = map(int, size.lower().split("x"))
            width = min(width, 512)
            height = min(height, 512)

            # Force garbage collection
            import gc

            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            gc.collect()

            with torch.inference_mode():
                image = self.pipe(
                    prompt,
                    num_inference_steps=15,  # Further reduced for CPU
                    guidance_scale=7.0,
                    width=width,
                    height=height,
                ).images[0]

            # Optimize output image
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="PNG", optimize=True, quality=90)
            return img_byte_arr.getvalue()

        except Exception as e:
            logger.error(f"[LocalSD] Error generating image: {str(e)}")
            import traceback

            logger.error(f"[LocalSD] Traceback: {traceback.format_exc()}")
            return None


def load_prompts(filepath: Path):
    with open(filepath, "r", encoding="utf-8") as f:
        return [
            line.replace("[Visual]", "").strip()
            for line in f
            if line.startswith("[Visual]")
        ]


def save_images(generator, prompts, output_dir: Path, size: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, prompt in enumerate(prompts, 1):
        img_path = output_dir / f"{idx:03d}.png"
        if img_path.exists():
            logger.info(f"[SKIP] Image already exists: {img_path}")
            continue

        logger.info(f"[INFO] Generating image {idx:03d}: {prompt}")
        img_data = generator.generate(prompt, size)
        if img_data:
            with open(img_path, "wb") as f:
                f.write(img_data)
            logger.info(f"[SUCCESS] Saved: {img_path}")
        else:
            logger.warning(f"[FAIL] Could not generate image for: {prompt}")


@hydra.main(version_base="1.3", config_path=".", config_name="config")
def main(cfg: DictConfig) -> None:
    script_dir = Path(os.path.expanduser(cfg.input_script)).parent
    imagegen_file = script_dir / "script_imagegen.txt"

    if not imagegen_file.exists():
        logger.error(f"Prompt file not found: {imagegen_file}")
        return

    output_dir = script_dir / "generated_images"
    prompts = load_prompts(imagegen_file)

    # Choose API
    if cfg.image_api == "reve":
        generator = ReveAIGenerator()
    elif cfg.image_api == "dalle":
        generator = DalleGenerator()
    elif cfg.image_api == "huggingface":
        generator = HuggingFaceGenerator()
    elif cfg.image_api == "local":
        if not HAVE_TORCH:
            logger.error("Local generation requires torch and diffusers")
            return
        generator = LocalStableDiffusionGenerator()
    else:
        logger.error(f"Unsupported image API: {cfg.image_api}")
        return

    save_images(generator, prompts, output_dir, cfg.image_size)


if __name__ == "__main__":
    main()
