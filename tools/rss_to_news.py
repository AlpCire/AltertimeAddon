#!/usr/bin/env python3
from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

WOW_CATEGORY_KEYWORDS = {
    "wow", "world of warcraft", "retail", "classic", "midnight",
    "the war within", "mists of pandaria classic", "addons", "warcraft"
}

USER_AGENT = "AlterTimeAddonGenerator/0.3.5"


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


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def parse_date(value: str) -> int:
    try:
        dt = email.utils.parsedate_to_datetime(value)
        return int(dt.timestamp())
    except Exception:
        return int(time.time())


def text(node: ET.Element | None) -> str:
    return html.unescape(node.text).strip() if node is not None and node.text else ""


def is_wow(title: str, categories: list[str]) -> bool:
    haystack = (title + " " + " ".join(categories)).lower()
    return any(keyword in haystack for keyword in WOW_CATEGORY_KEYWORDS)


def strip_html(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.I | re.S)
    value = re.sub(r"<style[^>]*>.*?</style>", "", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", "", value)
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
        "ü": "u", "ñ": "n", "ç": "c",
    }

    for src, dst in replacements.items():
        value = value.replace(src, dst)

    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:80] or "noticia"


def build_news_item(item: ET.Element) -> NewsItem | None:
    title = text(item.find("title"))
    url = text(item.find("link"))
    pub = parse_date(text(item.find("pubDate")))
    cats = [text(c) for c in item.findall("category") if text(c)]

    if not title or not url:
        return None

    if not is_wow(title, cats):
        return None

    desc = strip_html(text(item.find("description")))
    guid = text(item.find("guid")) or url

    return NewsItem(
        id=hashlib.md5(guid.encode("utf-8")).hexdigest()[:10],
        slug=slugify(title),
        title=title,
        excerpt=desc,
        author="AlterTime",
        published_at=pub,
        categories=cats or ["Retail"],
        url=url,
        body=[{"type": "paragraph", "text": desc}],
    )


def parse_rss(raw_xml: bytes, limit: int, max_age_days: int) -> list[NewsItem]:
    root = ET.fromstring(raw_xml)
    channel = root.find("channel")

    if channel is None:
        raise RuntimeError("RSS inválido: falta nodo <channel>")

    now = int(time.time())
    max_age = max_age_days * 86400

    print(f"[DEBUG] Fecha actual runner UTC: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now))}")
    print(f"[DEBUG] max_age_days: {max_age_days}")

    all_wow_items: list[NewsItem] = []
    recent_items: list[NewsItem] = []

    for item in channel.findall("item"):
        built = build_news_item(item)

        if built is None:
            title = text(item.find("title"))
            print(f"[SKIP] No WoW o inválida: {title[:80]}")
            continue

        pub_text = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(built.published_at))
        age_seconds = now - built.published_at
        age_days = age_seconds / 86400

        print(f"[RSS] {pub_text} | age={age_days:.2f}d | {built.title[:90]}")

        all_wow_items.append(built)

        if built.published_at > now + 86400:
            print(f"[SKIP] Fecha futura: {built.title[:80]}")
            continue

        if max_age_days > 0 and age_seconds > max_age:
            print(f"[SKIP] Demasiado antigua: {built.title[:80]}")
            continue

        recent_items.append(built)

    all_wow_items.sort(key=lambda x: x.published_at, reverse=True)
    recent_items.sort(key=lambda x: x.published_at, reverse=True)

    if max_age_days > 0 and recent_items:
        print(f"[OK] Usando {len(recent_items)} noticias recientes.")
        return recent_items[:limit] if limit > 0 else recent_items

    if max_age_days > 0 and not recent_items:
        print("[WARN] No hay noticias recientes según pubDate del RSS.")
        print("[WARN] Fallback activado: usando últimas noticias WoW disponibles sin filtro de fecha.")

    fallback = all_wow_items[:limit] if limit > 0 else all_wow_items

    if not fallback:
        raise RuntimeError("No se encontraron noticias WoW en el RSS.")

    return fallback


def render(items: list[NewsItem]) -> str:
    out = [
        "local ADDON_NAME, ns = ...",
        "",
        "-- Generado automáticamente por tools/rss_to_news.py.",
        "-- No editar a mano salvo emergencia.",
        f"ns.NewsGeneratedAt = {int(time.time())}",
        'ns.NewsSource = "rss"',
        "",
        "ns.News = {",
    ]

    for n in items:
        out += [
            "    {",
            f"        id = {lua_escape(n.id)},",
            f"        slug = {lua_escape(n.slug)},",
            f"        title = {lua_escape(n.title)},",
            f"        excerpt = {lua_escape(n.excerpt)},",
            f"        author = {lua_escape(n.author)},",
            f"        publishedAt = {n.published_at},",
            "        categories = { " + ", ".join(lua_escape(c) for c in n.categories) + " },",
            f"        url = {lua_escape(n.url)},",
            "        cover = nil,",
            "        body = {",
            f"            {{ type = \"paragraph\", text = {lua_escape(n.excerpt)} }},",
            "        },",
            "    },",
        ]

    out += ["}", ""]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rss", default="https://altertime.es/feed?rss")
    parser.add_argument("--output", default="Data/NewsData.lua")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-age-days", type=int, default=7)
    parser.add_argument("--media-dir", default="Media")
    parser.add_argument("--images", action="store_true")
    args = parser.parse_args()

    raw = fetch_url(args.rss)
    items = parse_rss(raw, args.limit, args.max_age_days)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(items), encoding="utf-8", newline="\n")

    print(f"[OK] {len(items)} noticias generadas en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
