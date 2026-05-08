#!/usr/bin/env python3
from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import mimetypes
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image
except Exception:
    Image = None


WOW_CATEGORY_KEYWORDS = {
    "wow",
    "world of warcraft",
    "retail",
    "classic",
    "midnight",
    "the war within",
    "mists of pandaria classic",
    "addons",
    "ayuda y addons",
    "warcraft",
}

EXCLUDED_CATEGORY_KEYWORDS = {
    "diablo",
    "overwatch",
    "hearthstone",
    "starcraft",
}

USER_AGENT = "AlterTimeAddonGenerator/0.3.3 (+https://altertime.es)"


@dataclass
class ImageAsset:
    source_url: str
    local_path: str
    lua_path: str
    width: int | None = None
    height: int | None = None


@dataclass
class NewsItem:
    id: str
    slug: str
    title: str
    excerpt: str
    author: str
    published_at: int
    categories: list[str]
    url: str
    cover: str | None = None
    body: list[dict] = field(default_factory=list)


def fetch_url(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, text/html, image/*",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def text_content(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return html.unescape(node.text).strip()


def is_bad_text(value: str) -> bool:
    lower = (value or "").lower()

    bad_fragments = [
        "background-repeat",
        "background-position",
        "background-size",
        "background-origin",
        "linear-gradient",
        "rgba(",
        "url(",
        "class=",
        "style=",
        "<script",
        "<style",
        "window.",
        "document.",
    ]

    return any(fragment in lower for fragment in bad_fragments)


def strip_html(value: str) -> str:
    value = html.unescape(value or "")

    value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.I | re.S)
    value = re.sub(r"<style[^>]*>.*?</style>", "", value, flags=re.I | re.S)
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)

    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n\n", value, flags=re.I)
    value = re.sub(r"<li[^>]*>", "\n• ", value, flags=re.I)
    value = re.sub(r"</li\s*>", "\n", value, flags=re.I)
    value = re.sub(r"</h[1-6]\s*>", "\n\n", value, flags=re.I)
    value = re.sub(r"</div\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)

    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)

    lines: list[str] = []
    for line in value.splitlines():
        line = line.strip()

        if not line:
            lines.append("")
            continue

        if is_bad_text(line):
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def lua_escape(value: str) -> str:
    value = value or ""
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    value = value.replace("\r", "").replace("\n", "\\n")
    return f'"{value}"'


def slugify(value: str) -> str:
    value = html.unescape(value or "").lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "ç": "c",
    }

    for src, dst in replacements.items():
        value = value.replace(src, dst)

    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:90] or "noticia"


def parse_date(value: str) -> int:
    if not value:
        return int(time.time())

    try:
        dt = email.utils.parsedate_to_datetime(value)
        return int(dt.timestamp())
    except Exception:
        return int(time.time())


def get_namespaces() -> dict[str, str]:
    return {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "media": "http://search.yahoo.com/mrss/",
    }


def absolutize(url: str, base_url: str) -> str:
    return urllib.parse.urljoin(base_url, html.unescape(url or "").strip())


def extract_image_urls(item: ET.Element, content_html: str, base_url: str) -> list[str]:
    ns = get_namespaces()
    urls: list[str] = []

    for media in item.findall("media:content", ns):
        if media.attrib.get("url"):
            urls.append(absolutize(media.attrib["url"], base_url))

    enclosure = item.find("enclosure")
    if enclosure is not None and enclosure.attrib.get("url"):
        mime = enclosure.attrib.get("type", "")
        if mime.startswith("image/"):
            urls.append(absolutize(enclosure.attrib["url"], base_url))

    for match in re.finditer(
        r'<img[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']',
        content_html or "",
        re.I,
    ):
        urls.append(absolutize(match.group(1), base_url))

    seen: set[str] = set()
    result: list[str] = []

    for url in urls:
        normalized = url.split("?")[0]
        if normalized not in seen:
            seen.add(normalized)
            result.append(url)

    return result


def is_wow_item(categories: Iterable[str], title: str) -> bool:
    cats = [c.lower() for c in categories]
    haystack = " ".join(cats) + " " + title.lower()

    if any(excluded in haystack for excluded in EXCLUDED_CATEGORY_KEYWORDS):
        if not any(k in haystack for k in ("wow", "warcraft", "world of warcraft")):
            return False

    return any(keyword in haystack for keyword in WOW_CATEGORY_KEYWORDS)


def image_extension(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()

    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tga", ".blp"}:
        return ext

    guessed = mimetypes.guess_extension(mimetypes.guess_type(path)[0] or "")
    return guessed or ".jpg"


def resize_image(img: Image.Image, max_width: int) -> Image.Image:
    if img.width <= max_width:
        return img

    ratio = max_width / img.width
    new_size = (max_width, max(1, int(img.height * ratio)))

    return img.resize(new_size, Image.LANCZOS)


def download_and_convert_image(
    url: str,
    slug: str,
    index: int,
    media_dir: Path,
    kind: str,
    max_cover_width: int,
    max_inline_width: int,
) -> ImageAsset | None:
    raw_dir = media_dir / "_raw"
    target_dir = media_dir / ("Covers" if kind == "cover" else "Inline")

    raw_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    base_name = f"{slug}_{index:02d}_{digest}"

    raw_path = raw_dir / f"{base_name}{image_extension(url)}"
    tga_path = target_dir / f"{base_name}.tga"

    try:
        if not raw_path.exists():
            raw_path.write_bytes(fetch_url(url))
    except Exception as exc:
        print(f"[WARN] No se pudo descargar imagen: {url} ({exc})", file=sys.stderr)
        return None

    if Image is None:
        print("[WARN] Pillow no está instalado; no se generan TGA.", file=sys.stderr)
        return None

    try:
        with Image.open(raw_path) as img:
            img = img.convert("RGBA")
            img = resize_image(img, max_cover_width if kind == "cover" else max_inline_width)

            width, height = img.size
            img.save(tga_path)
    except Exception as exc:
        print(f"[WARN] No se pudo convertir a TGA: {raw_path} ({exc})", file=sys.stderr)
        return None

    relative = tga_path.relative_to(media_dir.parent)
    lua_path = "Interface\\AddOns\\AltertimeAddon\\" + "\\".join(relative.parts)

    return ImageAsset(url, str(tga_path), lua_path, width, height)


def parse_body(content_html: str, description: str, assets: list[ImageAsset]) -> list[dict]:
    body: list[dict] = []

    text = strip_html(content_html or description)

    for raw in re.split(r"\n\s*\n", text):
        raw = raw.strip()

        if not raw:
            continue

        if len(raw) < 3:
            continue

        if is_bad_text(raw):
            continue

        if raw.startswith("• "):
            body.append({"type": "bullet", "text": raw[2:].strip()})
        elif len(raw) < 95 and not raw.endswith("."):
            body.append({"type": "heading", "text": raw})
        else:
            body.append({"type": "paragraph", "text": raw})

    for asset in assets:
        if asset.lua_path:
            body.append(
                {
                    "type": "image",
                    "path": asset.lua_path,
                    "width": min(asset.width or 720, 760),
                    "height": min(asset.height or 360, 430),
                }
            )

    return body[:50]


def clean_media(media_dir: Path) -> None:
    for folder in ["Covers", "Inline", "_raw"]:
        path = media_dir / folder

        if not path.exists():
            continue

        for file in path.rglob("*"):
            if file.is_file() and file.name != ".gitkeep":
                file.unlink()


def parse_rss(
    raw_xml: bytes,
    limit: int,
    media_dir: Path,
    download_images: bool,
    max_cover_width: int,
    max_inline_width: int,
    max_age_days: int,
) -> list[NewsItem]:
    root = ET.fromstring(raw_xml)
    ns = get_namespaces()
    channel = root.find("channel")

    if channel is None:
        raise RuntimeError("RSS sin nodo <channel>")

    candidates: list[NewsItem] = []
    now = int(time.time())

    for item in channel.findall("item"):
        title = text_content(item.find("title"))
        url = text_content(item.find("link"))
        guid = text_content(item.find("guid")) or url or title
        slug = slugify(urllib.parse.urlparse(url).path.strip("/").split("/")[-1] or title)
        item_id = hashlib.sha1(guid.encode("utf-8")).hexdigest()[:12]

        categories = [text_content(c) for c in item.findall("category") if text_content(c)]

        if not is_wow_item(categories, title):
            continue

        description = text_content(item.find("description"))
        content_node = item.find("content:encoded", ns)
        content_html = text_content(content_node)

        author = text_content(item.find("dc:creator", ns)) or "AlterTime"
        published_at = parse_date(text_content(item.find("pubDate")))

        if max_age_days > 0:
            max_age_seconds = max_age_days * 86400
            if now - published_at > max_age_seconds:
                continue

        excerpt = strip_html(description)
        if len(excerpt) > 190:
            excerpt = excerpt[:187].rstrip() + "..."

        image_urls = extract_image_urls(item, content_html or description, url)

        candidates.append(
            NewsItem(
                id=item_id,
                slug=slug,
                title=title,
                excerpt=excerpt,
                author=author,
                published_at=published_at,
                categories=categories or ["Retail"],
                url=url,
                cover=None,
                body=[],
            )
        )

        candidates[-1]._content_html = content_html  # type: ignore[attr-defined]
        candidates[-1]._description = description  # type: ignore[attr-defined]
        candidates[-1]._image_urls = image_urls  # type: ignore[attr-defined]

    candidates.sort(key=lambda n: n.published_at, reverse=True)

    if limit > 0:
        candidates = candidates[:limit]

    final_items: list[NewsItem] = []

    for candidate in candidates:
        image_urls = getattr(candidate, "_image_urls", [])
        content_html = getattr(candidate, "_content_html", "")
        description = getattr(candidate, "_description", "")

        cover_path = None
        inline_assets: list[ImageAsset] = []

        if download_images and image_urls:
            cover_asset = download_and_convert_image(
                image_urls[0],
                candidate.slug,
                1,
                media_dir,
                "cover",
                max_cover_width,
                max_inline_width,
            )

            if cover_asset:
                cover_path = cover_asset.lua_path

            for idx, image_url in enumerate(image_urls[1:3], start=2):
                asset = download_and_convert_image(
                    image_url,
                    candidate.slug,
                    idx,
                    media_dir,
                    "inline",
                    max_cover_width,
                    max_inline_width,
                )

                if asset:
                    inline_assets.append(asset)

        body = parse_body(content_html, description, inline_assets)

        if not body and candidate.excerpt:
            body = [{"type": "paragraph", "text": candidate.excerpt}]

        final_items.append(
            NewsItem(
                id=candidate.id,
                slug=candidate.slug,
                title=candidate.title,
                excerpt=candidate.excerpt,
                author=candidate.author,
                published_at=candidate.published_at,
                categories=candidate.categories,
                url=candidate.url,
                cover=cover_path,
                body=body,
            )
        )

    return final_items


def render_lua(items: list[NewsItem]) -> str:
    lines = [
        "local ADDON_NAME, ns = ...",
        "",
        "-- Generado automáticamente por tools/rss_to_news.py.",
        "-- No editar a mano salvo emergencia.",
        f"ns.NewsGeneratedAt = {int(time.time())}",
        'ns.NewsSource = "rss"',
        "",
        "ns.News = {",
    ]

    for item in items:
        lines.extend(
            [
                "    {",
                f"        id = {lua_escape(item.id)},",
                f"        slug = {lua_escape(item.slug)},",
                f"        title = {lua_escape(item.title)},",
                f"        excerpt = {lua_escape(item.excerpt)},",
                f"        author = {lua_escape(item.author)},",
                f"        publishedAt = {item.published_at},",
                "        categories = { " + ", ".join(lua_escape(c) for c in item.categories) + " },",
                f"        url = {lua_escape(item.url)},",
                f"        cover = {lua_escape(item.cover) if item.cover else 'nil'},",
                "        body = {",
            ]
        )

        for block in item.body:
            block_type = block.get("type", "paragraph")

            if block_type == "image":
                lines.append(
                    "            { type = \"image\", path = "
                    + lua_escape(block.get("path", ""))
                    + f", width = {int(block.get('width') or 720)}, height = {int(block.get('height') or 360)}"
                    + " },"
                )
            else:
                lines.append(
                    "            { type = "
                    + lua_escape(block_type)
                    + ", text = "
                    + lua_escape(block.get("text", ""))
                    + " },"
                )

        lines.extend(
            [
                "        },",
                "    },",
            ]
        )

    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rss", default="https://altertime.es/feed?rss")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", default="Data/NewsData.lua")
    parser.add_argument("--media-dir", default="Media")
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--max-cover-width", type=int, default=768)
    parser.add_argument("--max-inline-width", type=int, default=760)
    parser.add_argument("--max-age-days", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    media_dir = Path(args.media_dir)

    if args.images:
        clean_media(media_dir)

    raw = fetch_url(args.rss)

    items = parse_rss(
        raw,
        args.limit,
        media_dir,
        args.images,
        args.max_cover_width,
        args.max_inline_width,
        args.max_age_days,
    )

    lua = render_lua(items)

    if args.dry_run:
        print(lua)
        return 0

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(lua, encoding="utf-8", newline="\n")

    print(f"Generadas {len(items)} noticias en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
