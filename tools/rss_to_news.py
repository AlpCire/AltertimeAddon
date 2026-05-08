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

try:
    from PIL import Image
except Exception:
    Image = None


WOW_CATEGORY_KEYWORDS = {
    "wow",
    "world of warcraft",
    "warcraft",
    "retail",
    "classic",
    "midnight",
    "the war within",
    "mists of pandaria classic",
    "addons",
    "ayuda y addons",
    "blizzard",
}

USER_AGENT = "AlterTimeAddonGenerator/0.3.6 (+https://altertime.es)"


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
    image_urls: list[str] = field(default_factory=list)


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


def get_namespaces() -> dict[str, str]:
    return {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "media": "http://search.yahoo.com/mrss/",
        "atom": "http://www.w3.org/2005/Atom",
    }


def parse_date(value: str) -> int:
    value = (value or "").strip()
    if not value:
        return 0

    try:
        dt = email.utils.parsedate_to_datetime(value)
        return int(dt.timestamp())
    except Exception:
        pass

    known_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in known_formats:
        try:
            return int(time.mktime(time.strptime(value, fmt)))
        except Exception:
            continue

    return 0


def get_item_date(item: ET.Element) -> tuple[int, str]:
    ns = get_namespaces()

    candidates = [
        text_content(item.find("pubDate")),
        text_content(item.find("dc:date", ns)),
        text_content(item.find("atom:updated", ns)),
        text_content(item.find("updated")),
        text_content(item.find("published")),
    ]

    for raw in candidates:
        parsed = parse_date(raw)
        if parsed > 0:
            return parsed, raw

    return int(time.time()), "fallback_now"


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
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
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
    }

    for src, dst in replacements.items():
        value = value.replace(src, dst)

    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:90] or "noticia"


def is_wow_item(title: str, categories: list[str]) -> bool:
    haystack = (title + " " + " ".join(categories)).lower()
    return any(keyword in haystack for keyword in WOW_CATEGORY_KEYWORDS)


def absolutize(url: str, base_url: str) -> str:
    return urllib.parse.urljoin(base_url, html.unescape(url or "").strip())


def image_extension(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()

    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tga", ".blp"}:
        return ext

    guessed = mimetypes.guess_extension(mimetypes.guess_type(path)[0] or "")
    return guessed or ".jpg"


def extract_image_urls(item: ET.Element, content_html: str, description: str, base_url: str) -> list[str]:
    ns = get_namespaces()
    urls: list[str] = []

    for media in item.findall("media:content", ns):
        media_url = media.attrib.get("url")
        if media_url:
            urls.append(absolutize(media_url, base_url))

    for media in item.findall("media:thumbnail", ns):
        media_url = media.attrib.get("url")
        if media_url:
            urls.append(absolutize(media_url, base_url))

    enclosure = item.find("enclosure")
    if enclosure is not None and enclosure.attrib.get("url"):
        mime = enclosure.attrib.get("type", "")
        if mime.startswith("image/"):
            urls.append(absolutize(enclosure.attrib["url"], base_url))

    html_blob = (content_html or "") + "\n" + (description or "")

    for match in re.finditer(
        r'<img[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']',
        html_blob,
        re.I,
    ):
        urls.append(absolutize(match.group(1), base_url))

    seen: set[str] = set()
    result: list[str] = []

    for url in urls:
        if not url:
            continue

        normalized = url.split("?")[0]
        if normalized not in seen:
            seen.add(normalized)
            result.append(url)

    return result


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


def clean_media(media_dir: Path) -> None:
    for folder in ["Covers", "Inline", "_raw"]:
        path = media_dir / folder

        if not path.exists():
            continue

        for file in path.rglob("*"):
            if file.is_file() and file.name != ".gitkeep":
                file.unlink()


def parse_body(content_html: str, description: str, inline_assets: list[ImageAsset]) -> list[dict]:
    body: list[dict] = []
    text = strip_html(content_html or description)

    for raw in re.split(r"\n\s*\n", text):
        raw = raw.strip()

        if not raw:
            continue

        if len(raw) < 3:
            continue

        if len(raw) < 95 and not raw.endswith("."):
            body.append({"type": "heading", "text": raw})
        else:
            body.append({"type": "paragraph", "text": raw})

    for asset in inline_assets:
        body.append(
            {
                "type": "image",
                "path": asset.lua_path,
                "width": min(asset.width or 720, 760),
                "height": min(asset.height or 360, 430),
            }
        )

    return body[:50]


