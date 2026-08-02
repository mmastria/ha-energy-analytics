"""Arvore de entidades do Energy Dashboard: 5 fontes + N devices hierarquicos.

Cor: MESMA regra do EnergyHome (`palette.device(i)`, `i` = posicao em `device_consumption`;
fontes usam as CSS vars `--energy-*-color`). A cor e presa a entidade, nunca a ordem do grafico.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from . import labels, palette
from .energy_tree import EnergyTree


def _source_color(tree: EnergyTree) -> dict[str, str]:
    return {
        tree.SOLAR: palette.SOLAR,
        tree.BATT_DIS: palette.BATT_OUT,
        tree.BATT_CHG: palette.BATT_IN,
        tree.GRID_IN: palette.GRID_IN,
        tree.GRID_OUT: palette.GRID_OUT,
    }


def color(tree: EnergyTree, entity: str) -> str:
    src = _source_color(tree)
    if entity in src:
        return src[entity]
    i = tree.DEVICE_INDEX.get(entity)
    return palette.device(i) if i is not None else palette.UNTRACKED


def _node(hass: HomeAssistant, tree: EnergyTree, entity: str, depth: int, group: str) -> dict:
    return {
        "entity": entity,
        "label": labels.pretty(hass, tree, entity),
        "color": color(tree, entity),
        "depth": depth,
        "group": group,
        "children": len(tree.CHILDREN.get(entity, [])),
    }


def _walk(hass: HomeAssistant, tree: EnergyTree, entity: str, depth: int, out: list) -> None:
    out.append(_node(hass, tree, entity, depth, "device"))
    for child in tree.CHILDREN.get(entity, []):
        _walk(hass, tree, child, depth + 1, out)


def nodes(hass: HomeAssistant, tree: EnergyTree) -> list[dict]:
    """Lista PLANA na ordem de exibicao; `depth` da a identacao da arvore de consumo."""
    out = [_node(hass, tree, e, 0, "source") for e in tree.SOURCE_ENTITIES]
    for e in tree.TOP_LEVEL:
        _walk(hass, tree, e, 0, out)
    return out
