import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from lxml import etree


BASE_URL = "https://httpbin.org"


@dataclass
class Config:
    user: str = "usuario_test"
    passwd: str = "clave123"
    out_dir: str = "out"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_text(path: str, content: str) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def save_json(path: str, data: Any) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    max_retries: int = 2,
    backoff_s: float = 0.5,
    **kwargs,
) -> requests.Response:
    """
    Reintenta en errores de red y maneja 403 con logging + reintento limitado.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_retries + 2):
        try:
            resp = session.request(method, url, timeout=20, **kwargs)

            if resp.status_code == 403:
                print(f"[WARN] 403 Forbidden en {url} (intento {attempt}/{max_retries+1})")
                if attempt <= max_retries:
                    time.sleep(backoff_s * attempt)
                    continue

            return resp

        except requests.RequestException as e:
            last_exc = e
            print(f"[ERROR] Error de red en {url}: {e} (intento {attempt}/{max_retries+1})")
            if attempt <= max_retries:
                time.sleep(backoff_s * attempt)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("Fallo inesperado en request_with_retry")


def tarea_auth_basic(session: requests.Session, cfg: Config) -> None:
    url = f"{BASE_URL}/basic-auth/{cfg.user}/{cfg.passwd}"
    resp = request_with_retry(session, "GET", url, auth=HTTPBasicAuth(cfg.user, cfg.passwd))
    print("[AUTH BASIC] status:", resp.status_code)
    resp.raise_for_status()

    data = resp.json()
    if not data.get("authenticated"):
        raise RuntimeError("Autenticación no exitosa: authenticated != true")
    print("[AUTH BASIC] OK:", data)


def tarea_cookies(session: requests.Session) -> None:
    resp_set = request_with_retry(session, "GET", f"{BASE_URL}/cookies/set", params={"session": "activa"})
    print("[COOKIES] set status:", resp_set.status_code)
    resp_set.raise_for_status()

    resp_get = request_with_retry(session, "GET", f"{BASE_URL}/cookies")
    print("[COOKIES] get status:", resp_get.status_code)
    resp_get.raise_for_status()

    cookies = resp_get.json().get("cookies", {})
    if cookies.get("session") != "activa":
        raise RuntimeError(f"Cookie session no establecida correctamente. cookies={cookies}")
    print("[COOKIES] OK:", cookies)


def tarea_status_403(session: requests.Session) -> None:
    resp = request_with_retry(session, "GET", f"{BASE_URL}/status/403", max_retries=2)
    print("[403] status final:", resp.status_code)

    if resp.status_code == 403:
        print("[403] Acceso denegado detectado. Registrando evento y continuando...")
        return

    resp.raise_for_status()


def tarea_extraer_json(session: requests.Session, cfg: Config) -> None:
    resp = request_with_retry(session, "GET", f"{BASE_URL}/get")
    resp.raise_for_status()
    data = resp.json()

    save_json(os.path.join(cfg.out_dir, "datos.json"), data)
    print("[JSON] Guardado en out/datos.json")


def tarea_extraer_xml(session: requests.Session, cfg: Config) -> None:
    resp = request_with_retry(session, "GET", f"{BASE_URL}/xml")
    resp.raise_for_status()

    # Parse XML para mostrar que lo procesamos
    root = etree.fromstring(resp.content)
    slides = root.findall(".//slide")
    resumen = [{"type": s.get("type"), "title": s.findtext("title")} for s in slides]

    # Guardamos el XML original (cumple "datos.xml") y mostramos parse en consola
    save_text(os.path.join(cfg.out_dir, "datos.xml"), resp.text)
    print("[XML] Guardado en out/datos.xml")
    print("[XML] Resumen slides:", resumen)


# def tarea_extraer_html_title(session: requests.Session, cfg: Config) -> None:
#     resp = request_with_retry(session, "GET", f"{BASE_URL}/html")
#     resp.raise_for_status()

#     soup = BeautifulSoup(resp.text, "html.parser")
#     title = soup.title.text.strip() if soup.title else ""

#     save_text(os.path.join(cfg.out_dir, "titulo.html"), title)
#     print("[HTML] Título extraído:", title)
#     print("[HTML] Guardado en out/titulo.html")
def tarea_extraer_html_title(session: requests.Session, cfg: Config) -> None:
    resp = request_with_retry(session, "GET", f"{BASE_URL}/html")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # httpbin /html no siempre incluye <title>, así que usamos fallback a <h1>
    title = ""
    if soup.title and soup.title.text:
        title = soup.title.text.strip()
    else:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

    if not title:
        title = "SIN_TITULO"

    save_text(os.path.join(cfg.out_dir, "titulo.html"), title)
    print("[HTML] Título extraído:", title)
    print("[HTML] Guardado en out/titulo.html")


def tarea_post_form(session: requests.Session) -> None:
    payload = {
        "nombre": "Juan",
        "apellido": "Pérez",
        "correo": "juan.perez@example.com",
        "mensaje": "Este es un mensaje de prueba.",
    }
    resp = request_with_retry(session, "POST", f"{BASE_URL}/post", data=payload)
    resp.raise_for_status()
    data = resp.json()

    print("[POST] Enviado:", payload)
    print("[POST] Respuesta form:", data.get("form"))


def tarea_redirect(session: requests.Session) -> None:
    resp = request_with_retry(
        session, "GET", f"{BASE_URL}/redirect-to",
        params={"url": "/get"},
        allow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    print("[REDIRECT] url final:", resp.url)
    print("[REDIRECT] args:", data.get("args"))


def main() -> None:
    cfg = Config()
    ensure_dir(cfg.out_dir)

    with requests.Session() as session:
        tarea_auth_basic(session, cfg)
        tarea_cookies(session)
        tarea_status_403(session)
        tarea_extraer_json(session, cfg)
        tarea_extraer_xml(session, cfg)
        tarea_extraer_html_title(session, cfg)
        tarea_post_form(session)
        tarea_redirect(session)


if __name__ == "__main__":
    main()