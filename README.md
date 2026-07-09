# PlaiiinLight for Home Assistant

Control [PlaiiinLight](https://plaiiin.com) lamps from Home Assistant:
on/off, solid color, brightness, and the lamp's effects — all over your
local network (HTTP, no cloud).

## Installation (HACS)

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nebeleben&repository=plaiiin-light-homeassistant&category=integration)

Or manually: HACS → Integrations → ⋮ → *Custom repositories* → add
`https://github.com/nebeleben/plaiiin-light-homeassistant` (category
*Integration*), then install **PlaiiinLight** and restart Home Assistant.

## Adding a lamp

The lamp must already be set up on your Wi‑Fi (use the PlaiiinLight app to
onboard it first).  

- **Unclaimed lamp** (nobody has claimed it in the app): it shows up
  automatically under *Settings → Devices & Services* as a discovered
  device. Click *Add* — done, no key needed.
- **Claimed lamp**: ask the owner for a **share key** (PlaiiinLight app →
  lamp → *Sharing* → create a key with role *user*). Home Assistant asks
  for it when you add the lamp. If the key is ever revoked, Home Assistant
  prompts you to re-authenticate with a new one.
- **Manual add** (no mDNS on your network): *Settings → Devices & Services →
  Add integration → PlaiiinLight* and enter the lamp's IP address.

## What you get

One light entity per lamp with:

- On/off (does not interrupt a running effect)
- Color (switches the lamp to solid-color mode)
- Brightness
- Effect dropdown: **Solid** plus every effect on the lamp

## Options

*Settings → Devices & Services → PlaiiinLight → Configure*: poll interval
(default 10 s).

## License

Apache-2.0. The integration talks to the lamp's open, documented HTTP API
from the [PlaiiinLightOS](https://plaiiin.com) firmware project.
