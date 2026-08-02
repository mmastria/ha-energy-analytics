# Árvore de energia da instância (snapshot 2026-08-02)

**Isto é snapshot para orientação, não fonte de verdade.** Em runtime a árvore vem AO VIVO de
`energy.data.async_get_manager(hass)` — se o usuário mexer no painel de Energia, o painel segue e
este arquivo fica velho. Para reconferir: `mcp__ha-mcp__ha_manage_energy_prefs` (get) — é o único
caminho, não há acesso ao `.storage/energy` do host.

## Fontes (5 usadas + 1 ignorada)

| papel | entidade |
|---|---|
| `SOLAR` | `sensor.inverter_input_yield_energy` |
| `GRID_IN` | `sensor.pwm_grid_energy` |
| `GRID_OUT` | `sensor.pwm_grid_exported_energy` |
| `BATT_DIS` | `sensor.batteries_total_discharge` |
| `BATT_CHG` | `sensor.batteries_total_charge` |
| — **ignorada** — | fonte `type: water` (`sensor.registro_water_total`, m³) |

⚠️ **Solar = PV, não AC.** O inversor Huawei é **DC-coupled**: `sensor.inverter_active_energy`
(AC) já desconta a bateria e dobraria a contagem. A fonte é e continua sendo o PV
`sensor.inverter_input_yield_energy`.

⚠️ **Energia nunca toca água.** A fonte `water` existe nas prefs mas está fora deste app.

## Devices (28) — a ordem **é** a cor

`palette.device(i)` usa exatamente este índice. Reordenar no painel de Energia troca todas as cores.

| i | entidade | `included_in_stat` (pai) |
|---|---|---|
| 0 | `sensor.pwm_balcao_energy` | |
| 1 | `sensor.pwm_geladeira_energy` | `sensor.djt_pvac_110_energy` |
| 2 | `sensor.pwm_elevador_energia` | |
| 3 | `sensor.pwm_q3_13l_ext_energy` | |
| 4 | `sensor.pwm_lavadora_energy` | |
| 5 | `sensor.pwm_secadora_energy` | |
| 6 | `sensor.ar_do_loft_energy` | |
| 7 | `sensor.djt_mesa_energy` | `sensor.djt_pvac_110_energy` |
| 8 | `sensor.pwm_q3_03t_bar_mz_energy` | |
| 9 | `sensor.pwm_q3_14t_loft_energy` | |
| 10 | `sensor.ar_do_mezanino_energy` | |
| 11 | `sensor.djt_rowa_1_energy` | `sensor.djt_pvac_220_energy` |
| 12 | `sensor.pwm_oficina_energy` | |
| 13 | `sensor.djt_piscina_energy` | `sensor.pwm_oficina_energy` |
| 14 | `sensor.ar_do_quarto_energy` | `sensor.djt_pvac_220_energy` |
| 15 | `sensor.pwm_q2_13t_quarto_energy` | |
| 16 | `sensor.pwm_q2_14t_q_nich_energy` | |
| 17 | `sensor.ar_da_sala_energy` | |
| 18 | `sensor.pwm_rack_da_sala_energy` | `sensor.djt_pvac_110_energy` |
| 19 | `sensor.djt_rack_do_loft_energy` | `sensor.djt_pvac_110_energy` |
| 20 | `sensor.ar_do_nicholas_energy` | |
| 21 | `sensor.djt_pvac_110_energy` | |
| 22 | `sensor.djt_pvac_220_energy` | |
| 23 | `sensor.pwm_q1_15t_sala_deq_energy` | |
| 24 | `sensor.pwm_garagem_energy` | |
| 25 | `sensor.pwm_q1_17t_gar_energy` | `sensor.pwm_garagem_energy` |
| 26 | `sensor.pwm_q1_08lt_gar_energy` | `sensor.pwm_garagem_energy` |
| 27 | `sensor.djt_consul_energy` | `sensor.pwm_q1_17t_gar_energy` |

Profundidade máxima 3 (`pwm_garagem → pwm_q1_17t_gar → djt_consul`). `tree.nodes()` acha a raiz e
desce recursivamente; `TOP_LEVEL` = device sem `included_in_stat`.

## Vocabulário da casa (`labels._FIX`)

`pwm`, `djt`, `pvac`, `q1`/`q2`/`q3` são prefixos reais de quadro/medidor — mantidos em caixa
própria no rótulo derivado. A derivação só entra em cena quando as prefs não trazem `name` e o
`hass.states` não tem `friendly_name`.
