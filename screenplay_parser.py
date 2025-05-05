import json
import re


def parse_script_into_scenes(script_text):
    """
    Parses a video script into a list of scenes, where each scene is a dictionary
    containing scene-specific information and a list of its elements.

    Args:
        script_text (str): The raw script text in screenplay format.

    Returns:
        list: A list of dictionaries, where each dictionary represents a scene
              and contains 'scene_number', 'heading', 'slug', and 'elements' (a list
              of script elements within that scene). The top-level metadata
              (title, series, episode) is also included as the first element
              of the list.
    """
    lines = [line.strip() for line in script_text.split("\n") if line.strip()]
    script_metadata = {
        "metadata": {
            "title": "",
            "series": "",
            "episode": 1,
        }
    }
    scenes = [script_metadata]
    current_scene = None
    scene_number_counter = 0

    # Extract metadata
    title_match = re.search(r'\[Title card: "(.*?)"\]', script_text)
    if title_match:
        script_metadata["metadata"]["title"] = title_match.group(1)

    series_match = re.search(r'\[Opening music and animation: "(.*?)"', script_text)
    if series_match:
        script_metadata["metadata"]["series"] = series_match.group(1)

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for scene headings
        if re.match(r"Scene \d+:", line):
            scene_number_counter += 1
            scene_title = line.split(":", 1)[1].strip()
            current_scene = {
                "scene_number": scene_number_counter,
                "heading": scene_title,
                "slug": f"SCENE_{scene_number_counter}",
                "elements": [],
            }
            scenes.append(current_scene)

        # Production elements and dialogue within a scene
        elif current_scene is not None:
            if line.startswith("[") and "]" in line:
                element_content = line.strip("[]")

                if "Title card:" in element_content:
                    current_scene["elements"].append(
                        {
                            "type": "graphic",
                            "subtype": "title_card",
                            "content": element_content.replace("Title card:", "")
                            .strip()
                            .strip('"'),
                        }
                    )
                elif "Visual:" in element_content:
                    current_scene["elements"].append(
                        {
                            "type": "shot",
                            "description": element_content.replace(
                                "Visual:", ""
                            ).strip(),
                        }
                    )
                elif "Sound effect:" in element_content:
                    current_scene["elements"].append(
                        {
                            "type": "sound",
                            "description": element_content.replace(
                                "Sound effect:", ""
                            ).strip(),
                        }
                    )
                elif "Opening music and animation:" in element_content:
                    current_scene["elements"].append(
                        {
                            "type": "music_cue",
                            "description": element_content.replace(
                                "Opening music and animation:", ""
                            ).strip(),
                        }
                    )
                elif "Outro music" in element_content:
                    current_scene["elements"].append(
                        {"type": "music_cue", "description": "Outro music"}
                    )
                elif "Text on screen:" in element_content:
                    current_scene["elements"].append(
                        {
                            "type": "super",
                            "content": element_content.replace(
                                "Text on screen:", ""
                            ).strip(),
                        }
                    )
                elif "End card" in element_content:
                    if current_scene is not None:
                        current_scene["elements"].append(
                            {
                                "type": "graphic",
                                "subtype": "end_card",
                                "description": element_content,
                            }
                        )
                    else:
                        # No current scene is set; choose to either log a warning, create a default scene, or skip
                        # For now, we'll simply skip appending as there is no valid scene.
                        pass

            elif line.startswith("Narrator"):
                tone = "normal"
                if "(" in line and ")" in line:
                    tone_match = re.search(r"\((.*?)\)", line)
                    if tone_match:
                        tone = tone_match.group(1)

                if i + 1 < len(lines) and not (
                    lines[i + 1].startswith("[")
                    or lines[i + 1].startswith("Narrator")
                    or re.match(r"Scene \d+:", lines[i + 1])
                ):
                    narration_text = lines[i + 1]
                    current_scene["elements"].append(
                        {
                            "type": "dialogue",
                            "character": "NARRATOR",
                            "modifier": "V.O.",
                            "tone": tone,
                            "text": narration_text,
                        }
                    )
                    i += 1
                else:
                    # Handle case where narrator line is the last line or followed by another narrator/scene/bracketed element
                    current_scene["elements"].append(
                        {
                            "type": "dialogue",
                            "character": "NARRATOR",
                            "modifier": "V.O.",
                            "tone": tone,
                            "text": "",  # Or perhaps raise a warning about missing dialogue
                        }
                    )

            elif '"' in line and line.count('"') >= 2:
                quotes = re.findall(r'"([^"]*)"', line)
                if quotes:
                    dialogue_text = quotes[0]
                    match = re.match(r'\s*(Harmony|Melody|Star|Bubbles)\s*:', line)
                    if match:
                        speaker = match.group(1).upper()
                    else:
                        speaker = "CHARACTER"
                    current_scene["elements"].append(
                        {
                            "type": "dialogue",
                            "character": speaker,
                            "text": dialogue_text,
                        }
                    )

            elif not (
                line.startswith("[")
                or line.startswith("Narrator")
                or re.match(r"Scene \d+:", line)
            ):
                if i > 0 and not (lines[i - 1].startswith("Narrator")):
                    current_scene["elements"].append({"type": "action", "text": line})

        i += 1

    return scenes


