<h1 align="center">EDL21 – smart meter reading head for Home Assistant</h1>

<p align="center">
  Read electricity meters with an SML interface (EDL21) locally, also via ser2net.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2.svg?logo=home-assistant&logoColor=white" alt="Home Assistant"></a>
  <a href="https://github.com/bertel2020/HA-EDL21/releases"><img src="https://img.shields.io/github/v/release/bertel2020/HA-EDL21?sort=semver&include_prereleases" alt="Release"></a>
  <a href="https://github.com/bertel2020/HA-EDL21/actions/workflows/validate.yml"><img src="https://github.com/bertel2020/HA-EDL21/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/bertel2020/HA-EDL21" alt="License"></a>
</p>

<p align="center">
  <a href="https://buymeacoffee.com/bertel2020"><img src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buy-me-a-coffee&logoColor=black" alt="Buy Me a Coffee"></a>
  <a href="https://ko-fi.com/bertel2020"><img src="https://img.shields.io/badge/Ko--fi-support-FF5E5B?logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
  <a href="https://paypal.me/RobertoMartins"><img src="https://img.shields.io/badge/PayPal-donate-00457C?logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

<p align="center"><em><a href="https://github.com/bertel2020/HA-EDL21/blob/main/README.de.md">Deutsche Version</a></em></p>

Custom integration for electricity meters with an SML interface (EDL21), e.g.
via an optical reading head. Connect it directly via USB or through **ser2net**
(`socket://host:port`). Based on the core `edl21` integration, with:

- setup with a USB device picker or ser2net host/port, connection check, connection changeable later (**Reconfigure**)
- configurable **update interval** and optional **minimum change** for power sensors
- diagnostic sensors **Last telegram**, **Reconnects** and **Telegram rate** (disabled by default); sensors become *unavailable* when the reading head is silent
- **Test connection** button: waits for the next telegram and reports its OBIS codes
- **repair issue** when no data arrives for more than 10 minutes
- more OBIS codes than core (feed-in power `2.7.0`, tariff T3, device ID `96.1.1`); unknown codes are exposed as sensors that are disabled by default
- identifiers, versions and status values are updated immediately on change, measurements follow the update interval
- diagnostics download (without host, port and meter ID)
- clean removal of entry and device

## Note: replaces the core integration

This integration deliberately uses the same domain `edl21` as the integration
bundled with Home Assistant and **replaces** it while installed under
`custom_components`. Existing entries, sensors and history are kept. Home
Assistant logs a warning about a custom integration at startup. To switch back,
remove `custom_components/edl21` (or uninstall via HACS) and restart.

## Note: dependencies

`pysml` requires `bitstring` without an upper bound. With `bitstring` 5.0,
parsing telegrams fails (`module 'bitstring' has no attribute
'ConstBitStream'`) and the connection is re-established over and over. This
integration therefore pins `bitstring==4.4.0` in `manifest.json`. An error
with this text means another integration forces a newer version.

## Requirements

Home Assistant 2026.10 or newer (device picker and options flow). The `usb`
integration is loaded automatically as a dependency.

## Installation

### Via HACS (recommended)

[![Open the HACS repository in My Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bertel2020&repository=HA-EDL21&category=integration)
[![Add EDL21 to My Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=edl21)

1. Use the first button to open the EDL21 repository in HACS.
2. Download **EDL21** and restart Home Assistant.
3. Use the second button to add the integration. Alternatively open **Settings
   → Devices & services → Add integration → EDL21**.

If the first button does not work, add `https://github.com/bertel2020/HA-EDL21`
in HACS under **Integrations → Custom repositories** as category **Integration**.

### Manual

Copy the `custom_components/edl21` directory to `/config/custom_components/edl21`
and restart Home Assistant.

## Configuration

When adding the integration, choose how the reading head is connected:

- **USB / serial device:** pick the device from the list (prefer the stable
  `/dev/serial/by-id/…` entry).
- **Network (ser2net / TCP):** enter host and port of the ser2net server
  (stored as `socket://host:port`).

To change the connection later, open the entry and choose **Reconfigure**.

**Options** (cog on the entry):

| Option | Meaning |
|---|---|
| Update interval | Maximum rate at which a sensor gets a new value (1–3600 s, default 15). |
| Minimum power change | Power sensors are only written when the value changed by at least this many watts (0 = off). |

Sensors become *unavailable* after 3 minutes without a telegram. After 10
minutes without data a repair issue with the configured port appears.

## Supported OBIS codes

Energy `1.8.x` / `2.8.x` (total, T1–T3), power `1.7.0`, `2.7.0`, `15.7.0`,
`16.7.0` and per phase (`36/56/76.7.0`), voltage and current per phase, supply
frequency, phase angles, meter and device IDs, firmware and status values.
Codes that are not known appear as disabled sensors named **OBIS …** and can be
enabled individually. Your meter usually only sends a subset; the codes it actually
sends are listed in the diagnostics download under `seen_obis`.

## Energy dashboard

Use these sensors (names depend on your language and renames):

| Dashboard field | Sensor (OBIS) |
|---|---|
| Grid consumption | Positive active energy total (`1-0:1.8.0`) |
| Return to grid | Negative active energy total (`1-0:2.8.0`) |
| Power (live) | Sum active instantaneous power (`1-0:16.7.0`) |

If you replace the core integration, keep the existing entities: the unique IDs
stay the same, so history and the dashboard configuration are preserved. Entities
that Home Assistant created for old entity IDs (cost/compensation sensors of the
energy dashboard) stay `unavailable` and can be deleted.

## Troubleshooting

Press **Test connection** (diagnostic button): it waits up to 15 seconds for a
telegram and reports the received OBIS codes in a notification. The **Reconnects**
sensor counts re-connections; steadily rising values point to an unstable
ser2net, cable or reading head. The **Download diagnostics** function contains
the `pysml` version, connection type and seen OBIS codes, without host, port or
meter ID.

## Disclaimer

EDL21 is a privately developed, free open-source project and is provided without
warranty or guarantee. Use is at your own risk; in particular, no guarantee can be
given for error-free operation or for the correctness, completeness or availability
of the meter values. **The values are not calibrated measurements and must not be
used for billing; only the meter of your metering point operator is authoritative.**
The integration only reads the meter and never writes back.

## License

This project is released under the [MIT License](LICENSE).
Copyright 2026 Roberto / bertel2020.
