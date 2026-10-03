"""Render committed sharing images offline; no per-share generation or AI calls."""

from argparse import ArgumentParser
from functools import lru_cache
import hashlib
from itertools import combinations
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if __package__:
    from .social_meta import (
        HEIGHT, IMAGE_DIRECTORY, IMAGE_VERSION, ROOT, WIDTH,
        image_filename, load_headlines, validate_headlines,
    )
else:
    from social_meta import (
        HEIGHT, IMAGE_DIRECTORY, IMAGE_VERSION, ROOT, WIDTH,
        image_filename, load_headlines, validate_headlines,
    )

ASSETS = ROOT / "tools/share_assets"
INKS = ("#102432", "#422238", "#143b31")
PAPER = "#fff9ec"
MIN_FONT_SIZE = 104
MAX_FONT_SIZE = 148
TEXT_LEFT, TEXT_RIGHT = 300, 900
TEXT_TOP, TEXT_BOTTOM = 214, 518
SITE_HEADLINE = "Lincoln's Devotional"
SITE_CAPTION = "Daily readings"
FUNCTION_WORDS = {"a", "and", "by", "for", "from", "in", "of", "the", "through", "to", "with"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inputs_fingerprint():
    paths = [Path(__file__), ROOT / "tools/social_meta.py", ROOT / "data/share_headlines.json"]
    paths.extend(sorted(path for path in ASSETS.iterdir() if path.is_file()))
    return digest(b"".join(path.read_bytes() for path in paths))


@lru_cache(maxsize=96)
def font(size, utility=False):
    face = ImageFont.truetype(str(ASSETS / ("Inter.ttf" if utility else "Newsreader.ttf")), size)
    values = []
    for axis in face.get_variation_axes():
        name = axis["name"].decode()
        value = 600 if name == "Weight" else (32 if utility else 72)
        values.append(max(axis["minimum"], min(axis["maximum"], value)))
    face.set_variation_by_axes(values)
    return face


def line_partitions(text):
    words = text.split()
    for count in range(1, min(3, len(words)) + 1):
        for cuts in combinations(range(1, len(words)), count - 1):
            stops = (0, *cuts, len(words))
            yield [" ".join(words[start:end]) for start, end in zip(stops, stops[1:])]


def choose_layout(text):
    partitions = list(line_partitions(text))
    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -2):
        face = font(size)
        advance = round(size * .90)
        candidates = []
        for lines in partitions:
            boxes = [face.getbbox(line) for line in lines]
            widths = [box[2] - box[0] for box in boxes]
            heights = [box[3] - box[1] for box in boxes]
            height = max(
                index * advance + line_height
                for index, line_height in enumerate(heights)
            )
            if max(widths) > TEXT_RIGHT - TEXT_LEFT or height > TEXT_BOTTOM - TEXT_TOP:
                continue
            dangling = sum(line.split()[-1].lower() in FUNCTION_WORDS for line in lines[:-1])
            score = (dangling, max(widths) - min(widths), len(lines))
            candidates.append((score, lines, boxes, advance, height))
        if candidates:
            _, lines, boxes, advance, height = min(candidates)
            return size, lines, boxes, advance, height
    raise ValueError(f"Headline needs a shorter editorial phrase to stay readable: {text!r}")


def render_card(headline, caption, ink):
    image = Image.new("RGB", (WIDTH, HEIGHT), ink)
    with Image.open(ASSETS / "lincoln-stovepipe.png") as source:
        profile = source.convert("RGBA")
    profile = profile.resize((132, 184), Image.Resampling.LANCZOS)
    image.paste(profile, (534, 22), profile)
    draw = ImageDraw.Draw(image)
    size, lines, boxes, advance, height = choose_layout(headline)
    y = TEXT_TOP + (TEXT_BOTTOM - TEXT_TOP - height) // 2
    bounds = []
    for line, box in zip(lines, boxes):
        x = (WIDTH - (box[2] - box[0])) // 2 - box[0]
        draw.text((x, y - box[1]), line, font=font(size), fill=PAPER)
        bounds.append([x + box[0], y, x + box[2], y + box[3] - box[1]])
        y += advance
    caption_face = font(72, utility=True)
    box = caption_face.getbbox(caption)
    if box[2] - box[0] > TEXT_RIGHT - TEXT_LEFT:
        raise ValueError(f"Caption exceeds the crop-safe width: {caption}")
    x = (WIDTH - (box[2] - box[0])) // 2 - box[0]
    draw.text((x, 552 - box[1]), caption, font=caption_face, fill=PAPER)
    bounds.append([x + box[0], 552, x + box[2], 552 + box[3] - box[1]])
    return image, {"font_size": size, "lines": lines, "text_bounds": bounds, "ink": ink}


def image_jobs(entries, headlines):
    yield "site", None, SITE_HEADLINE, SITE_CAPTION, INKS[0]
    for entry in entries:
        ink = INKS[(entry["month"] - 1) % len(INKS)]
        yield entry["mmdd"], entry, headlines[entry["mmdd"]]["headline"], entry["display_date"], ink


def generate(entries, headlines, output_root=ROOT, check=False):
    validate_headlines(entries, headlines)
    directory = Path(output_root) / IMAGE_DIRECTORY
    manifest_path = directory / "manifest.json"
    fingerprint = inputs_fingerprint()
    stored = json.loads(manifest_path.read_text()) if check and manifest_path.exists() else None
    if check and (stored is None or stored.get("inputs_sha256") != fingerprint):
        raise ValueError("Sharing images are missing or stale; run tools/generate_share_images.py")
    records = {}
    for key, entry, headline, caption, ink in image_jobs(entries, headlines):
        image, layout = render_card(headline, caption, ink)
        name = image_filename(entry)
        path = directory / name
        pixels = digest(image.tobytes())
        if check:
            if not path.is_file():
                raise ValueError(f"Missing sharing image: {path}")
            with Image.open(path) as existing:
                if existing.size != (WIDTH, HEIGHT) or digest(existing.convert("RGB").tobytes()) != pixels:
                    raise ValueError(f"Sharing image does not match its headline or layout: {path}")
        else:
            directory.mkdir(parents=True, exist_ok=True)
            image.save(path, optimize=True)
        records[key] = {
            "file": name, "headline": headline, "caption": caption, **layout,
            "pixels_sha256": pixels, "png_sha256": digest(path.read_bytes()),
        }
    manifest = {
        "version": IMAGE_VERSION, "width": WIDTH, "height": HEIGHT,
        "inputs_sha256": fingerprint, "images": records,
    }
    if check:
        if manifest != stored:
            raise ValueError("Sharing image manifest is stale")
        if {path.name for path in directory.glob("*.png")} != {item["file"] for item in records.values()}:
            raise ValueError("Unexpected sharing image files in the active version")
    else:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify every committed image without writing")
    args = parser.parse_args()
    entries = json.loads((ROOT / "data/entries.json").read_text(encoding="utf-8"))
    manifest = generate(entries, load_headlines(), check=args.check)
    print(f"{'Verified' if args.check else 'Generated'} {len(manifest['images'])} static sharing images in {IMAGE_DIRECTORY}/")


if __name__ == "__main__":
    main()
