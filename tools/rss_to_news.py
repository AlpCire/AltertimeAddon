#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import mimetypes
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

try:
    from PIL import Image
except Exception:
    Image = None


USER_AGENT = "AlterTimeAddonGenerator/0.4.0 (+https://altertime.es)"

WOW_CATEGORY_KEYWORDS = {
    "retail",
    "classic",
    "midnight",
    "world of warcraft",
    "warcraft",
    "wow",
    "addons",
    "ayuda y addons",
    "mazmorras",
    "bandas",
    "coleccionables",
    "monturas",
    "reino de pruebas",
    "noticias blizzard",
    "blizzard",
}

EXCLUDED_KEYWORDS = {
    "diablo",
    "hearthstone",
    "rumble",
    "overwatch",
    "starcraft",
}


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
    relative_time: str = ""
    cover: str | None = None
    body: list[dict] = field(default_factory=list)
    image_url: str | None = None


def fetch_url(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,image/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def strip_tags(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.I | re.S)
    value = re.sub(r"<style[^>]*>.*?</style>", "", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def lua_escape(value: str) -> str:
    value = value or ""
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    value = value.replace("\r", "")
    value = value.replace("\n", "\\n")
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
        "¿": "",
        "¡": "",
    }

    for src, dst in replacements.items():
        value = value.replace(src, dst)

    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:90] or "noticia"


def absolutize(url: str, base_url: str) -> str:
    return urllib.parse.urljoin(base_url, html.unescape(url or "").strip())


def parse_relative_time(value: str) -> int:
    now = int(time.time())
    value = (value or "").lower().strip()

    match = re.search(r"hace\s+(\d+)\s+min", value)
    if match:
        return now - int(match.group(1)) * 60

    match = re.search(r"hace\s+(\d+)\s+hora", value)
    if match:
        return now - int(match.group(1)) * 3600

    match = re.search(r"hace\s+(\d+)\s+d[ií]a", value)
    if match:
        return now - int(match.group(1)) * 86400

    match = re.search(r"hace\s+(\d+)\s+semana", value)
    if match:
        return now - int(match.group(1)) * 7 * 86400

    return now


def is_wow_item(title: str, categories: list[str]) -> bool:
    haystack = (title + " " + " ".join(categories)).lower()

    if any(excluded in haystack for excluded in EXCLUDED_KEYWORDS):
        if not any(force in haystack for force in ("wow", "warcraft", "world of warcraft", "blizzard")):
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
    return img.resize((max_width, max(1, int(img.height * ratio))), Image.LANCZOS)


def download_and_convert_image(
    url: str,
    slug: str,
    media_dir: Path,
    max_cover_width: int,
) -> ImageAsset | None:
    if not url:
        return None

    raw_dir = media_dir / "_raw"
    target_dir = media_dir / "Covers"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    base_name = f"{slug}_cover_{digest}"

    raw_path = raw_dir / f"{base_name}{image_extension(url)}"
    tga_path = target_dir / f"{base_name}.tga"

    try:
        raw_path.write_bytes(fetch_url(url))
    except Exception as exc:
        print(f"[WARN] No se pudo descargar imagen {url}: {exc}", file=sys.stderr)
        return None

    if Image is None:
        print("[WARN] Pillow no está instalado; no se generan TGA.", file=sys.stderr)
        return None

    try:
        with Image.open(raw_path) as img:
            img = img.convert("RGBA")
            img = resize_image(img, max_cover_width)
            width, height = img.size
            img.save(tga_path)
    except Exception as exc:
        print(f"[WARN] No se pudo convertir imagen {raw_path}: {exc}", file=sys.stderr)
        return None

    relative = tga_path.relative_to(media_dir.parent)
    lua_path = "Interface\\AddOns\\AltertimeAddon\\" + "\\".join(relative.parts)

    return ImageAsset(url, str(tga_path), lua_path, width, height)


def clean_media(media_dir: Path) -> None:
    for folder in ["Covers", "Inline", "_raw"]:
        path = media_dir / folder

        if not path.exists():
            continue

        for file in path.rglob("*"):
            if file.is_file() and file.name != ".gitkeep":
                file.unlink()


def find_cover_near_link(page_html: str, href: str, base_url: str) -> str | None:
    idx = page_html.find(href)
    if idx < 0:
        return None

    start = max(0, idx - 3500)
    end = min(len(page_html), idx + 3500)
    chunk = page_html[start:end]

    img_matches = list(
        re.finditer(
            r'<img[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']',
            chunk,
            flags=re.I,
        )
    )

    if not img_matches:
        return None

    image_url = img_matches[-1].group(1)

    if "login" in image_url.lower() or "avatar" in image_url.lower():
        return None

    return absolutize(image_url, base_url)


