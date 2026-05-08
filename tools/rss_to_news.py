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
    "wow", "world of warcraft", "retail", "classic", "midnight",
    "the war within", "mists of pandaria classic", "addons",
    "warcraft"
}

USER_AGENT = "AlterTimeAddonGenerator/0.3.4"


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
    return urllib.request.urlopen(req, timeout=20).read()


def parse_date(value: str) -> int:
    try:
        dt = email.utils.parsedate_to_datetime(value)
        return int(dt.timestamp())
    except Exception:
        return int(time.time())


def text(node):
    return html.unescape(node.text).strip() if node is not None and node.text else ""


def is_wow(title: str, categories: list[str]) -> bool:
    hay = (title + " " + " ".join(categories)).lower()
    return any(k in hay for k in WOW_CATEGORY_KEYWORDS)


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:80]


def download_image(url: str, path: Path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch_url(url))
    except:
        pass


def parse_rss(raw_xml: bytes, limit: int, max_age_days: int) -> list[NewsItem]:
    root = ET.fromstring(raw_xml)
    channel = root.find("channel")

    now = int(time.time())
    max_age = max_age_days * 86400

    print(f"[DEBUG] Fecha actual: {time.strftime('%Y-%m-%d', time.gmtime(now))}")

    items: list[NewsItem] = []

    for item in channel.findall("item"):
        title = text(item.find("title"))
        url = text(item.find("link"))
        pub = parse_date(text(item.find("pubDate")))

        print(f"[DEBUG] Noticia: {title[:40]}... Fecha: {time.strftime('%Y-%m-%d', time.gmtime(pub))}")

        # ❌ futura → ignorar
        if pub > now + 86400:
            print("[SKIP] futura")
            continue

        # ❌ vieja → ignorar
        if max_age_days > 0 and (now - pub > max_age):
            print("[SKIP] demasiado antigua")
            continue

        cats = [text(c) for c in item.findall("category")]

        if not is_wow(title, cats):
            continue

        desc = strip_html(text(item.find("description")))

        items.append(
            NewsItem(
                id=hashlib.md5(url.encode()).hexdigest()[:10],
                slug=slugify(title),
                title=title,
                excerpt=desc,
                author="AlterTime",
                published_at=pub,
                categories=cats,
                url=url,
                body=[{"type": "paragraph", "text": desc}],
            )
        )

    items.sort(key=lambda x: x.published_at, reverse=True)

    if limit:
        items = items[:limit]

    # 🔴 CLAVE → evitar builds con basura
    if max_age_days > 0 and not items:
        raise RuntimeError("❌ No hay noticias recientes. El RSS no devuelve datos válidos.")

    return items


def render(items: list[NewsItem]) -> str:
    out = [
        "local ADDON_NAME, ns = ...",
        "",
        f"ns.NewsGeneratedAt = {int(time.time())}",
        'ns.NewsSource = "rss"',
        "",
        "ns.News = {",
    ]

    for n in items:
        out += [
            "  {",
            f'    title = "{n.title}",',
            f'    excerpt = "{n.excerpt}",',
            f'    url = "{n.url}",',
            f'    publishedAt = {n.published_at},',
            "    body = {",
            f'      {{ type = "paragraph", text = "{n.excerpt}" }},',
            "    },",
            "  },",
        ]

    out += ["}", ""]
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rss", default="https://altertime.es/feed?rss")
    p.add_argument("--output", default="Data/NewsData.lua")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--max-age-days", type=int, default=7)
    args = p.parse_args()

    raw = fetch_url(args.rss)

    items = parse_rss(raw, args.limit, args.max_age_days)

    lua = render(items)

    Path(args.output).write_text(lua, encoding="utf-8")

    print(f"[OK] {len(items)} noticias generadas")


if __name__ == "__main__":
    main()
