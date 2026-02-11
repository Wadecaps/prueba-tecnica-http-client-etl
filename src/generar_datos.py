import argparse
import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List


ENDPOINTS = ["/get", "/post", "/status/403", "/basic-auth", "/cookies", "/xml", "/html"]


def ensure_dir_for_file(filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)


def random_timestamp_last_days(rng: random.Random, days: int = 3) -> str:
    """
    Genera un timestamp UTC aleatorio dentro de los últimos `days` días.
    Formato: YYYY-MM-DDTHH:MM:SSZ
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    total_seconds = int((now - start).total_seconds())
    offset = rng.randint(0, total_seconds)
    ts = start + timedelta(seconds=offset)
    return ts.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def status_code_for_endpoint(rng: random.Random, endpoint: str) -> int:
    """
    /status/403 siempre 403.
    """
    if endpoint == "/status/403":
        return 403

    p = rng.random()
    if p < 0.88:
        return 200
    elif p < 0.96:
        return rng.choice([400, 401, 404, 429])
    else:
        return rng.choice([500, 502, 503])


def parse_result_value(rng: random.Random) -> str:
    """5% de los casos debe ser 'error'."""
    return "error" if rng.random() < 0.05 else "ok"


def generate_record(rng: random.Random) -> Dict:
    endpoint = rng.choice(ENDPOINTS)
    return {
        "timestamp_utc": random_timestamp_last_days(rng, days=3),
        "endpoint": endpoint,
        "status_code": status_code_for_endpoint(rng, endpoint),
        "elapsed_ms": round(rng.uniform(50, 800), 2),
        "parse_result": parse_result_value(rng),
    }


def write_jsonl(records: List[Dict], output_path: str) -> None:
    ensure_dir_for_file(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera bitácora ficticia de llamadas HTTP en formato JSONL")
    parser.add_argument("--n_registros", type=int, required=True)
    parser.add_argument("--salida", type=str, required=True)
    parser.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    records = [generate_record(rng) for _ in range(args.n_registros)]
    write_jsonl(records, args.salida)

    print(f"OK -> Generados {args.n_registros} registros en {args.salida} (seed={args.seed})")


if __name__ == "__main__":
    main()