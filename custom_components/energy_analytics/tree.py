"""Arvore de entidades do Energy Dashboard: 5 fontes + N devices hierarquicos.

Cor: MESMA regra do EnergyHome (`palette.device(i)`, `i` = posicao em `device_consumption`;
fontes usam as CSS vars `--energy-*-color`). A cor e presa a entidade, nunca a ordem do grafico.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from . import labels, palette
from .const import HOME_ID, HOME_LABEL, SUM_PREFIX, UNTRACKED_PREFIX
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
    if entity == HOME_ID:
        return palette.HOME
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


def _synthetic(tree: EnergyTree, parent: str, depth: int, kind: str) -> dict:
    """Linha derivada de um no com filhos — nao e' entidade do HA.

    `sum` herda a cor do pai (o front a desenha TRACEJADA, para nao se confundir com a linha
    do proprio pai); `untracked` usa o cinza de "nao monitorado" do HA.
    """
    is_sum = kind == "sum"
    return {
        "entity": (SUM_PREFIX if is_sum else UNTRACKED_PREFIX) + parent,
        "label": "Σ filhos" if is_sum else "(untracked)",
        "color": color(tree, parent) if is_sum else palette.UNTRACKED,
        "depth": depth,
        "group": "device",
        "children": 0,
        "parent": parent,     # so' e' selecionavel com o pai seleciona
        "synthetic": kind,
    }


def _walk(hass: HomeAssistant, tree: EnergyTree, entity: str, depth: int, out: list) -> None:
    out.append(_node(hass, tree, entity, depth, "device"))
    kids = tree.CHILDREN.get(entity, [])
    if kids:
        # `Σ filhos` abre a lista de filhos, `(untracked)` a fecha — ambos no nivel dos filhos.
        out.append(_synthetic(tree, entity, depth + 1, "sum"))
    for child in kids:
        _walk(hass, tree, child, depth + 1, out)
    if kids:
        out.append(_synthetic(tree, entity, depth + 1, "untracked"))


def nodes(hass: HomeAssistant, tree: EnergyTree) -> list[dict]:
    """Lista PLANA na ordem de exibicao; `depth` da a identacao da arvore de consumo.

    A raiz dos devices e' o `Total consumed` do painel de Energia — consumo da casa, derivado das
    5 fontes (nao e' entidade). Os devices de topo sao filhos dele, entao a linha `(untracked)` da
    raiz e' exatamente o `Untracked consumption` que o HA mostra.
    """
    out = [_node(hass, tree, e, 0, "source") for e in tree.SOURCE_ENTITIES]
    out.append({
        "entity": HOME_ID,
        "label": HOME_LABEL,
        "color": palette.HOME,
        "depth": 0,
        "group": "device",
        "children": len(tree.TOP_LEVEL),
    })
    out.append(_synthetic(tree, HOME_ID, 1, "sum"))
    for e in tree.TOP_LEVEL:
        _walk(hass, tree, e, 1, out)
    out.append(_synthetic(tree, HOME_ID, 1, "untracked"))
    return out
