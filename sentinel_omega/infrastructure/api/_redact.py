"""Redacción de credenciales en texto de log.

La lección del 2026-09-27 (bitácora): el token viejo de Telegram llegó al
log ROTADO 195 veces porque la excepción de `requests` TRAE la URL, y
`logger.error(f"...: {e}")` la escribió entera. El 2026-10-25 el mismo
patrón se midió con `appid=<OPENWEATHERMAP_KEY>` y `api_key=<NASA_API_KEY>`
en `data/sentinel_omega.log`.

Rotar la llave no arregla esto: el siguiente fallo de red vuelve a filtrar
la nueva. Se enmascara por PATRÓN (query-params de credencial + forma de
token de bot), no comparando contra variables de entorno, para que cubra
también una llave de otra fuente que aparezca en el mismo mensaje.

Enmascarar de más es inofensivo; de menos, es una fuga.
"""
from __future__ import annotations

import re

# Query-params que viajan credenciales. Claves ordenadas por longitud
# descendente para que `client_secret` no quede a medias por `key`.
_PARAMS = [
    "client_secret", "apisecret", "api_secret", "access_token",
    "refresh_token", "signature", "api_key", "appid", "token",
    "secret", "password",
]
_PARAM_RE = re.compile(
    r"(?i)(" + "|".join(sorted(set(_PARAMS), key=len, reverse=True)) +
    r")=[^&\s'\"]+"
)

# Tokens de bot de Telegram: `<8-10 dígitos>:<30+ chars>` (el patrón medido
# de sin_token, con sus dos lecciones: sin `\b` delante y `{30,}` no `{35}`).
_BOT_TOKEN_RE = re.compile(r"(?<![0-9])[0-9]{8,10}:[A-Za-z0-9_-]{30,}")

# El tramo `/bot<token>/` de la URL de la API de Telegram, aunque el token
# no tenga la forma canónica (truncado, de pruebas).
_BOT_PATH_RE = re.compile(r"/bot[^/\s]*:[^/\s]*/")

# Credenciales en HEADERS (P2 2026-11-10): los logs de `requests`/`httpx`
# vuelcan las cabeceras en el mensaje de error igual que la URL, y los
# patrones de arriba solo cubren query-params y tokens de bot. `Authorization`
# cubre Bearer/Basic de cualquier API; `x-cg-demo-api-key` es la llave Demo
# de CoinGecko (`crypto.py:36-39`, antes solo cubierta por
# `mask_coingecko_key`, que exige conocer la llave). El valor se enmascara
# entero: el esquema (Bearer/Basic) se conserva para diagnosticar. La segunda
# rama acepta también la forma dict de repr (`'x-cg-demo-api-key': '…'`).
_HEADER_RE = re.compile(
    r"(?i)(Authorization:\s*(?:Bearer|Basic)\s+)[^\s'\"]+"
    r"|(x-cg-demo-api-key['\"]?\s*:\s*['\"]?)[^\s'\",}\]]+"
)


def sin_credenciales(texto: object) -> str:
    """El texto con toda credencial enmascarada.

    Cubre: query-params de credencial (`appid=`, `api_key=`, `secret=`,
    `token=`, …), tokens de bot por forma, y el tramo `/bot<token>/`.
    Además cubre credenciales en headers (`Authorization: Bearer/Basic …`
    y `x-cg-demo-api-key: …`, P2 2026-11-10).
    """
    s = str(texto)
    s = _BOT_TOKEN_RE.sub("<TOKEN>", s)
    s = _BOT_PATH_RE.sub("/bot<TOKEN>/", s)
    s = _PARAM_RE.sub(r"\1=<REDACTADO>", s)
    s = _HEADER_RE.sub(lambda m: (m.group(1) or m.group(2)) + "<REDACTADO>", s)
    return s
