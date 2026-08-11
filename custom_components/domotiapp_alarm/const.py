"""Constanten voor DomotiApp Alarm."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "domotiapp_alarm"

# --- Frontend (SPEC 2) --------------------------------------------------
# Bestandsnaam van de gebundelde Lovelace-kaart, en het URL-pad waarop de
# integratie hem serveert.
CARD_FILENAME: Final = "domotiapp-alarm-card.js"
CARD_URL_PATH: Final = f"/{DOMAIN}/{CARD_FILENAME}"

# De tweede laadroute. `module` is het enige type dat een ES-module importeert.
RESOURCE_TYPE: Final = "module"

# Lengte van de hash in de ?v=. De hash is die van het bundelbestand, niet het
# versienummer: alleen dan verandert de URL precies wanneer de inhoud verandert.
HASH_LENGTE: Final = 12

# --- Sleutels in hass.data[DOMAIN] --------------------------------------
DATA_STATIC_PATH_REGISTERED: Final = "static_path_registered"
DATA_JS_URL: Final = "js_url"
DATA_ENTRY_COUNT: Final = "entry_count"
DATA_RESOURCE_ID: Final = "resource_id"
DATA_STORE: Final = "store"
DATA_WS_REGISTERED: Final = "ws_registered"
DATA_RINGING: Final = "ringing"
DATA_PLANNER: Final = "planner"
DATA_VOORBEELD: Final = "voorbeeld"

# --- Opslag (SPEC 14.1) -------------------------------------------------
STORAGE_KEY: Final = f"{DOMAIN}.alarms"
STORAGE_VERSION: Final = 1
STORAGE_MINOR_VERSION: Final = 1

# --- Labels (SPEC 7.1) --------------------------------------------------
# De namen die de eigenaar plakt. De integratie zoekt het label_id erbij en
# werkt daarna met dat ID, want hernoemen laat het label_id ongemoeid.
LABEL_SPEAKER_NAAM: Final = "Music Assistant Wekker"
LABEL_LAMP_NAAM: Final = "Verlichting Wekker"

# --- Music Assistant ----------------------------------------------------
MA_DOMAIN: Final = "music_assistant"
# Het attribuut waarin MA het spelertype zet. Let op: extra state attributes
# verdwijnen zodra een entiteit unavailable is (SPEC 7.2), dus dit is nooit de
# enige zeef.
ATTR_MASS_PLAYER_TYPE: Final = "mass_player_type"
MASS_PLAYER_TYPE_GROUP: Final = "group"

# --- Planner (SPEC 13.4) ------------------------------------------------
# Het respijtvenster: een gemiste wekker gaat alsnog af als hij minder dan zoveel
# minuten te laat is. Bewust een eigen constante en niet dezelfde als de
# automatische stop uit SPEC 9.4: dat die ook 30 is, is toeval.
RESPIJT_MINUTEN: Final = 30

# --- Afvuren (SPEC 9) ---------------------------------------------------
# De volume-oploop: 20 stappen van 1 seconde, van 0 naar het ingestelde niveau.
# SPEC 9.3 legt dit vast als één constante, met opzet: klinkt de oploop trapsgewijs,
# dan wordt dit getal verhoogd en verandert er niets anders. De techniek laat 100
# stappen toe — de volumeresolutie is 1 % en een aanroep kost 3–6 ms (gemeten in
# fase 0b) — dus de bovengrens wordt door het gehoor bepaald, niet door MA.
OPLOOP_STAPPEN: Final = 20
OPLOOP_STAP_SECONDEN: Final = 1.0

# De oploop breekt af als het gelezen volume meer dan zoveel procentpunt afwijkt van
# wat de oploop zelf net zette (SPEC 9.3). Zonder deze regel vecht de integratie met
# de gebruiker: hij draait zachter, de volgende stap zet het weer harder.
OPLOOP_AFBREEK_MARGE_PCT: Final = 5

# De tweede noodremcontrole, zoveel seconden ná het starten van het geluid
# (SPEC 11.3). Lang genoeg dat MA de stream heeft opgezet, kort genoeg dat de klant
# nog niet is doorgeslapen.
NOODREM_NA_SECONDEN: Final = 5.0

# De wekker stopt automatisch na zoveel minuten (SPEC 9.4). Bewust een eigen
# constante en niet dezelfde als RESPIJT_MINUTEN: SPEC 13.4 zegt uitdrukkelijk dat
# het toeval is dat die ook 30 is.
STOP_NA_MINUTEN: Final = 30

# Providerdomeinen die `ProviderFeature.SIMILAR_TRACKS` ondersteunen, afgeleid uit
# MA's broncode (SPEC 8.3.1). Alleen dán wordt `radio_mode` meegestuurd.
#
# LET OP — deze lijst kan STIL verouderen. Hij hoort nagelopen te worden bij elke
# MA-release, en dat staat als openstaand punt in CLAUDE.md. Erop vertrouwen is niet
# genoeg: `afvuren.py` vangt de HTTP 500 van `play_media` op en probeert het opnieuw
# zonder `radio_mode`. De lijst is de optimalisatie, de terugval is de garantie.
#
# Geen van de gratis radio- en podcastproviders heeft de feature; het zijn de
# streamingproviders en de mediaservers.
SIMILAR_TRACKS_PROVIDERS: Final[frozenset[str]] = frozenset(
    {
        "spotify",
        "tidal",
        "apple_music",
        "ytmusic",
        "deezer",
        "soundcloud",
        "plex",
        "jellyfin",
        "emby",
        "opensubsonic",
        "subsonic",
        "qobuz",
    }
)

# Mediasoorten die uit zichzelf niet ophouden (SPEC 8.3). Voor deze twee is de
# waarschuwing uit 8.3.1 nooit nodig, ongeacht de provider.
#
# Een afspeellijst staat er bewust bij: hij is niet oneindig maar wél van
# onbepaalde duur, en in de praktijk langer dan de stoptimer van 30 minuten
# (SPEC 9.4). SPEC 8.3 noemt radio en afspeellijst samen als "de soorten die bij
# een wekker passen".
ONEINDIGE_SOORTEN: Final[frozenset[str]] = frozenset({"radio", "playlist"})

# --- Standaardwaarden voor een nieuwe wekker (SPEC 14.3) ----------------
DEFAULT_TIME: Final = "07:00"
DEFAULT_VOLUME_PCT: Final = 40

# --- Grenzen uit het schema (SPEC 14.2) ---------------------------------
VOLUME_PCT_MIN: Final = 1
VOLUME_PCT_MAX: Final = 100
BRIGHTNESS_PCT_MIN: Final = 1
BRIGHTNESS_PCT_MAX: Final = 100
# ISO-weekdagen: 1 = maandag t/m 7 = zondag.
WEEKDAG_MIN: Final = 1
WEEKDAG_MAX: Final = 7

# --- De voorbeeldknop (SPEC 5.4 en 15.11) -------------------------------
# Een voorbeeld stopt hoe dan ook na zoveel minuten. Een abonnement leeft zolang
# de verbinding leeft, en een browsertabblad dat openblijft op een editor kan
# dagen leven. **VOORSTEL**: SPEC 5.4 legt geen maximum vast.
VOORBEELD_MAX_MINUTEN: Final = 5

# Zoekopdracht (SPEC 15.6).
SEARCH_LIMIT_DEFAULT: Final = 10
SEARCH_LIMIT_MAX: Final = 50
SEARCH_TIMEOUT_SECONDEN: Final = 10

# --- Meldingen (SPEC 11.7 en 14.2.1) ------------------------------------
SEVERITY_ERROR: Final = "error"
SEVERITY_NOTICE: Final = "notice"

# --- Reparatiemeldingen (SPEC 19.2) -------------------------------------
ISSUE_CORRUPT_PERSON_PREFIX: Final = "corrupte_opslag_"
ISSUE_STORE_UNUSABLE: Final = "opslag_onbruikbaar"
