# DomotiApp Alarm

Een wekkerkaart voor Home Assistant.

DomotiApp Alarm is een custom integration (domein `domotiapp_alarm`) met eigen
opslag en WebSocket-commando's, plus een Lovelace-kaart (custom element
`domotiapp-alarm-card`) die de integratie zelf serveert en registreert. De klant
hoeft geen Lovelace-resource toe te voegen.

Een wekker gaat af op de ingestelde wandkloktijd, ook wanneer er geen browser
openstaat en ook wanneer Home Assistant 's nachts herstart is.

## Minimum Home Assistant-versie

**2026.8**

## Status

**In ontwikkeling — nog niet bruikbaar als wekker.**

Wat er nu staat is de laadketen: de integratie serveert haar eigen kaart en
registreert die langs twee routes. De kaart toont één regel tekst. Er is nog
geen wekkerlogica, geen opslag, geen editor en geen koppeling met Music
Assistant. Er is nog geen release.

## Ontwikkelen

```bash
npm install
npm run build              # bundelt src/ -> custom_components/.../frontend/
npm run verify             # faalt als de gecommitte bundel afwijkt van de bron
npm run check:registratie  # bewaakt de registratieregel
npm test                   # JS-unittests (node --test), geen jsdom
```

De bundel wordt **meegecommit**: HACS levert wat er in de repo staat.

Python-tests draaien niet op Windows — Home Assistant importeert `fcntl`. Draai
ze in Linux:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "C:/dev/domotiapp-alarm:/app" -w /app \
  python:3.14-slim sh -c "pip install -q -r requirements-test.txt && python -m pytest -q"
```

De testinstance staat in `docker-compose.yml` (poort 8129). **Na elke
`npm run build` moet de config entry herladen worden**, want de `?v=` in de
frontend-URL is de hash van het bundelbestand en die wordt bij setup berekend.
