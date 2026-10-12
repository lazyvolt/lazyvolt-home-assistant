# LazyVolt for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/lazyvolt/lazyvolt-home-assistant.svg)](https://github.com/lazyvolt/lazyvolt-home-assistant/releases)

Connect your [LazyVolt](https://lazyvolt.com) account to Home Assistant. LazyVolt automatically schedules your EV charging around cheap grid hours and solar production — this integration applies those decisions directly to your Peblar charger.

## Pricing & availability

- **LazyVolt Cloud is a commercial service.** It is free while LazyVolt is in alpha; a subscription of roughly €5 per month is planned once the service is stable. Every charge decision comes from LazyVolt Cloud, so this integration does nothing without an active LazyVolt account.
- **Netherlands only.** Planning uses Dutch day-ahead prices and Dutch energy taxes, so LazyVolt currently only supports households in the Netherlands.

## How it works

Every 30 seconds the integration:

1. Fetches the current charge decision from LazyVolt Cloud (`SOLAR`, `MAX`, or `STANDBY`)
2. Applies the decision to your Peblar charger via the Peblar HA integration
3. Reports charger state and session energy back to LazyVolt Cloud

**SOLAR** → sets Peblar to *Smart Solar* mode (Peblar's built-in solar intelligence handles P1 load-balancing)
**MAX** → sets Peblar to *Default* mode (charge at full speed)
**STANDBY** → turns the charger off

### Fail-safe behaviour

The integration only acts on the three modes above. If LazyVolt Cloud is unreachable, rejects the login, or returns anything else, the charger is left exactly as it is — it is never switched on because of a missing or malformed decision.

## Entities

Each configured charger gets a **LazyVolt** service device with:

| Entity | Description |
|--------|-------------|
| Charge mode | Mode LazyVolt Cloud currently dictates: `solar`, `max` or `standby`; unknown when Cloud sends something unrecognised |
| Cloud connection | Diagnostic; on while the last poll of LazyVolt Cloud succeeded |
| Last decision | Diagnostic; when LazyVolt Cloud last answered — keeps its value during an outage so you can see how long it has lasted |

## Requirements

- A [LazyVolt](https://lazyvolt.com) account (see [Pricing & availability](#pricing--availability))
- The [Peblar integration](https://www.home-assistant.io/integrations/peblar/) installed and configured in Home Assistant
- Home Assistant 2024.11 or newer

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/lazyvolt/lazyvolt-home-assistant` with category **Integration**
3. Search for **LazyVolt** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/lazyvolt` folder to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **LazyVolt**
3. Enter the email and password you use on [lazyvolt.com](https://lazyvolt.com)
4. Give this Home Assistant instance a name (shown in your LazyVolt dashboard). Use a different name for every charger: logging in with a name that is already in use disconnects the edge that had it.
5. Select your Peblar charger — if only one is available it is selected automatically

Each Peblar charger can be added once. If the edge is removed from your LazyVolt dashboard, or another device logs in with the same edge name, Home Assistant shows a **Reconfigure** prompt — log in again there and the integration resumes.

## Troubleshooting

**Charger not responding to mode changes**
Make sure the Peblar integration is installed and the charger is reachable. Check that the `smart_charging` select entity is enabled in Home Assistant.

**"Cannot connect" during setup**
Verify your lazyvolt.com credentials and that Home Assistant has internet access.

**Cloud connection is off**
Home Assistant cannot reach LazyVolt Cloud. The charger keeps its last mode until the connection returns. Check the Home Assistant logs (`Settings → System → Logs`) for errors from the `lazyvolt` component.

## Contributing

Issues and pull requests welcome at [github.com/lazyvolt/lazyvolt-home-assistant](https://github.com/lazyvolt/lazyvolt-home-assistant/issues).
