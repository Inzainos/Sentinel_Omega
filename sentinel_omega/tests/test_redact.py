"""Tests del sanitizador de credenciales en logs (_redact.sin_credenciales).

La fuga real medida el 2026-10-25: `logger.error(f"OWM fetch failed...: {e}")`
escribía la URL de la excepción con `appid=<OPENWEATHERMAP_KEY>` entera. La
lección del 2026-09-27 (Telegram): rotar no arregla la clase — se enmascara
por patrón. Enmascarar de más es inofensivo; de menos, es una fuga.
"""
from sentinel_omega.infrastructure.api._redact import sin_credenciales


class TestSinCredenciales:

    def test_appid_de_owm(self):
        """La fuga medida: la URL de la excepción de requests trae el appid."""
        msg = (
            "OWM fetch failed for tlaxcala: HTTPSConnectionPool("
            "host='api.openweathermap.org', port=443): Max retries exceeded "
            "with url: /data/2.5/weather?lat=19.3&lon=-98.2"
            "&appid=fa1e2d3c4b5a6f7e8d9c0b1a2d3e4f5a&units=metric"
        )
        out = sin_credenciales(msg)
        assert "fa1e2d3c4b5a6f7e8d9c0b1a2d3e4f5a" not in out
        assert "appid=<REDACTADO>" in out
        # lo que NO es credencial se conserva (para seguir debugueando)
        assert "api.openweathermap.org" in out
        assert "lat=19.3" in out

    def test_api_key_de_nasa(self):
        msg = "NASA NEO fetch failed: 403 with url /neo/rest/v1?api_key=AbCdEf123456"
        out = sin_credenciales(msg)
        assert "AbCdEf123456" not in out
        assert "api_key=<REDACTADO>" in out

    def test_token_de_bot_forma_canonica(self):
        """El caso de 2026-09-27: <8-10 dígitos>:<35 chars> en la URL."""
        msg = "send failed: url /bot8460857489:AAH" + "x" * 35 + "/sendMessage"
        out = sin_credenciales(msg)
        assert "8460857489:AAH" not in out
        assert "<TOKEN>" in out
        assert "/bot<TOKEN>/" in out

    def test_token_largo_no_se_escapa(self):
        """{30,} no {35}: un token de 36+ chars también se enmascara."""
        msg = "x 1234567890:" + "a" * 40 + " y"
        assert "a" * 40 not in sin_credenciales(msg)

    def test_path_bot_no_canonico(self):
        """`/bot<algo>:<algo>/` se redacta aunque el token sea truncado."""
        msg = "GET /bot123:short/ failed"
        out = sin_credenciales(msg)
        assert "/bot<TOKEN>/" in out
        assert "short" not in out.split("<TOKEN>")[0]

    def test_param_mayuscula_y_variantes(self):
        """API_KEY=, client_secret=, Token=: case-insensitive, largos."""
        out = sin_credenciales("u?API_KEY=zzz&client_secret=www&Token=t")
        assert "zzz" not in out and "www" not in out
        assert "API_KEY=<REDACTADO>" in out

    def test_mensaje_sin_credenciales_intacto(self):
        """No reescribir mensajes limpios: el diagnóstico no se pierde."""
        msg = "IERS LOD fetch failed: 400 Client Error: Bad Request"
        assert sin_credenciales(msg) == msg

    def test_sin_token_de_telegram_delega(self):
        """telegram.sin_token conserva su contrato y hereda los params."""
        from sentinel_omega.infrastructure.api.telegram import sin_token
        assert sin_token("appid=abc123") == "appid=<REDACTADO>"
        # contrato histórico: el token queda enmascarado (el prefijo `bot`
        # de una URL parcial se conserva — siempre fue así)
        out = sin_token("bot8460857489:" + "A" * 35)
        assert "8460857489:" not in out and "<TOKEN>" in out
