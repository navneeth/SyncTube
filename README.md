# SyncTube

Generate Video from a Scripted Storyline

## Overview

SyncTube takes a folder containing an audio file (`.mp3`) and a set of images (`.webp`, `.png`, etc.), resizes the images, and generates a YouTube-ready video where each image is shown for approximately one second, synchronized to the audio duration.

## Requirements

- Python 3.x
- [pydub](https://github.com/jiaaro/pydub)
- [Pillow](https://python-pillow.org/)
- [ffmpeg](https://ffmpeg.org/) (must be installed and available in your system PATH)

Install Python dependencies:

```sh
pip install pydub Pillow
```

## Usage

```sh
python audio_image_sync.py <folder> [--image_pattern PATTERNS] [--output_folder OUTPUT]
```

- `<folder>`: Path to the folder containing the `.mp3` audio file and images.
- `--image_pattern`: (Optional) Comma-separated glob patterns for images (default: `*.webp,*.png`).
- `--output_folder`: (Optional) Where to save the output video (default: `./`).

### Example

Suppose your folder structure is:

```
SharkStory/
  ├── narration.mp3
  ├── img1.webp
  ├── img2.png
  └── img3.webp
```

Run:

```sh
python audio_image_sync.py ~/YouTube-Channel-WaitForIt/SharkStory
```

Sample output:

```
Using audio file: /Users/navneeth/YouTube-Channel-WaitForIt/SharkStory/narration.mp3
Looking for images with patterns: ['*.webp', '*.png']
Temporary directory created at: /Users/navneeth/YouTube-Channel-WaitForIt/SharkStory/tmp_573668
Processing 41 images...
Video created: ./output_video.mp4
Temporary directory ... has been removed.
```

The resulting `output_video.mp4` will be in your specified output folder.

## License

MIT License. See [LICENSE](LICENSE).
