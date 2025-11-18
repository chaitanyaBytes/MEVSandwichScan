from __future__ import annotations

from typing import Dict, Iterable, List

import requests

API_URL = "https://lite-api.jup.ag/price/v3"
BATCH_SIZE = 50


def _chunk(items: Iterable[str], size: int) -> Iterable[List[str]]:
    batch: List[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def fetch_prices_usd(mints: List[str]) -> Dict[str, float]:
    """Return {mint: price_usd} using Jupiter lite API."""
    if not mints:
        return {}

    prices: Dict[str, float] = {}
    unique_mints = list(dict.fromkeys(mints))
    for batch in _chunk(unique_mints, BATCH_SIZE):
        try:
            resp = requests.get(API_URL, params={"ids": ",".join(batch)}, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[WARN] Price fetch failed for {batch}: {exc}")
            continue

        data = resp.json()
        for mint, obj in data.items():
            price = obj.get("priceUsd") or obj.get("usdPrice") or obj.get("price")
            print(f"Price for {mint}: {price}")
            if price is None:
                continue
            try:
                prices[mint] = float(price)
            except (TypeError, ValueError):
                continue

    return prices
