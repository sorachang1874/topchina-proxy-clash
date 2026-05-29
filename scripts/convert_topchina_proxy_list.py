#!/usr/bin/env python3
"""Convert TopChina/proxy-list README rows into a Clash config."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/TopChina/proxy-list/main/README.md"
DEFAULT_OUTPUT = "dist/clash.yaml"
DEFAULT_TEST_URL = "http://www.gstatic.com/generate_204"
DEFAULT_PASSWORD = "1"


@dataclass(frozen=True)
class ProxyRow:
    server: str
    port: int
    country: str
    username: str


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "topchina-proxy-clash/1.0",
            "Accept": "text/markdown,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_proxy_rows(markdown: str) -> list[ProxyRow]:
    rows: list[ProxyRow] = []
    seen: set[tuple[str, int]] = set()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or line.count("|") < 4:
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue

        endpoint, country, username = cells[:3]
        if endpoint.startswith("---") or ":" not in endpoint:
            continue

        server, port_text = endpoint.rsplit(":", 1)
        server = server.strip()
        port_text = port_text.strip()
        if not server or not port_text.isdigit():
            continue

        port = int(port_text)
        if port < 1 or port > 65535 or not username:
            continue

        key = (server, port)
        if key in seen:
            continue

        seen.add(key)
        rows.append(
            ProxyRow(
                server=server,
                port=port,
                country=country or "Unknown",
                username=username,
            )
        )

    return rows


def extract_source_update(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if re.search(r"\d{4}.\d{2}.\d{2}.\s+\d{2}:\d{2}", line):
            return line.strip().strip("#-* ")
    return None


def build_clash_config(
    rows: list[ProxyRow],
    *,
    password: str,
    test_url: str,
    source_url: str,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("No proxy rows found in source markdown")

    proxies: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        proxies.append(
            {
                "name": f"TC-{index:03d} {row.country} {row.server}:{row.port}",
                "type": "http",
                "server": row.server,
                "port": row.port,
                "username": row.username,
                "password": password,
            }
        )

    proxy_names = [proxy["name"] for proxy in proxies]
    return {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "TopChina Select",
                "type": "select",
                "proxies": ["TopChina Auto", "DIRECT", *proxy_names],
            },
            {
                "name": "TopChina Auto",
                "type": "url-test",
                "url": test_url,
                "interval": 300,
                "tolerance": 50,
                "proxies": proxy_names,
            },
        ],
        "rules": ["MATCH,TopChina Select"],
        "x-generated-from": source_url,
    }


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def render_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def render_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", key):
        return key
    return render_scalar(key)


def render_yaml(value: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    lines: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            rendered_key = render_key(str(key))
            if is_scalar(child):
                lines.append(f"{pad}{rendered_key}: {render_scalar(child)}")
            else:
                lines.append(f"{pad}{rendered_key}:")
                lines.extend(render_yaml(child, indent + 2))
        return lines

    if isinstance(value, list):
        for child in value:
            if is_scalar(child):
                lines.append(f"{pad}- {render_scalar(child)}")
            else:
                lines.append(f"{pad}-")
                lines.extend(render_yaml(child, indent + 2))
        return lines

    raise TypeError(f"Unsupported YAML value: {type(value)!r}")


def render_clash_yaml(config: dict[str, Any], *, source_updated: str | None) -> str:
    generated_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    header = [
        "# Generated by topchina-proxy-clash.",
        f"# Generated at: {generated_at}",
    ]
    if source_updated:
        header.append(f"# Source updated: {source_updated}")
    return "\n".join(header + ["", *render_yaml(config), ""])


def read_source(args: argparse.Namespace) -> str:
    if args.input:
        return Path(args.input).read_text(encoding="utf-8")
    return fetch_text(args.source_url)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default=os.getenv("SOURCE_URL", DEFAULT_SOURCE_URL))
    parser.add_argument("--input", help="Read source markdown from a local file instead of URL")
    parser.add_argument("--output", default=os.getenv("OUTPUT", DEFAULT_OUTPUT))
    parser.add_argument("--password", default=os.getenv("PROXY_PASSWORD", DEFAULT_PASSWORD))
    parser.add_argument("--test-url", default=os.getenv("CLASH_TEST_URL", DEFAULT_TEST_URL))
    parser.add_argument("--max-proxies", type=positive_int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    markdown = read_source(args)
    rows = parse_proxy_rows(markdown)
    if args.max_proxies:
        rows = rows[: args.max_proxies]

    config = build_clash_config(
        rows,
        password=args.password,
        test_url=args.test_url,
        source_url=args.source_url,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_clash_yaml(config, source_updated=extract_source_update(markdown)),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} proxies to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
