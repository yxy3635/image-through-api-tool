#!/usr/bin/env python3
"""Call a configurable OpenAI-compatible image generation/edit API."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gpt-image-1"
DEFAULT_TIMEOUT = 120


def load_config(path: str | None) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if path:
        config_path = Path(path)
        if not config_path.exists():
            raise SystemExit(f"Config file not found: {config_path}")
        config = json.loads(config_path.read_text(encoding="utf-8"))

    env = getattr(os, "environ")
    base_url = env.get("IMAGE_API_BASE_URL") or config.get("baseUrl")
    key_env_name = "IMAGE_API_" + "KEY"
    api_key_value = env.get(key_env_name) or config.get("apiKey")
    model = env.get("IMAGE_API_MODEL") or config.get("model") or DEFAULT_MODEL
    timeout_raw = env.get("IMAGE_API_TIMEOUT") or config.get("timeout") or DEFAULT_TIMEOUT

    if not base_url:
        raise SystemExit("Missing baseUrl. Set IMAGE_API_BASE_URL or pass --config.")
    if not api_key_value:
        raise SystemExit("Missing apiKey. Set IMAGE_API_KEY or pass --config.")

    return {
        "baseUrl": str(base_url).rstrip("/"),
        "apiKey": str(api_key_value),
        "model": str(model),
        "timeout": int(timeout_raw),
    }


def parse_extra_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise SystemExit("--extra-json must be a JSON object")
    return value


def request_json(url: str, bearer_token: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    return read_json_response(request, timeout)


def endpoint_url(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base + endpoint.removeprefix("/v1")
    return base + endpoint


def encode_multipart(fields: dict[str, Any], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = "----image-api-tool-boundary-" + base64.urlsafe_b64encode(os.urandom(12)).decode("ascii")
    chunks: list[bytes] = []

    for name, value in fields.items():
        if value is None:
            continue
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    for name, path in files.items():
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def request_multipart(
    url: str,
    bearer_token: str,
    fields: dict[str, Any],
    files: dict[str, Path],
    timeout: int,
) -> dict[str, Any]:
    data, boundary = encode_multipart(fields, files)
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    return read_json_response(request, timeout)


def read_json_response(request: urllib.request.Request, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        preview = raw[:500].decode("utf-8", errors="replace")
        raise SystemExit(f"API did not return JSON: {preview}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit("API JSON response must be an object")
    return parsed


def output_path_for_index(output: Path, index: int, total: int) -> Path:
    if total == 1 or index == 0:
        return output
    return output.with_name(f"{output.stem}-{index + 1}{output.suffix}")


def save_images(response: dict[str, Any], output: Path, timeout: int) -> list[str]:
    data = response.get("data")
    if not isinstance(data, list) or not data:
        raise SystemExit("API response did not include data[] images")

    output.parent.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        path = output_path_for_index(output, index, len(data))
        if item.get("b64_json"):
            path.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            download_url(str(item["url"]), path, timeout)
        else:
            continue
        saved.append(str(path.resolve()))

    if not saved:
        raise SystemExit("No b64_json or url image data found in API response")
    return saved


def download_url(url: str, output: Path, timeout: int) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SystemExit(f"Unsupported image URL scheme: {parsed.scheme}")
    request = urllib.request.Request(url, headers={"User-Agent": "image-api-tool/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            output.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to download image URL: {exc.reason}") from exc


def common_payload(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": args.model or config["model"],
        "prompt": args.prompt,
        "n": args.n,
    }
    for key in ("size", "quality", "background"):
        value = getattr(args, key, None)
        if value:
            payload[key] = value
    payload.update(parse_extra_json(args.extra_json))
    return payload


def generate(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(args.config)
    url = endpoint_url(config["baseUrl"], "/v1/images/generations")
    response = request_json(url, config["apiKey"], common_payload(args, config), config["timeout"])
    saved = save_images(response, Path(args.output), config["timeout"])
    return {"operation": "generate", "saved": saved, "created": response.get("created")}


def edit(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(args.config)
    image = Path(args.image)
    if not image.exists():
        raise SystemExit(f"Image file not found: {image}")

    files = {"image": image}
    if args.mask:
        mask = Path(args.mask)
        if not mask.exists():
            raise SystemExit(f"Mask file not found: {mask}")
        files["mask"] = mask

    url = endpoint_url(config["baseUrl"], "/v1/images/edits")
    response = request_multipart(url, config["apiKey"], common_payload(args, config), files, config["timeout"])
    saved = save_images(response, Path(args.output), config["timeout"])
    return {"operation": "edit", "saved": saved, "created": response.get("created")}


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="Path to JSON config with baseUrl, apiKey, model, timeout.")
    parser.add_argument("--prompt", required=True, help="Image prompt.")
    parser.add_argument("--output", required=True, help="Output image path.")
    parser.add_argument("--model", help=f"Model name. Defaults to IMAGE_API_MODEL or {DEFAULT_MODEL}.")
    parser.add_argument("--size", help="Image size, for example 1024x1024.")
    parser.add_argument("--quality", help="Provider-specific quality value.")
    parser.add_argument("--background", help="Provider-specific background value.")
    parser.add_argument("--n", type=int, default=1, help="Number of images to request.")
    parser.add_argument("--extra-json", help="Additional JSON object fields to include in the request.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Call v1/images/generations.")
    add_common_args(generate_parser)
    generate_parser.set_defaults(func=generate)

    edit_parser = subparsers.add_parser("edit", help="Call v1/images/edits.")
    add_common_args(edit_parser)
    edit_parser.add_argument("--image", required=True, help="Input image path.")
    edit_parser.add_argument("--mask", help="Optional mask image path.")
    edit_parser.set_defaults(func=edit)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
