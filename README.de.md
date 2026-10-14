<h1 align="center">EDL21 – Smart-Meter-Lesekopf für Home Assistant</h1>

<p align="center">
  Stromzähler mit SML-Schnittstelle (EDL21) lokal auslesen, auch über ser2net.
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

<p align="center"><em><a href="https://github.com/bertel2020/HA-EDL21/blob/main/README.md">English version</a></em></p>

Custom Integration für Stromzähler mit SML-Schnittstelle (EDL21), z. B. über einen
optischen Lesekopf. Der Zähler kann direkt per USB oder über **ser2net**
(`socket://host:port`) angebunden werden. Basiert auf der Core-Integration
`edl21`, ergänzt um:

- Einrichtung mit Verbindungsprüfung, Port nachträglich änderbar (**Neu konfigurieren**)
- einstellbares **Aktualisierungsintervall** und optionale **Mindeständerung** für Leistungssensoren
- Diagnosesensor **Letztes Telegramm**; Sensoren werden *nicht verfügbar*, wenn der Lesekopf schweigt
- **Reparaturhinweis**, wenn länger als 10 Minuten keine Daten ankommen
- unbekannte OBIS-Kennzahlen als standardmäßig deaktivierte Sensoren
- Diagnose-Download (ohne Host, Port und Zähler-ID)
- sauberes Entfernen von Eintrag und Gerät

## Hinweis: ersetzt die Core-Integration

Diese Integration verwendet bewusst dieselbe Domain `edl21` wie die in Home
Assistant mitgelieferte Core-Integration und **ersetzt** sie, solange sie unter
`custom_components` installiert ist. Bestehende Einträge, Sensoren und
Historie bleiben erhalten. Home Assistant zeigt dazu beim Start eine Warnung
zu einer Custom-Integration an. Zum Zurückwechseln `custom_components/edl21`
entfernen (bzw. in HACS deinstallieren) und neu starten.

## Hinweis: Abhängigkeiten

`pysml` verlangt `bitstring` ohne Obergrenze. Mit `bitstring` 5.0 schlägt das
Parsen der Telegramme fehl (`module 'bitstring' has no attribute
'ConstBitStream'`), die Verbindung wird dann ständig neu aufgebaut. Deshalb
fixiert diese Integration `bitstring==4.4.0` in der `manifest.json`. Ein
Fehler mit diesem Text bedeutet, dass eine andere Integration eine neuere
Version erzwingt.

## Installation

### Über HACS (empfohlen)

[![HACS-Repository in My Home Assistant öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bertel2020&repository=HA-EDL21&category=integration)
[![EDL21 zu My Home Assistant hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=edl21)

1. Über den ersten Button das EDL21-Repository in HACS öffnen.
2. **EDL21** herunterladen und Home Assistant neu starten.
3. Über den zweiten Button die Integration hinzufügen. Alternativ in Home
   Assistant **Einstellungen → Geräte & Dienste → Integration hinzufügen →
   EDL21** öffnen.

Falls der erste Button nicht funktioniert, in HACS unter **Integrationen →
Benutzerdefinierte Repositories** `https://github.com/bertel2020/HA-EDL21` als
Kategorie **Integration** eintragen.

### Manuell

Das Verzeichnis `custom_components/edl21` nach `/config/custom_components/edl21`
kopieren und Home Assistant neu starten.

## Konfiguration

Als Port einen Gerätepfad (z. B. `/dev/serial/by-id/…`) oder eine
ser2net-Adresse (`socket://192.168.1.10:2000`) eintragen. Den Port später
ändern: Eintrag öffnen → **Neu konfigurieren**.

**Optionen** (Zahnrad am Eintrag):

| Option | Bedeutung |
|---|---|
| Aktualisierungsintervall | Wie oft pro Sensor höchstens ein neuer Wert geschrieben wird (1–3600 s, Standard 15). |
| Mindeständerung Leistung | Leistungssensoren werden nur geschrieben, wenn sich der Wert um mindestens so viele Watt geändert hat (0 = aus). |

Sensoren werden nach 3 Minuten ohne Telegramm *nicht verfügbar*.

## Haftungsausschluss

EDL21 ist ein privat entwickeltes, kostenloses Open-Source-Projekt und wird ohne
Gewährleistung oder Garantie bereitgestellt. Die Nutzung erfolgt auf eigene
Verantwortung; insbesondere kann keine Garantie für einen fehlerfreien Betrieb sowie
für die Richtigkeit, Vollständigkeit und Verfügbarkeit der Zählerwerte übernommen
werden. **Die Werte sind keine geeichten Messwerte und dürfen nicht zur Abrechnung
verwendet werden; maßgeblich ist allein der Zähler des Messstellenbetreibers.** Die
Integration liest den Zähler nur aus und schreibt nichts zurück.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
Copyright 2026 Roberto / bertel2020.
