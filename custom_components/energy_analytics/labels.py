"""Rotulo de cada entidade = o `getStatisticLabel` do HA (mesma regra do EnergyHome).

1. `name` das prefs do painel de Energia; 2. `friendly_name` do estado vivo (substitui o
snapshot `ha.entity_labels.json` do app Flask); 3. derivacao do entity_id.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .energy_tree import EnergyTree

_FIX = {
    "energia": "Energy", "energy": "Energy", "pwm": "PWM", "djt": "DJT",
    "pvac": "PVAC", "ac": "AC", "q1": "Q1", "q2": "Q2", "q3": "Q3",
}


def pretty(hass: HomeAssistant, tree: EnergyTree, entity: str) -> str:
    name = tree.DEVICE_NAMES.get(entity)
    if not name:
        state = hass.states.get(entity)
        if state:
            name = state.attributes.get("friendly_name")
    if name:
        return name
    stem = entity.split(".", 1)[-1]
    return " ".join(str(_FIX.get(w, w.capitalize())) for w in stem.split("_"))