def parse_homepage(home_html: str, base_url: str, limit: int, max_age_days: int) -> list[NewsItem]:
    link_pattern = re.compile(
        r'<a[^>]+href=["\'](?P<href>/article/[^"\']+)["\'][^>]*>(?P<body>.*?)</a>',
        flags=re.I | re.S,
    )

    seen: set[str] = set()
    items: list[NewsItem] = []
    now = int(time.time())

    for match in link_pattern.finditer(home_html):
        href = html.unescape(match.group("href"))
        link_body = match.group("body")
        clean = strip_tags(link_body)

        if href in seen:
            continue

        seen.add(href)

        if not clean:
            continue

        metadata_match = re.search(
            r"(?P<author>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_ -]+)\s+"
            r"(?P<relative>hace\s+\d+\s+(?:minutos?|horas?|d[ií]as?|semanas?))\s+"
            r"(?P<cats>.+)$",
            clean,
            flags=re.I,
        )

        if metadata_match:
            author = metadata_match.group("author").strip()
            relative_time = metadata_match.group("relative").strip()
            cats_text = metadata_match.group("cats").strip()
            text_before_meta = clean[: metadata_match.start()].strip()
        else:
            author = "AlterTime"
            relative_time = ""
            cats_text = ""
            text_before_meta = clean

        categories = [
            c.strip()
            for c in re.split(r",|·|\|", cats_text)
            if c.strip()
        ]

        title = text_before_meta
        excerpt = ""

        if " ¡" in text_before_meta:
            title, excerpt = text_before_meta.split(" ¡", 1)
            excerpt = "¡" + excerpt
        elif ". " in text_before_meta and len(text_before_meta) > 140:
            title, excerpt = text_before_meta.split(". ", 1)
            title += "."
        else:
            title = text_before_meta

        title = title.strip()
        excerpt = excerpt.strip()

        if not excerpt:
            excerpt = title

        if not is_wow_item(title, categories):
            print(f"[SKIP] No WoW portada: {title[:90]} | cats={categories}")
            continue

        published_at = parse_relative_time(relative_time)

        if max_age_days > 0 and now - published_at > max_age_days * 86400:
            print(f"[SKIP] Antigua portada: {title[:90]} | {relative_time}")
            continue

        url = absolutize(href, base_url)
        slug = slugify(urllib.parse.urlparse(url).path.strip("/").split("/")[-1] or title)
        cover_url = find_cover_near_link(home_html, href, base_url)

        print(f"[HOME] {relative_time or 'sin fecha'} | {categories} | {title[:100]}")

        items.append(
            NewsItem(
                id=hashlib.sha1(url.encode("utf-8")).hexdigest()[:12],
                slug=slug,
                title=title,
                excerpt=excerpt,
                author=author,
                published_at=published_at,
                categories=categories or ["Retail"],
                url=url,
                relative_time=relative_time,
                image_url=cover_url,
                body=[
                    {"type": "paragraph", "text": excerpt},
                    {"type": "paragraph", "text": f"Publicado en AlterTime: {relative_time or 'fecha no disponible'}"},
                ],
            )
        )

        if limit > 0 and len(items) >= limit:
            break

    if not items:
        raise RuntimeError("No se encontraron noticias WoW en la portada de AlterTime.")

    return items


def hydrate_images(items: list[NewsItem], media_dir: Path, images: bool, max_cover_width: int) -> list[NewsItem]:
    for item in items:
        if images and item.image_url:
            asset = download_and_convert_image(item.image_url, item.slug, media_dir, max_cover_width)
            if asset:
                item.cover = asset.lua_path

    return items


def render_lua(items: list[NewsItem]) -> str:
    lines = [
        "local ADDON_NAME, ns = ...",
        "",
        "-- Generado automáticamente por tools/rss_to_news.py.",
        "-- Fuente principal: portada AlterTime.",
        "-- No editar a mano salvo emergencia.",
        f"ns.NewsGeneratedAt = {int(time.time())}",
        'ns.NewsSource = "homepage"',
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
            lines.append(
                "            { type = "
                + lua_escape(block.get("type", "paragraph"))
                + ", text = "
                + lua_escape(block.get("text", ""))
                + " },"
            )

        lines.extend(["        },", "    },"])

    lines.extend(["}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--homepage", default="https://altertime.es/")
    parser.add_argument("--output", default="Data/NewsData.lua")
    parser.add_argument("--media-dir", default="Media")
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-age-days", type=int, default=7)
    parser.add_argument("--max-cover-width", type=int, default=768)

    # Compatibilidad: el workflow puede seguir pasando --rss sin romper.
    parser.add_argument("--rss", default="")
    args = parser.parse_args()

    media_dir = Path(args.media_dir)

    if args.images:
        clean_media(media_dir)

    html_doc = fetch_url(args.homepage).decode("utf-8", errors="ignore")
    items = parse_homepage(html_doc, args.homepage, args.limit, args.max_age_days)
    items = hydrate_images(items, media_dir, args.images, args.max_cover_width)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_lua(items), encoding="utf-8", newline="\n")

    print(f"[OK] Generadas {len(items)} noticias desde portada en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
