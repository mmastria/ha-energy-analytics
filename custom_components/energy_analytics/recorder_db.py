"""Acesso ao banco pela SESSAO DO RECORDER. SOMENTE SELECT.

Substitui a conexao psycopg do app Flask original: o recorder ja mantem um pool para o mesmo
banco, entao nao ha segunda credencial nem segundo DSN para manter.

`read_only=True` NAO e' barreira de escrita — o proprio HA documenta que ele so' sinaliza que a
sessao dispensa commit. A garantia de leitura pura e' textual: esta integracao so' emite SELECT.

Todo SELECT roda no executor DO RECORDER (`get_instance(hass).async_add_executor_job`) — nunca no
event loop. O trabalho de CPU (a regressao) NAO entra aqui: ele vai para o executor geral, senao
segura o recorder e o HA comeca a acumular eventos.
"""
from __future__ import annotations

from typing import Any, Iterable

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.util import session_scope
from homeassistant.core import HomeAssistant
from sqlalchemy import bindparam, text


async def query(
    hass: HomeAssistant,
    sql: str,
    params: dict[str, Any] | None = None,
    expanding: Iterable[str] = (),
) -> list[tuple]:
    """Retorna lista de tuplas.

    `expanding` lista os binds que recebem uma LISTA (`... IN :ids`). SQLAlchemy precisa saber
    disso na compilacao — `= ANY(:ids)` do psycopg nao sobrevive ao `text()` sem tipagem.
    """
    binds = [bindparam(name, expanding=True) for name in expanding]

    def _run() -> list[tuple]:
        with session_scope(hass=hass, read_only=True) as session:
            stmt = text(sql)
            if binds:
                stmt = stmt.bindparams(*binds)
            return [tuple(row) for row in session.execute(stmt, params or {})]

    return await get_instance(hass).async_add_executor_job(_run)