def print_script_stats(parsed_script):
    """
    Prints statistics about the parsed script, such as the number of scenes
    and the number of elements in each scene.

    Args:
        parsed_script (list): The list of scenes returned by parse_script_into_scenes.
    """
    num_scenes = len(parsed_script) - 1  # Exclude the metadata dictionary
    print("--- Script Statistics ---")
    print(f"Number of Scenes: {num_scenes}")

    if num_scenes > 0:
        for scene in parsed_script[1:]:
            print(f"\nScene {scene['scene_number']}: {scene['heading']}")
            print(f"  Number of Elements: {len(scene['elements'])}")
            dialogue_count = sum(bool(element["type"] == "dialogue")
                             for element in scene["elements"])

            action_count = sum(
                1 for element in scene["elements"] if element["type"] == "action"
            )
            shot_count = sum(
                1 for element in scene["elements"] if element["type"] == "shot"
            )
            sound_count = sum(
                1 for element in scene["elements"] if element["type"] == "sound"
            )
            graphic_count = sum(
                1 for element in scene["elements"] if element["type"] == "graphic"
            )
            music_count = sum(
                1 for element in scene["elements"] if element["type"] == "music_cue"
            )
            super_count = sum(
                1 for element in scene["elements"] if element["type"] == "super"
            )
            print(f"    - Dialogue Lines: {dialogue_count}")
            print(f"    - Action Lines: {action_count}")
            print(f"    - Shots: {shot_count}")
            print(f"    - Sound Effects: {sound_count}")
            print(f"    - Graphics: {graphic_count}")
            print(f"    - Music Cues: {music_count}")
            print(f"    - On-Screen Text: {super_count}")
    else:
        print("No scenes found in the script.")


# Example usage
if __name__ == "__main__":
    test_script = """
    [Opening music and animation: "Wait for it, Kids!" intro plays]
    Narrator (excited tone):
    Hey, ocean explorers!
    Today, we're diving deep into the magical world of humpback whales…
    With a special story about one very curious whale named Harmony and her amazing family.
    [Title card: "A Humpback Whale Adventure: The Tale of Harmony and Her Pod"]

    Scene 1: The Sparkling Surface
    [Visual: Calm ocean sunrise, shimmering water]
    Narrator:
    Early morning in the Pacific Ocean, and the waves sparkle like golden treasure.
    PSSHHHH!
    A big, misty spout bursts into the air—
    That's Harmony, a young humpback whale, saying "good morning!"
    [Visual: Harmony swimming beside her mom]
    "Mom," she asks, "why does my spout look like a sparkly cloud?"
    Her mom, Melody, smiles.
    "That's your warm breath meeting the cool ocean air. Every whale's spout is unique—just like you!"
    Narrator (whisper tone):
    See those little bumps on Melody's back? Those are barnacles—tiny creatures that hitch a ride and sparkle like ocean jewels.

    Scene 2: Underwater Wonders
    [Visual: Coral reef teeming with colorful fish]
    Narrator:
    Now, let's dive beneath the surface to explore the vibrant coral reefs!
    [Sound effect: Gentle bubbling]
    Harmony swims through the colorful corals.
    Star, a playful dolphin, zips by.
    Star:
    "Hey, Harmony! What are you looking at?"
    Harmony:
    "Everything! It's so beautiful down here."
    [Text on screen: "The Great Barrier Reef"]
    """

    parsed_script_scenes = parse_script_into_scenes(test_script)

    # Print the parsed script (optional)
    # print(json.dumps(parsed_script_scenes, indent=2))

    # Print the script statistics
    print_script_stats(parsed_script_scenes)
