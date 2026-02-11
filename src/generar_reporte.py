
import argparse
import os
from typing import Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def ensure_dir_for_file(filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def compute_global_metrics(df: pd.DataFrame) -> Tuple[int, float, float, float]:
    total = int(df["requests_total"].sum())
    success = int(df["success_2xx"].sum())
    client4xx = int(df["client_4xx"].sum())
    server5xx = int(df["server_5xx"].sum())
    errors = client4xx + server5xx

    pct_success = (success / total * 100.0) if total else 0.0
    pct_errors = (errors / total * 100.0) if total else 0.0

    # p90 global (aprox): percentil 90 sobre la columna p90 (sin raw no hay exacto global)
    p90_global = float(np.percentile(df["p90_elapsed_ms"].values, 90)) if len(df) else 0.0
    return total, pct_success, pct_errors, p90_global


def build_endpoint_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye tabla agregada por endpoint_base.
    - Suma conteos
    - Promedia tiempos ponderado por requests_total (más justo)
    """
    g = (
        df.groupby("endpoint_base", as_index=False)
        .apply(
            lambda x: pd.Series(
                {
                    "requests_total": x["requests_total"].sum(),
                    "success_2xx": x["success_2xx"].sum(),
                    "client_4xx": x["client_4xx"].sum(),
                    "server_5xx": x["server_5xx"].sum(),
                    "avg_elapsed_ms": (x["avg_elapsed_ms"] * x["requests_total"]).sum()
                    / max(x["requests_total"].sum(), 1),
                    "p90_elapsed_ms": (x["p90_elapsed_ms"] * x["requests_total"]).sum()
                    / max(x["requests_total"].sum(), 1),
                }
            )
        )
        .reset_index(drop=True)
    )

    g["%_success"] = (g["success_2xx"] / g["requests_total"] * 100.0).where(g["requests_total"] > 0, 0.0)
    g["%_client_4xx"] = (g["client_4xx"] / g["requests_total"] * 100.0).where(g["requests_total"] > 0, 0.0)
    g["%_server_5xx"] = (g["server_5xx"] / g["requests_total"] * 100.0).where(g["requests_total"] > 0, 0.0)

    g = g.sort_values("requests_total", ascending=False)

    for c in ["avg_elapsed_ms", "p90_elapsed_ms", "%_success", "%_client_4xx", "%_server_5xx"]:
        g[c] = g[c].round(2)

    return g


def plot_requests(df_endpoints: pd.DataFrame, out_png: str) -> None:
    plt.figure()
    plt.barh(df_endpoints["endpoint_base"], df_endpoints["requests_total"])
    plt.title("Requests total por endpoint")
    plt.xlabel("requests_total")
    plt.ylabel("endpoint_base")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


def plot_p90(df_endpoints: pd.DataFrame, out_png: str) -> None:
    plt.figure()
    plt.bar(df_endpoints["endpoint_base"], df_endpoints["p90_elapsed_ms"])
    plt.title("p90_elapsed_ms por endpoint")
    plt.xlabel("endpoint_base")
    plt.ylabel("p90_elapsed_ms")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


# def render_html(
#     df_endpoints: pd.DataFrame,
#     total: int,
#     pct_success: float,
#     pct_errors: float,
#     p90_global: float,
#     requests_png_name: str,
#     p90_png_name: str,
#     umbral_p90: float,
# ) -> str:
#     """
#     Marca en rojo los p90_elapsed_ms que superen el umbral.
#     """
#     def style_p90(val):
#         try:
#             v = float(val)
#             if v > umbral_p90:
#                 return "color: white; background-color: #c0392b;"
#         except Exception:
#             pass
#         return ""

#     styled = df_endpoints.style.applymap(style_p90, subset=["p90_elapsed_ms"])
#     table_html = styled.hide(axis="index").to_html()

#     return f"""<!doctype html>
# <html lang="es">
# <head>
#   <meta charset="utf-8" />
#   <title>Reporte KPI Diario</title>
#   <style>
#     body {{ font-family: Arial, sans-serif; margin: 24px; }}
#     .cards {{ display: flex; gap: 12px; flex-wrap: wrap; }}
#     .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; min-width: 220px; }}
#     h1 {{ margin-top: 0; }}
#     img {{ max-width: 100%; border: 1px solid #eee; border-radius: 8px; padding: 6px; }}
#     .note {{ color: #555; font-size: 0.95em; }}
#   </style>
# </head>
# <body>
#   <h1>Reporte KPI Diario (simulado)</h1>

#   <div class="cards">
#     <div class="card"><b>Total solicitudes</b><br>{total}</div>
#     <div class="card"><b>% Éxitos (2xx)</b><br>{pct_success:.2f}%</div>
#     <div class="card"><b>% Errores (4xx/5xx)</b><br>{pct_errors:.2f}%</div>
#     <div class="card"><b>p90 global (aprox)</b><br>{p90_global:.2f} ms</div>
#   </div>

#   <p class="note">
#     p90_elapsed_ms = tiempo por debajo del cual cae el 90% de las solicitudes (cola).
#     Umbral alerta p90: <b>{umbral_p90:.2f} ms</b>.
#   </p>

#   <h2>Tabla por endpoint</h2>
#   {table_html}

#   <h2>Gráficos</h2>

#   <h3>Requests total por endpoint</h3>
#   <img src="{requests_png_name}" alt="requests_total" />

#   <h3>p90_elapsed_ms por endpoint</h3>
#   <img src="{p90_png_name}" alt="p90_elapsed_ms" />
# </body>
# </html>
# """

def render_html(
    df_endpoints: pd.DataFrame,
    total: int,
    pct_success: float,
    pct_errors: float,
    p90_global: float,
    requests_png_name: str,
    p90_png_name: str,
    umbral_p90: float,
) -> str:
    """
    Genera HTML sin usar df.style (evita dependencia jinja2).
    Marca p90 > umbral con clase CSS 'alert'.
    """
    df_view = df_endpoints.copy()
    df_view["alerta_p90"] = df_view["p90_elapsed_ms"].apply(lambda v: "SI" if float(v) > umbral_p90 else "NO")

    # Convertimos a HTML simple
    table_html = df_view.to_html(index=False, escape=False)

    # Luego inyectamos un pequeño JS para pintar filas con alerta_p90=SI
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Reporte KPI Diario</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .cards {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; min-width: 220px; }}
    h1 {{ margin-top: 0; }}
    img {{ max-width: 100%; border: 1px solid #eee; border-radius: 8px; padding: 6px; }}
    .note {{ color: #555; font-size: 0.95em; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f4f4f4; }}
    tr.alert {{ background: #c0392b; color: white; }}
  </style>
</head>
<body>
  <h1>Reporte KPI Diario (simulado)</h1>

  <div class="cards">
    <div class="card"><b>Total solicitudes</b><br>{total}</div>
    <div class="card"><b>% Éxitos (2xx)</b><br>{pct_success:.2f}%</div>
    <div class="card"><b>% Errores (4xx/5xx)</b><br>{pct_errors:.2f}%</div>
    <div class="card"><b>p90 global (aprox)</b><br>{p90_global:.2f} ms</div>
  </div>

  <p class="note">
    p90_elapsed_ms = tiempo por debajo del cual cae el 90% de las solicitudes (cola).
    Umbral alerta p90: <b>{umbral_p90:.2f} ms</b>. (Filas con alerta en rojo)
  </p>

  <h2>Tabla por endpoint</h2>
  {table_html}

  <h2>Gráficos</h2>

  <h3>Requests total por endpoint</h3>
  <img src="{requests_png_name}" alt="requests_total" />

  <h3>p90_elapsed_ms por endpoint</h3>
  <img src="{p90_png_name}" alt="p90_elapsed_ms" />

  <script>
    // Pinta de rojo filas donde la columna 'alerta_p90' sea "SI"
    (function() {{
      const table = document.querySelector('table');
      if (!table) return;

      const headerCells = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
      const alertaIndex = headerCells.indexOf('alerta_p90');
      if (alertaIndex === -1) return;

      const rows = table.querySelectorAll('tbody tr');
      rows.forEach(tr => {{
        const tds = tr.querySelectorAll('td');
        const val = (tds[alertaIndex]?.textContent || '').trim();
        if (val === 'SI') {{
          tr.classList.add('alert');
        }}
      }});
    }})();
  </script>
</body>
</html>
"""

def main() -> None:
    parser = argparse.ArgumentParser(description="Genera reporte HTML de KPIs con gráficos")
    parser.add_argument("--input", required=True, help="Ej: out/kpi_por_endpoint_dia.csv")
    parser.add_argument("--output", required=True, help="Ej: out/report/kpi_diario.html")
    parser.add_argument("--umbral_p90", required=True, type=float)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"No existe el archivo de entrada: {args.input}")

    df = pd.read_csv(args.input)
    total, pct_success, pct_errors, p90_global = compute_global_metrics(df)
    df_endpoints = build_endpoint_table(df)

    out_dir = os.path.dirname(args.output)
    ensure_dir(out_dir)

    requests_png = os.path.join(out_dir, "requests_por_endpoint.png")
    p90_png = os.path.join(out_dir, "p90_por_endpoint.png")

    plot_requests(df_endpoints, requests_png)
    plot_p90(df_endpoints, p90_png)

    html = render_html(
        df_endpoints,
        total,
        pct_success,
        pct_errors,
        p90_global,
        os.path.basename(requests_png),
        os.path.basename(p90_png),
        args.umbral_p90,
    )

    ensure_dir_for_file(args.output)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK -> Reporte generado en {args.output}")


if __name__ == "__main__":
    main()