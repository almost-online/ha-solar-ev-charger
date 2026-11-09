---
name: home-assistant-live
description: >-
  Read the live Home Assistant instance for Solar EV Charger through the
  home-assistant MCP server. Use when checking entity ids, sensor units,
  signs, history, config-entry state, or solar_ev_charger logs. Do not use
  it to change charger current unless the user asked.
---

# Home Assistant live checks

MCP namespace: `home-assistant`. URL in `~/.cursor/mcp.json` is `/api/mcp/homeassistant` (admin API). `/api/mcp` is the "All LLM APIs" entry and also works; do not switch this client over to it.

Discover the tool schema with GetDynamicTools before calling.

## Which tool

| Need | Tool |
| --- | --- |
| Find the charger, solar, grid, battery, or SOC entity | `search__search` |
| Read state, unit, and attributes | `homeassistant__render_template` |
| Past power or SOC | `history__get_history` (`entity_ids` required) |
| Is `solar_ev_charger` loaded | `config__get_config_entries` with `domain` |
| Integration errors | `system_log__get_entries`, then `hassio__get_logs` with a `contains` filter |
| Service name before any write | `homeassistant__search_actions` |

## Template for one entity

```jinja
{{ states('sensor.example') }} {{ state_attr('sensor.example', 'unit_of_measurement') }} {{ state_attr('sensor.example', 'device_class') }}
```

## Writes

`homeassistant__call_action` and `config__reload_config_entry` change the house. Use them only when the user asked to change or reload the live system. Do not set charger current to try an idea.

Do not paste long-lived access tokens into the repo or the reply.