def parse_rss(
    raw_xml: bytes,
    limit: int,
    max_age_days: int,
) -> list[NewsItem]:
    root = ET.fromstring(raw_xml)
    ns = get_namespaces()
    channel = root.find("channel")

    if channel is None:
        raise RuntimeError("RSS inválido: falta nodo <channel>")

    now = int(time.time())
    max_age_seconds = max_age_days * 86400

    print(f"[DEBUG] Fecha runner UTC: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))}")
    print(f"[DEBUG] max_age_days: {max_age_days}")

    candidates: list[NewsItem] = []

    for item in channel.findall("item"):
        title = text_content(item.find("title"))
        url = text_content(item.find("link"))
        guid = text_content(item.find("guid")) or url or title
        categories = [text_content(c) for c in item.findall("category") if text_content(c)]

        published_at, raw_date = get_item_date(item)
        date_text = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(published_at))

        print(f"[RSS] {date_text} | raw={raw_date} | cats={categories} | {title[:90]}")

        if not title or not url:
            print("[SKIP] Sin título o URL")
            continue

        if not is_wow_item(title, categories):
            print(f"[SKIP] No WoW: {title[:90]}")
            continue

        if published_at > now + 86400:
            print(f"[SKIP] Fecha futura: {title[:90]}")
            continue

        if max_age_days > 0 and now - published_at > max_age_seconds:
            print(f"[SKIP] Antigua: {title[:90]}")
            continue

        description = text_content(item.find("description"))
        content_node = item.find("content:encoded", ns)
        content_html = text_content(content_node)

        excerpt = strip_html(description)
        if len(excerpt) > 190:
            excerpt = excerpt[:187].rstrip() + "..."

        image_urls = extract_image_urls(item, content_html, description, url)

        candidates.append(
            NewsItem(
                id=hashlib.sha1(guid.encode("utf-8")).hexdigest()[:12],
                slug=slugify(urllib.parse.urlparse(url).path.strip("/").split("/")[-1] or title),
                title=title,
                excerpt=excerpt,
                author=text_content(item.find("dc:creator", ns)) or "AlterTime",
                published_at=published_at,
                categories=categories or ["Retail"],
                url=url,
                body=[],
                image_urls=image_urls,
            )
        )

    candidates.sort(key=lambda n: n.published_at, reverse=True)

    if limit > 0:
        candidates = candidates[:limit]

    print(f"[DEBUG] Noticias candidatas finales: {len(candidates)}")

    if not candidates:
        raise RuntimeError("No hay noticias WoW válidas tras aplicar filtros. Revisa logs [RSS]/[SKIP].")

    return candidates


def hydrate_images_and_body(
    items: list[NewsItem],
    media_dir: Path,
    download_images: bool,
    max_cover_width: int,
    max_inline_width: int,
) -> list[NewsItem]:
    result: list[NewsItem] = []

    for item in items:
        cover_path = None
        inline_assets: list[ImageAsset] = []

        if download_images and item.image_urls:
            cover_asset = download_and_convert_image(
                item.image_urls[0],
                item.slug,
                1,
                media_dir,
                "cover",
                max_cover_width,
                max_inline_width,
            )

            if cover_asset:
                cover_path = cover_asset.lua_path

            for idx, image_url in enumerate(item.image_urls[1:3], start=2):
                asset = download_and_convert_image(
                    image_url,
                    item.slug,
                    idx,
                    media_dir,
                    "inline",
                    max_cover_width,
                    max_inline_width,
                )
                if asset:
                    inline_assets.append(asset)

        item.cover = cover_path
        item.body = parse_body(item.excerpt, item.excerpt, inline_assets)

        result.append(item)

    return result


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
            if block.get("type") == "image":
                lines.append(
                    "            { type = \"image\", path = "
                    + lua_escape(block.get("path", ""))
                    + f", width = {int(block.get('width') or 720)}, height = {int(block.get('height') or 360)}"
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
    parser.add_argument("--rss", default="https://altertime.es/feed?rss")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", default="Data/NewsData.lua")
    parser.add_argument("--media-dir", default="Media")
    parser.add_argument("--images", action="store_true")
    parser.add_argument("--max-age-days", type=int, default=14)
    parser.add_argument("--max-cover-width", type=int, default=768)
    parser.add_argument("--max-inline-width", type=int, default=760)
    args = parser.parse_args()

    media_dir = Path(args.media_dir)

    if args.images:
        clean_media(media_dir)

    raw_xml = fetch_url(args.rss)
    items = parse_rss(raw_xml, args.limit, args.max_age_days)
    items = hydrate_images_and_body(
        items,
        media_dir,
        args.images,
        args.max_cover_width,
        args.max_inline_width,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_lua(items), encoding="utf-8", newline="\n")

    print(f"[OK] Generadas {len(items)} noticias en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
