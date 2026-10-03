#!/usr/bin/env python3
"""Instant Prometheus query for the lab scripts: prints one "<instance or alert> <value>" line per series."""

import json
import sys
import urllib.parse
import urllib.request

PROMETHEUS = "http://prometheus:9090"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: promq.py '<promql>'", file=sys.stderr)
        return 2
    url = f"{PROMETHEUS}/api/v1/query?" + urllib.parse.urlencode({"query": sys.argv[1]})
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.load(response)
    for series in data["data"]["result"]:
        labels = series["metric"]
        name = labels.get("instance") or labels.get("alertname") or "value"
        print(name, series["value"][1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
