# prueba-tecnica-http-client-etl

Prueba técnica – HTTP Client + ETL en Python.

---

## Descripción general

Este repositorio es sobre la resolución de la prueba técnica orientada al consumo de APIs HTTP, simulación de bitácoras, procesamiento de datos, cálculo de KPIs operativos y generación de reportes, utilizando **Python 3**.

La solución cubre:

- Interacción automatizada con endpoints de **httpbin.org**
- Generación y procesamiento de datos simulados
- Cálculo de métricas diarias por endpoint
- Visualización de KPIs mediante un **reporte HTML**

---

## Estructura del proyecto

```text
prueba-tecnica-http-client-etl/
│
├── src/
│   ├── http_client.py          # Cliente HTTP automatizado (httpbin)
│   ├── generar_datos.py        # Generación de datos ficticios (JSONL)
│   ├── calcular_kpi.py         # Cálculo de KPIs diarios por endpoint
│   └── generar_reporte.py      # Generación de reporte HTML con gráficos
│
├── out/
│   ├── datos.json              # Respuesta JSON extraída de /get
│   ├── datos.xml               # Respuesta XML extraída de /xml
│   ├── titulo.html             # Título extraído del HTML
│   ├── datos.jsonl             # Bitácora simulada de llamadas HTTP
│   ├── kpi_por_endpoint_dia.csv# KPIs diarios por endpoint
│   └── report/
│       ├── kpi_diario.html     # Reporte HTML final
│       ├── requests_por_endpoint.png
│       └── p90_por_endpoint.png
│
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Requisitos técnicos

- **Python**: 3.10+
- **Sistema operativo**: Linux (Yo lo hice en linux)

### Librerías principales
- requests
- beautifulsoup4
- lxml
- numpy
- pandas
- matplotlib

### Instalación de dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución de la solución

### 1️⃣ Cliente HTTP automatizado

Interactúa con los endpoints de **httpbin.org**, cubriendo:

- Autenticación básica
- Manejo de cookies y sesiones
- Manejo de errores 403
- Extracción de datos JSON, XML y HTML
- Envío de formularios
- Redirecciones

```bash
python src/http_client.py
```

Genera:
- `out/datos.json`
- `out/datos.xml`
- `out/titulo.html`

---

### 2️⃣ Generación de datos ficticios (JSONL)

Simula una bitácora de llamadas HTTP.

```bash
python src/generar_datos.py \
  --n_registros 500 \
  --salida out/datos.jsonl \
  --seed 42
```

### 3️⃣ Cálculo de KPIs diarios

Calcula métricas por `(date_utc, endpoint_base)`:

- requests_total
- success_2xx
- client_4xx
- server_5xx
- parse_errors
- avg_elapsed_ms
- p90_elapsed_ms

```bash
python src/calcular_kpi.py \
  --input out/datos.jsonl \
  --output out/kpi_por_endpoint_dia.csv
```

### 4️⃣ Generación de reporte HTML

Crea un reporte visual con:

- Métricas globales
- Tabla agregada por endpoint
- Gráficos
- Alertas configurables por p90

```bash
python src/generar_reporte.py \
  --input out/kpi_por_endpoint_dia.csv \
  --output out/report/kpi_diario.html \
  --umbral_p90 300
```

Abrir en navegador:

```bash
xdg-open out/report/kpi_diario.html
```

## Interpretación del reporte

- El **p90_elapsed_ms** representa la latencia máxima del 90% de las solicitudes.
- Los endpoints que superan el umbral configurado (`--umbral_p90`) se muestran en rojo.
- Permite identificar problemas de latencia y comportamiento anómalo por endpoint.

---

## Normalización de endpoints

Para el cálculo de KPIs se normalizan rutas dinámicas:

- `/status/403` → `/status`
- `/basic-auth/usuario/clave` → `/basic-auth`
- Se eliminan parámetros de *query string*

Esto permite un análisis agregado consistente.


## ⚠️ Sobre Pentaho Data Integration (PDI) ⚠️ (IMportante aca de lo que no puede lograr)

La prueba incluye una sección de carga ETL utilizando **Pentaho Data Integration (PDI)**.

### Nota

- La lógica completa del pipeline fue implementada en **Python**.
- La sección de Pentaho (archivos `.ktr` y `.kjb`) **no fue ejecutada** debido a restricciones de entorno (heeramientas que me faltaban y de conocimiento profundo de la herramienta).
- El diseño del flujo es **directamente trasladable a PDI** sin cambios de lógica.

### Diseño del flujo ETL propuesto

```text
CSV Input → Filter Rows → Staging → Fact
