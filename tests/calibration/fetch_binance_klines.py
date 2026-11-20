"""Descarga UNA vez velas históricas públicas de BTCUSDT de Binance y las congela en
fixtures/binance_btcusdt_klines.json (validación secundaria de IMPL-2, DEC-016 Q37).

Endpoint público de datos de mercado (`/api/v3/klines`), sin credenciales ni operaciones.
Solo velas cerradas antes de DATA_TS (closeTime < DATA_TS), como exige REQ-G-070. Si el
archivo ya existe no se sobrescribe (la batería debe usar siempre la misma instantánea).

Uso: .venv/bin/python -m tests.calibration.fetch_binance_klines
"""
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .scenarios import DATA_TS, FIXTURES, _epoch

HOSTS = ("https://data-api.binance.vision", "https://api.binance.com")
FRAMES = {"D1": ("1d", 60), "H4": ("4h", 30), "H1": ("1h", 24)}
OUT = FIXTURES / "binance_btcusdt_klines.json"


def _iso_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(host: str, interval: str, limit: int, end_ms: int) -> tuple[str, list]:
    q = urllib.parse.urlencode({"symbol": "BTCUSDT", "interval": interval, "endTime": end_ms - 1, "limit": limit + 1})
    url = f"{host}/api/v3/klines?{q}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "kline-fixture"}), timeout=20) as r:
        return url, json.loads(r.read())


def main() -> int:
    if OUT.exists():
        print(f"ya existe {OUT}; no se sobrescribe", file=sys.stderr)
        return 1
    end_ms = _epoch(DATA_TS) * 1000
    last_err = None
    for host in HOSTS:
        try:
            ohlcv, urls = {}, {}
            for tf, (interval, limit) in FRAMES.items():
                url, rows = fetch(host, interval, limit, end_ms)
                closed = [k for k in rows if k[6] < end_ms][-limit:]
                if len(closed) != limit:
                    raise RuntimeError(f"{tf}: {len(closed)} velas cerradas, se esperaban {limit}")
                ohlcv[tf] = [{"timestamp": _iso_ms(k[0]), "open": float(k[1]), "high": float(k[2]),
                              "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in closed]
                urls[tf] = url
            break
        except Exception as e:  # noqa: BLE001 — se prueba el siguiente host público
            last_err = e
    else:
        raise SystemExit(f"no se pudieron descargar las velas: {last_err}")
    snap = {"source": "Binance Spot, endpoint público /api/v3/klines (sin credenciales)",
            "symbol": "BTCUSDT", "closed_before_utc": DATA_TS, "urls": urls,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(), "ohlcv": ohlcv}
    FIXTURES.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=1) + "\n", encoding="utf-8")
    print(OUT, hashlib.sha256(OUT.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
