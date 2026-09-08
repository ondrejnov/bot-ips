"""Download official crawler ranges and publish an atomic aggregate snapshot."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import ipaddress
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
MAX_BYTES = 10 * 1024 * 1024


def parse_prefixes(data):
    if not isinstance(data, dict) or not isinstance(data.get("prefixes"), list):
        raise ValueError("expected an object containing a prefixes list")
    networks = set()
    for entry in data["prefixes"]:
        if not isinstance(entry, dict):
            raise ValueError("prefix entry must be an object")
        keys = entry.keys() & {"ipv4Prefix", "ipv6Prefix"}
        if not keys:
            raise ValueError("prefix entry has no supported IP field")
        for key in keys:
            value = entry[key]
            if not isinstance(value, str) or "/" not in value:
                raise ValueError("prefix must be a CIDR string")
            network = ipaddress.ip_network(value, strict=True)
            if network.version != (4 if key == "ipv4Prefix" else 6):
                raise ValueError("IP family does not match prefix field")
            networks.add(network)
    if not networks:
        raise ValueError("refusing an empty prefix list")
    return sorted(networks, key=lambda n: (n.version, int(n.network_address), n.prefixlen))


def fetch(url, timeout):
    request = Request(url, headers={"User-Agent": "bot-ips/0.1", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                if urlsplit(response.url).scheme != "https":
                    raise ValueError("refusing a non-HTTPS response")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("response exceeds 10 MiB")
            return json.loads(raw)
        except (URLError, TimeoutError, ConnectionError) as exc:
            if isinstance(exc, HTTPError) and exc.code != 429 and exc.code < 500:
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def aggregate(sources, timeout):
    def download(item):
        name, url = item
        try:
            data = fetch(url, timeout)
            networks = parse_prefixes(data)
            return name, {
                "url": url,
                "creation_time": data.get("creationTime"),
                "prefixes": [str(n) for n in networks],
            }, networks
        except (OSError, ValueError) as exc:
            raise ValueError(f"{name} ({url}): {exc}") from exc

    bots = {}
    networks = set()
    with ThreadPoolExecutor(max_workers=6) as executor:
        for name, bot, ranges in executor.map(download, sorted(sources.items())):
            bots[name] = bot
            networks.update(ranges)
    return {
        "schema_version": 1,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "bots": bots,
        "ipv4": [str(n) for n in ipaddress.collapse_addresses(n for n in networks if n.version == 4)],
        "ipv6": [str(n) for n in ipaddress.collapse_addresses(n for n in networks if n.version == 6)],
    }


def write_snapshot(path, snapshot):
    path.parent.mkdir(parents=True, exist_ok=True)
    outputs = {
        path: json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n",
        path.with_suffix(".txt"): "\n".join(snapshot["ipv4"] + snapshot["ipv6"]) + "\n",
    }
    staged = []
    try:
        for destination, content in outputs.items():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=f".{destination.name}.", delete=False) as stream:
                temporary = Path(stream.name)
                staged.append((temporary, destination))
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, destination in staged:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "sources.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "bot-ips.json")
    parser.add_argument("--timeout", type=float, default=30, help="socket timeout in seconds (default: 30)")
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a positive finite number")
    if args.output.suffix != ".json":
        parser.error("--output must have a .json suffix; a sibling .txt file is also generated")
    if args.sources.resolve() in {args.output.resolve(), args.output.with_suffix(".txt").resolve()}:
        parser.error("output files must differ from --sources")
    try:
        sources = json.loads(args.sources.read_text(encoding="utf-8"))
        if not isinstance(sources, dict) or not sources:
            raise ValueError("sources must be a nonempty object mapping bot names to HTTPS URLs")
        for name, url in sources.items():
            if not name or not isinstance(url, str):
                raise ValueError("invalid source name or URL")
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f"{name}: expected an HTTPS URL without credentials")
        snapshot = aggregate(sources, args.timeout)
        write_snapshot(args.output, snapshot)
    except (OSError, ValueError) as exc:
        print(f"Update failed: {exc}", file=sys.stderr)
        return 1
    print(f"Published {len(snapshot['bots'])} bots, {len(snapshot['ipv4'])} IPv4 and "
          f"{len(snapshot['ipv6'])} IPv6 aggregated ranges to {args.output} and {args.output.with_suffix('.txt')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
