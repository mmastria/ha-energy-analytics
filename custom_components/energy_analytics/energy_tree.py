"""Arvore de energia AO VIVO, lida do manager do painel de Energia do HA.

Substitui o snapshot `ha.storage.energy` do app Flask: `EnergyManager.data` e' exatamente o
mesmo dict do `.storage/energy`, na MESMA ordem. Isso importa: a cor de cada device vem da
POSICAO dele em `device_consumption` (ver `palette.device`), entao a ordem e' carga util, nao
detalhe de serializacao.

Reconstruido a cada request (dezenas de entradas — custo irrisorio) para que mudar o dashboard
de Energia apareca no painel sem reiniciar o HA.
"""
from __future__ import annotations

from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


class EnergyTree:
    """Espelho de `analytics_app/config.py`: mesmas chaves, montadas do dict das prefs."""

    def __init__(self, prefs: dict) -> None:
        sources = {s["type"]: s for s in prefs["energy_sources"]}
        devices = prefs["device_consumption"]

        missing = [t for t in ("grid", "solar", "battery") if t not in sources]
        if missing:
            raise HomeAssistantError(
                f"painel de Energia sem as fontes {', '.join(missing)} — configure-as primeiro"
            )

        self.GRID_IN = sources["grid"]["stat_energy_from"]
        self.GRID_OUT = sources["grid"]["stat_energy_to"]
        self.SOLAR = sources["solar"]["stat_energy_from"]
        self.BATT_DIS = sources["battery"]["stat_energy_from"]
        self.BATT_CHG = sources["battery"]["stat_energy_to"]

        self.DEVICE_ENTITIES = [d["stat_consumption"] for d in devices]
        self.DEVICE_NAMES = {d["stat_consumption"]: d.get("name") for d in devices}
        self.DEVICE_INDEX = {e: i for i, e in enumerate(self.DEVICE_ENTITIES)}

        self.INCLUDED: dict[str, str] = {}   # filho -> pai
        self.CHILDREN: dict[str, list[str]] = {}  # pai -> [filhos]
        for d in devices:
            parent = d.get("included_in_stat")
            if parent:
                self.INCLUDED[d["stat_consumption"]] = parent
                self.CHILDREN.setdefault(parent, []).append(d["stat_consumption"])
        self.TOP_LEVEL = [e for e in self.DEVICE_ENTITIES if e not in self.INCLUDED]

        # Fontes na ordem do card `Sources` do HA: solar -> bateria -> rede.
        self.SOURCE_ENTITIES = [self.SOLAR, self.BATT_DIS, self.BATT_CHG,
                                self.GRID_IN, self.GRID_OUT]
        self.ALL_ENTITIES = self.SOURCE_ENTITIES + self.DEVICE_ENTITIES


def _flat(source: dict, key: str, flows_key: str) -> str | None:
    """`stat_energy_from`/`_to` do grid.

    Esta instancia (HA 2026.7) guarda os dois no primeiro nivel. Versoes que usam as listas
    `flow_from`/`flow_to` caem no fallback — o valor plano SEMPRE vence, para a normalizacao
    nunca sobrescrever com `None` o que ja estava certo.
    """
    if source.get(key):
        return source[key]
    flows = source.get(flows_key) or []
    if not flows:
        return None
    return flows[0].get(key)


async def async_get_tree(hass: HomeAssistant) -> EnergyTree:
    """Le as prefs do painel de Energia e monta a arvore."""
    manager = await async_get_manager(hass)
    if not manager.data:
        raise HomeAssistantError("painel de Energia do HA ainda nao foi configurado")

    prefs = dict(manager.data)
    normalized = []
    for src in prefs["energy_sources"]:
        if src["type"] == "grid":
            src = dict(src)
            src["stat_energy_from"] = _flat(src, "stat_energy_from", "flow_from")
            src["stat_energy_to"] = _flat(src, "stat_energy_to", "flow_to")
        normalized.append(src)
    prefs["energy_sources"] = normalized
    return EnergyTree(prefs)
