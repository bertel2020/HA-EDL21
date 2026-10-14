<h1 align="center">EDL21 – smart meter reading head for Home Assistant</h1>

<p align="center">
  Read electricity meters with an SML interface (EDL21) locally, also via ser2net.
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2.svg?logo=home-assistant&logoColor=white" alt="Home Assistant"></a>
  <a href="https://github.com/bertel2020/HA-EDL21/releases"><img src="https://img.shields.io/github/v/release/bertel2020/HA-EDL21?sort=semver&include_prereleases" alt="Release"></a>
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

- setup with connection check, port changeable later (**Reconfigure**)
- configurable **update interval** and optional **minimum change** for power sensors
- diagnostic sensor **Last telegram**; sensors become *unavailable* when the reading head is silent
- **repair issue** when no data arrives for more than 10 minutes
- unknown OBIS codes exposed as sensors that are disabled by default
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

Enter a device path (e.g. `/dev/serial/by-id/…`) or a ser2net address
(`socket://192.168.1.10:2000`) as port. To change it later, open the entry and
choose **Reconfigure**.

**Options** (cog on the entry):

| Option | Meaning |
|---|---|
| Update interval | Maximum rate at which a sensor gets a new value (1–3600 s, default 15). |
| Minimum power change | Power sensors are only written when the value changed by at least this many watts (0 = off). |

Sensors become *unavailable* after 3 minutes without a telegram.

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
