import os
import shutil
import random
import argparse
from glob import glob
from pydub.utils import mediainfo
from PIL import Image

# Standard video size for YouTube (HD)
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def find_audio_file(folder):
    mp3_files = glob(os.path.join(folder, '*.mp3'))
    if mp3_files:
        return mp3_files[0]
    else:
        raise FileNotFoundError("No MP3 file found in the folder.")


def find_image_files(folder, patterns):
    """Find image files matching any of the given patterns."""
    all_images = []
    for pattern in patterns:
        all_images.extend(glob(os.path.join(folder, pattern)))
    
    # Sort all images together
    all_images = sorted(all_images)
    
    if not all_images:
        raise FileNotFoundError(f"No images found matching patterns {patterns} in the folder.")
    return all_images


def get_audio_duration(audio_file):
    audio_info = mediainfo(audio_file)
    return float(audio_info['duration'])


def resize_and_save(image_path, output_path, size=(TARGET_WIDTH, TARGET_HEIGHT)):
    with Image.open(image_path) as img:
        img = img.convert("RGB")  # Convert to RGB (webp and png may have alpha)
        img = img.resize(size, Image.LANCZOS)
        img.save(output_path, format="WEBP")


def duplicate_images(audio_file, image_patterns, output_folder, target_folder):
    # Support multiple image patterns
    image_files = find_image_files(target_folder, image_patterns)
    if len(image_files) == 0:
        raise ValueError("No images found to duplicate.")

    temp_dir = os.path.join(target_folder, 'tmp_' + str(random.randint(100000, 999999)))
    os.makedirs(temp_dir)

    audio_duration = get_audio_duration(audio_file)
    num_images = len(image_files)
    target_num_images = int(audio_duration)

    frames_per_image = target_num_images // num_images
    remainder = target_num_images % num_images

    idx = 0
    for image_idx, image_path in enumerate(image_files):
        repeats = frames_per_image + (1 if image_idx < remainder else 0)
        for _ in range(repeats):
            temp_image_path = os.path.join(temp_dir, f"image_{idx + 1:04d}.webp")
            resize_and_save(image_path, temp_image_path)
            idx += 1

    return temp_dir


def create_video(temp_dir, audio_file, output_file):
    os.system(
        f"ffmpeg -framerate 1 -pattern_type glob -i '{temp_dir}/image_*.webp' -i '{audio_file}' "
        "-filter_complex '[0:v]fps=1,format=yuv420p[v];[1:a]aresample=async=1[a]' "
        "-map '[v]' -map '[a]' -c:v libx264 -c:a aac -strict experimental -shortest "
        f"{output_file}"
    )


def main():
    parser = argparse.ArgumentParser(description="Sync resized images with audio duration and create a YouTube-ready video.")
    parser.add_argument('folder', type=str, help="Folder containing the audio and images.")
    parser.add_argument('--image_pattern', type=str, default='*.webp,*.png', 
                        help="Comma-separated patterns to match image files (default: *.webp,*.png).")
    parser.add_argument('--output_folder', type=str, default='./', help="Folder to save the output video.")
    
    args = parser.parse_args()
    folder = args.folder
    audio_file = find_audio_file(folder)
    print(f"Using audio file: {audio_file}")

    # Split the image pattern into a list of patterns
    image_patterns = [pattern.strip() for pattern in args.image_pattern.split(',')]
    print(f"Looking for images with patterns: {image_patterns}")

    try:
        temp_dir = duplicate_images(audio_file, image_patterns, args.output_folder, folder)
        print(f"Temporary directory created at: {temp_dir}")
        print(f"Processing {len(find_image_files(folder, image_patterns))} images...")

        output_file = os.path.join(args.output_folder, "output_video.mp4")
        create_video(temp_dir, audio_file, output_file)
        print(f"Video created: {output_file}")

        shutil.rmtree(temp_dir)
        print(f"Temporary directory {temp_dir} has been removed.")

    except Exception as e:
        print(f"An error occurred: {e}")
        # Clean up temp dir if it exists
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory {temp_dir} after error.")


if __name__ == "__main__":
    main()