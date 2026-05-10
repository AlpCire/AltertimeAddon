#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.parse
import mimetypes
from pathlib import Path


def encode_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = "----AlterTimeCurseForgeUploadBoundary"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(str(value).encode())
        body.extend(b"\r\n")

    for name, file_path in files.items():
        path = Path(file_path)
        mime = mimetypes.guess_type(path.name)[0] or "application/zip"
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {mime}\r\n\r\n".encode())
        body.extend(path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), boundary


def main() -> int:
    token = os.environ.get("CF_API_TOKEN")
    project_id = os.environ.get("CF_PROJECT_ID")

    if not token:
        raise RuntimeError("Falta secret CF_API_TOKEN")
    if not project_id:
        raise RuntimeError("Falta secret CF_PROJECT_ID")

    dist = Path("dist")
    zips = sorted(dist.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not zips:
        raise RuntimeError("No se encontró ningún ZIP en dist/")

    zip_path = zips[0]

    # IMPORTANTE:
    # Los IDs de gameVersions hay que confirmarlos en CurseForge.
    # Podemos empezar con metadata mínima y ajustar después.
    metadata = {
        "changelog": "Actualización automática de noticias de AlterTime.",
        "changelogType": "text",
        "displayName": zip_path.stem,
        "releaseType": os.environ.get("CF_RELEASE_TYPE", "alpha"),
        "gameVersions": [120005],
    }

    body, boundary = encode_multipart(
        fields={"metadata": json.dumps(metadata)},
        files={"file": zip_path},
    )

    url = f"https://www.curseforge.com/api/projects/{project_id}/upload-file"

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "X-Api-Token": token,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = response.read().decode("utf-8", errors="replace")
            print(f"[OK] Subida CurseForge completada: {payload}")
            return 0
    except urllib.error.HTTPError as exc:
        print(f"[ERROR] CurseForge HTTP {exc.code}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
