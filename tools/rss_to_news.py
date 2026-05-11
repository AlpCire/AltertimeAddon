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

from bs4 import BeautifulSoup

try:
    from PIL import Image
except Exception:
    Image = None


USER_AGENT = "AlterTimeAddonGenerator/0.4.7 (+https://altertime.es)"


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
    cover_url: str | None = None
    inline_image_urls: list[str] = field(default_factory=list)


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


def text_clean(value: str) -> str:
    value = html.unescape(value or "")
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
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ü": "u", "ñ": "n", "ç": "c", "¿": "", "¡": "",
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


def image_extension(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()

    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tga", ".blp"}:
        return ext

    guessed = mimetypes.guess_extension(mimetypes.guess_type(path)[0] or "")
    return guessed or ".jpg"


def is_bad_image_url(url: str) -> bool:
    lower = (url or "").lower()
    bad = [
        "avatar", "profile", "logo", "icon", "favicon", "emoji",
        "user", "placeholder", "login", "discord", "twitter", "x.com",
        "facebook", "youtube", "twitch", "calender", "calendar",
        "tag", "flag", "wowtoken", "blizzbucks",
    ]
    return any(x in lower for x in bad)


def resize_image(img: Image.Image, max_width: int) -> Image.Image:
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    return img.resize((max_width, max(1, int(img.height * ratio))), Image.LANCZOS)


def download_and_convert_image(
    url: str,
    slug: str,
    media_dir: Path,
    folder: str,
    index: int,
    max_width: int,
    min_width: int = 300,
    min_height: int = 120,
) -> ImageAsset | None:
    if not url or is_bad_image_url(url):
        return None

    raw_dir = media_dir / "_raw"
    target_dir = media_dir / folder
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    base_name = f"{slug}_{index:02d}_{digest}"

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

            if img.width < min_width or img.height < min_height:
                print(f"[SKIP IMG] Imagen pequeña: {url} ({img.width}x{img.height})")
                return None

            img = resize_image(img, max_width)
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


def get_meta_image(soup: BeautifulSoup, base_url: str) -> str | None:
    for selector in [
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
        'meta[property="twitter:image"]',
    ]:
        node = soup.select_one(selector)
        if node and node.get("content"):
            url = absolutize(node["content"], base_url)
            if not is_bad_image_url(url):
                return url
    return None


def should_stop_article_text(text: str) -> bool:
    lower = text_clean(text).lower()
    stop_markers = [
        "fuente:",
        "compartir",
        "mercado negro",
        "ficha de wow",
        "afijos míticas",
        "redes sociales",
        "términos y condiciones",
        "privacy policy",
        "por favor, desactiva tu adblock",
    ]
    return any(marker in lower for marker in stop_markers)


def should_skip_text(text: str) -> bool:
    lower = text_clean(text).lower()

    if len(lower) < 3:
        return True

    bad = [
        "loading...",
        "creación de contenido",
        "inicia sesión",
        "adblock",
        "privacy policy",
        "términos y condiciones",
        "realizado por raider.io",
        "hecho con",
        "copyright",
    ]

    return any(x in lower for x in bad)


def find_article_h1(soup: BeautifulSoup):
    h1s = soup.find_all("h1")
    for h1 in h1s:
        text = text_clean(h1.get_text(" "))
        if len(text) > 20 and not should_skip_text(text):
            return h1
    return None


def extract_article_body(article_html: str, article_url: str) -> tuple[str, str, list[dict], list[str]]:
    soup = BeautifulSoup(article_html, "html.parser")

    for node in soup.select("script, style, nav, header, footer, iframe, noscript, form"):
        node.decompose()

    cover_url = get_meta_image(soup, article_url)

    h1 = find_article_h1(soup)
    if not h1:
        return "", cover_url or "", [], []

    title = text_clean(h1.get_text(" "))
    blocks: list[dict] = []
    inline_images: list[str] = []
    seen_text: set[str] = set()

    for node in h1.find_all_next(["h2", "h3", "p", "li", "img"]):
        if node.name == "img":
            src = (
                node.get("src")
                or node.get("data-src")
                or node.get("data-lazy-src")
                or node.get("data-original")
            )

            if src:
                url = absolutize(src, article_url)
                if not is_bad_image_url(url) and url != cover_url and url not in inline_images:
                    inline_images.append(url)

            continue

        text = text_clean(node.get_text(" "))

        if should_stop_article_text(text):
            break

        if should_skip_text(text):
            continue

        if text in seen_text:
            continue

        seen_text.add(text)

        if node.name in {"h2", "h3"}:
            blocks.append({"type": "heading", "text": text})
        elif node.name == "li":
            blocks.append({"type": "bullet", "text": text})
        else:
            blocks.append({"type": "paragraph", "text": text})

        if len(blocks) >= 80:
            break

    return title, cover_url or "", blocks, inline_images[:4]


def parse_homepage(home_html: str, base_url: str, limit: int, max_age_days: int) -> list[NewsItem]:
    soup = BeautifulSoup(home_html, "html.parser")
    links = soup.select('a[href^="/article/"], a[href*="/article/"]')

    seen: set[str] = set()
    items: list[NewsItem] = []
    now = int(time.time())

    for link in links:
        href = link.get("href")
        if not href:
            continue

        parsed = urllib.parse.urlparse(absolutize(href, base_url))
        path = parsed.path

        if not path.startswith("/article/"):
            continue

        if path in seen:
            continue
        seen.add(path)

        text = text_clean(link.get_text(" "))
        if not text:
            continue

        relative_match = re.search(r"hace\s+\d+\s+(?:minutos?|horas?|d[ií]as?|semanas?)", text, re.I)
        relative_time = relative_match.group(0) if relative_match else ""

        published_at = parse_relative_time(relative_time)

        if max_age_days > 0 and now - published_at > max_age_days * 86400:
            continue

        categories = []
        for cat in [
            "Retail", "Classic", "Midnight", "Addons", "Ayuda y Addons",
            "Blizzard", "Hearthstone", "Rumble", "Housing", "Diablo",
            "Overwatch", "Starcraft", "Proyectos",
        ]:
            if re.search(rf"\b{re.escape(cat)}\b", text, re.I):
                categories.append(cat)

        title = text
        if relative_match:
            title = text[:relative_match.start()].strip()

        title = re.sub(r"^(Pixpo|Hols|AlterTime|Blizzard)\s+", "", title).strip()
        title = re.sub(r"\s+", " ", title)

        if len(title) > 220:
            title = title[:220].rstrip() + "..."

        url = absolutize(path, base_url)
        slug = slugify(urllib.parse.urlparse(url).path.strip("/").split("/")[-1] or title)

        print(f"[HOME] {relative_time or 'sin fecha'} | {categories} | {title[:100]}")

        try:
            article_html = fetch_url(url).decode("utf-8", errors="ignore")
            article_title, cover_url, body, inline_images = extract_article_body(article_html, url)
        except Exception as exc:
            print(f"[WARN] No se pudo leer artículo {url}: {exc}", file=sys.stderr)
            article_title, cover_url, body, inline_images = "", "", [], []

        if article_title:
            title = article_title

        excerpt = ""
        for block in body:
            if block.get("type") == "paragraph":
                excerpt = block.get("text", "")
                break

        if not excerpt:
            excerpt = title

        items.append(
            NewsItem(
                id=hashlib.sha1(url.encode("utf-8")).hexdigest()[:12],
                slug=slug,
                title=title,
                excerpt=excerpt[:260],
                author="AlterTime",
                published_at=published_at,
                categories=categories or ["AlterTime"],
                url=url,
                relative_time=relative_time,
                cover_url=cover_url,
                body=body or [{"type": "paragraph", "text": excerpt}],
                inline_image_urls=inline_images,
            )
        )

        if limit > 0 and len(items) >= limit:
            break

    if not items:
        raise RuntimeError("No se encontraron noticias recientes en la portada de AlterTime.")

    return items


def hydrate_images(items: list[NewsItem], media_dir: Path, images: bool, max_cover_width: int) -> list[NewsItem]:
    for item in items:
        if images and item.cover_url:
            asset = download_and_convert_image(
                item.cover_url,
                item.slug,
                media_dir,
                "Covers",
                1,
                max_cover_width,
                min_width=500,
                min_height=180,
            )
            if asset:
                item.cover = asset.lua_path

        if images and item.inline_image_urls:
            image_blocks: list[dict] = []

            for idx, url in enumerate(item.inline_image_urls[:3], start=2):
                asset = download_and_convert_image(
                    url,
                    item.slug,
                    media_dir,
                    "Inline",
                    idx,
                    760,
                    min_width=420,
                    min_height=160,
                )

                if asset:
                    image_blocks.append(
                        {
                            "type": "image",
                            "path": asset.lua_path,
                            "width": asset.width or 760,
                            "height": asset.height or 360,
                        }
                    )

            if image_blocks:
                item.body.extend(image_blocks)

    return items


def render_lua(items: list[NewsItem]) -> str:
    latest_stamp = max((item.published_at for item in items), default=0)
    news_signature = hashlib.sha1(
        "|".join(item.id for item in items).encode("utf-8")
    ).hexdigest()

    lines = [
        "local ADDON_NAME, ns = ...",
        "",
        "-- Generado automáticamente por tools/rss_to_news.py.",
        "-- Fuente principal: portada + artículo AlterTime.",
        "-- No editar a mano salvo emergencia.",
        f"ns.NewsGeneratedAt = {latest_stamp}",
        f"ns.NewsSignature = {lua_escape(news_signature)}",
        'ns.NewsSource = "homepage+article"',
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
            if block.get("type") == "image":
                lines.append(
                    "            { type = \"image\", path = "
                    + lua_escape(block.get("path", ""))
                    + f", width = {int(block.get('width') or 760)}, height = {int(block.get('height') or 360)}"
                    + " },"
                )
            else:
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
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--max-age-days", type=int, default=7)
    parser.add_argument("--max-cover-width", type=int, default=768)
    parser.add_argument("--rss", default="")
    args = parser.parse_args()

    media_dir = Path(args.media_dir)

    if args.images:
        clean_media(media_dir)

    home_html = fetch_url(args.homepage).decode("utf-8", errors="ignore")
    items = parse_homepage(home_html, args.homepage, args.limit, args.max_age_days)
    items = hydrate_images(items, media_dir, args.images, args.max_cover_width)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_lua(items), encoding="utf-8", newline="\n")

    print(f"[OK] Generadas {len(items)} noticias desde portada + artículo en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
