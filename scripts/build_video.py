from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
STORY_FILE = ROOT / "content" / "story.txt"
VOICE = os.getenv("TTS_VOICE", "en-US-AnaNeural")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_card(text: str, index: int, path: Path) -> None:
    width, height = 1280, 720
    palettes = [
        ((27, 68, 120), (88, 177, 206)),
        ((75, 54, 130), (190, 117, 183)),
        ((24, 105, 91), (116, 190, 129)),
        ((166, 91, 39), (239, 180, 89)),
    ]
    top, bottom = palettes[index % len(palettes)]
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(top[c] * (1 - t) + bottom[c] * t) for c in range(3))
        for x in range(width):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image, "RGBA")
    # Simple decorative shapes; these are original graphics, not stock characters.
    draw.ellipse((930, 70, 1160, 300), fill=(255, 238, 160, 210))
    draw.ellipse((80, 520, 250, 690), fill=(255, 255, 255, 35))
    draw.ellipse((1030, 470, 1240, 680), fill=(255, 255, 255, 35))
    draw.rounded_rectangle((75, 90, 1205, 630), radius=42, fill=(8, 20, 40, 105))

    font = load_font(46)
    lines = wrap_text(draw, text, font, 980)
    line_height = 64
    total_height = len(lines) * line_height
    y = max(150, (height - total_height) // 2)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (width - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(25, 35, 55, 180))
        y += line_height
    image.save(path, quality=92)


async def make_audio(text: str, path: Path) -> None:
    communicator = edge_tts.Communicate(text, VOICE, rate="-5%", pitch="+2Hz")
    await communicator.save(str(path))


def get_story_sections() -> tuple[str, list[str]]:
    raw = STORY_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("content/story.txt is empty.")
    parts = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    title = parts[0].splitlines()[0].strip()
    paragraphs = parts[1:] if len(parts) > 1 else parts
    if not paragraphs:
        raise ValueError("Add a title followed by story paragraphs in content/story.txt.")
    return title, paragraphs


def build_video(title: str) -> Path:
    OUT.mkdir(exist_ok=True)
    _, paragraphs = get_story_sections()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        audio_files, card_files, durations = [], [], []

        for i, paragraph in enumerate(paragraphs):
            audio_path = temp / f"voice_{i:03d}.mp3"
            card_path = temp / f"card_{i:03d}.png"
            asyncio.run(make_audio(paragraph, audio_path))
            make_card(paragraph, i, card_path)
            audio_files.append(audio_path)
            card_files.append(card_path)
            probe = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
            ], text=True).strip()
            durations.append(float(probe) + 0.6)

        concat_file = temp / "slides.txt"
        with concat_file.open("w", encoding="utf-8") as f:
            for card, duration in zip(card_files, durations):
                f.write(f"file '{card.as_posix()}'\n")
                f.write(f"duration {duration:.3f}\n")
            f.write(f"file '{card_files[-1].as_posix()}'\n")

        audio_list = temp / "audio.txt"
        with audio_list.open("w", encoding="utf-8") as f:
            for audio in audio_files:
                f.write(f"file '{audio.as_posix()}'\n")

        narration = temp / "narration.mp3"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list), "-c", "copy", str(narration)])

        output = OUT / "tom-kids-world.mp4"
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(narration), "-vf", "scale=1280:720,format=yuv420p",
            "-r", "25", "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "160k", "-shortest", str(output)
        ])
        return output


def upload_video(video_path: Path, title: str, description: str, privacy: str) -> str:
    token_raw = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token_raw:
        raise RuntimeError("Missing GitHub secret: YOUTUBE_TOKEN_JSON")
    token_data = json.loads(token_raw)
    credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": "1",
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": True,
        },
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True),
    )
    response = request.execute()
    return response["id"]


if __name__ == "__main__":
    title = os.getenv("VIDEO_TITLE", "Tommy and the Little Lost Duck | Tom Kids World")
    description = os.getenv(
        "VIDEO_DESCRIPTION",
        "A gentle story for kids about kindness and asking a trusted grown-up for help.\n\n#KidsStories #TomKidsWorld"
    )
    privacy = os.getenv("VIDEO_PRIVACY", "private")
    if privacy not in {"private", "unlisted", "public"}:
        raise ValueError("VIDEO_PRIVACY must be private, unlisted, or public.")
    video = build_video(title)
    video_id = upload_video(video, title, description, privacy)
    print(f"Upload complete: https://www.youtube.com/watch?v={video_id}")
