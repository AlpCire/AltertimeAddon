#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request


def main() -> int:
    token = os.environ.get("CF_API_TOKEN")
    if not token:
        raise RuntimeError("Falta CF_API_TOKEN")

    url = "https://wow.curseforge.com/api/game/versions"

    req = urllib.request.Request(
        url,
        headers={
            "X-Api-Token": token,
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))

    for item in data:
        name = str(item.get("name", ""))
        if name.startswith("12.0.") or name == "12.0.5":
            print(item)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
