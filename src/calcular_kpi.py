import argparse
import csv
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np


@dataclass
class Agg:
    elapsed: List[float]
    requests_total: int = 0
    success_2xx: int = 0
    client_4xx: int = 0
    server_5xx: int = 0
    parse_errors: int = 0

    def add(self, status_code: int, elapsed_ms: float, parse_result: str) -> None:
        self.requests_total += 1
        self.elapsed.append(elapsed_ms)

        if 200 <= status_code <= 299:
            self.success_2xx += 1
        elif 400 <= status_code <= 499:
            self.client_4xx += 1
        elif 500 <= status_code <= 599:
            self.server_5xx += 1

        if parse_result != "ok":
            self.parse_errors += 1

    def avg_elapsed_ms(self) -> float:
        return float(np.mean(self.elapsed)) if self.elapsed else 0.0

    def p90_elapsed_ms(self) -> float:
        """
        Percentil 90: numpy.percentile(valores, 90)
        Interpreta el valor por debajo del cual cae el 90% de los tiempos.
        """
        return float(np.percentile(self.elapsed, 90)) if self.elapsed else 0.0


def ensure_dir_for_file(filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)


def parse_date_utc(timestamp_utc: str) -> str:
    dt = datetime.strptime(timestamp_utc, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%d")


def normalize_endpoint(endpoint: str) -> str:
    """
    Normaliza el endpoint para agrupar por 'endpoint_base':
      1) Quita query params: /redirect-to?url=/get -> /redirect-to
      2) Colapsa rutas variables conocidas:
         - /status/403 -> /status
         - /basic-auth/usuario/pass -> /basic-auth
    """
    base = endpoint.split("?", 1)[0]

    if base.startswith("/status/"):
        return "/status"
    if base.startswith("/basic-auth/"):
        return "/basic-auth"

    return base


def read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON mal formado en línea {line_num}: {e}") from e


def compute_kpis(rows: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str], Agg]:
    groups: Dict[Tuple[str, str], Agg] = defaultdict(lambda: Agg(elapsed=[]))

    for r in rows:
        ts = r.get("timestamp_utc")
        endpoint = r.get("endpoint")
        status_code = r.get("status_code")
        elapsed_ms = r.get("elapsed_ms")
        parse_result = r.get("parse_result")

        if ts is None or endpoint is None:
            continue

        date_utc = parse_date_utc(str(ts))
        endpoint_base = normalize_endpoint(str(endpoint))

        try:
            sc = int(status_code)
        except Exception:
            sc = 0
            parse_result = "error"

        try:
            ems = float(elapsed_ms)
        except Exception:
            ems = 0.0
            parse_result = "error"

        pr = str(parse_result) if parse_result is not None else "error"

        groups[(date_utc, endpoint_base)].add(sc, ems, pr)

    return groups


def write_csv(groups: Dict[Tuple[str, str], Agg], output_path: str) -> None:
    ensure_dir_for_file(output_path)

    fieldnames = [
        "date_utc",
        "endpoint_base",
        "requests_total",
        "success_2xx",
        "client_4xx",
        "server_5xx",
        "parse_errors",
        "avg_elapsed_ms",
        "p90_elapsed_ms",
    ]

    items = sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1]))

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for (date_utc, endpoint_base), agg in items:
            w.writerow({
                "date_utc": date_utc,
                "endpoint_base": endpoint_base,
                "requests_total": agg.requests_total,
                "success_2xx": agg.success_2xx,
                "client_4xx": agg.client_4xx,
                "server_5xx": agg.server_5xx,
                "parse_errors": agg.parse_errors,
                "avg_elapsed_ms": round(agg.avg_elapsed_ms(), 2),
                "p90_elapsed_ms": round(agg.p90_elapsed_ms(), 2),
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Calcula KPIs diarios por endpoint_base desde un JSONL")
    parser.add_argument("--input", required=True, help="Ej: out/datos.jsonl")
    parser.add_argument("--output", required=True, help="Ej: out/kpi_por_endpoint_dia.csv")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"No existe el archivo de entrada: {args.input}")

    groups = compute_kpis(read_jsonl(args.input))
    write_csv(groups, args.output)

    print(f"OK -> KPIs generados en {args.output} (grupos={len(groups)})")


if __name__ == "__main__":
    main()