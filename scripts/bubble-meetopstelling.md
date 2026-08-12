# De Bubble Card-meetopstelling (fase 9)

Dit is de conditie waarin de klant de kaart gebruikt, en tot fase 9 is er nooit in
gemeten. `grid_options: {columns: 6}` maakt de kaart smal, maar een Bubble
Card-pop-up is iets anders: eigen breedte, eigen padding, eigen scrollcontainer, en
op een telefoon is hij **schermvullend**.

Alles hieronder staat klaar op de dev-instance (8129) en is met deze stappen
opnieuw op te zetten.

---

## 1. Bubble Card installeren

Er staat **geen HACS** op de dev-instance, dus de route is de handmatige die Bubble
Card zelf documenteert: het bestand in `www/` en registreren als Lovelace-resource.

```powershell
cd C:\dev\domotiapp-alarm
mkdir .ha-dev-config\www
curl -sL -o .ha-dev-config\www\bubble-card.js `
  https://raw.githubusercontent.com/Clooos/Bubble-Card/v3.2.5/dist/bubble-card.js
docker restart ha-alarm
```

**De herstart is niet optioneel.** HA registreert het statische pad voor `/local/`
bij het opstarten; bestond `www/` toen nog niet, dan geeft hij 404 op alles eronder
— ook nadat je de map hebt gemaakt.

Daarna de resource aanmelden. Vanuit de console op een HA-pagina:

```js
const hass = document.querySelector('home-assistant').hass;
await hass.callWS({ type: 'lovelace/resources/create',
                    res_type: 'module', url: '/local/bubble-card.js?v=3.2.5' });
```

## 2. De rig en de meetfunctie

```powershell
copy scripts\telefoon.html      .ha-dev-config\www\telefoon.html
copy scripts\meet-afsnijden.js  .ha-dev-config\www\meet-afsnijden.js
```

`telefoon.html` zet een HA-dashboard in een iframe van een vaste breedte, omdat het
browservenster van de meetsessie **niet te verkleinen is**: het tabblad rendert
buiten beeld op een vaste viewport van 1920 px, `resize_window` meldt succes en
verandert niets, en `window.outerWidth` is 0. Zie de kop van dat bestand, inclusief
de reden dat het frame `name="ha-main-window"` moet dragen.

## 3. Het dashboard

Op dashboard `fase-4a` staat de view **`bubble-echt`**. Bubble Card gebruikt sinds
v3.2.0 het **standalone** formaat: de inhoud staat rechtstreeks onder `cards:` in de
pop-up, en er komt **geen `vertical-stack`** meer aan te pas.

```yaml
- type: custom:bubble-card
  card_type: button
  button_type: name
  name: Wekkers openen
  icon: mdi:alarm
  tap_action:
    action: navigate
    navigation_path: '#wekker'
- type: custom:bubble-card
  card_type: pop-up
  hash: '#wekker'
  name: Wekkers
  icon: mdi:alarm
  cards:
    - type: custom:domotiapp-alarm-card
      person: person.dev
```

## 4. Meten

```
http://localhost:8129/local/telefoon.html#390|/fase-4a/bubble-echt#wekker
```

Het `#wekker` achteraan is nodig: Bubble Card bouwt de inhoud van een standalone
pop-up **pas als de hash bij het laden aanwezig is**, en breekt hem bij het sluiten
weer af. Openen daarna:

```js
const w = document.getElementById('frame').contentWindow;
w.history.pushState(null, '', w.location.pathname + '#wekker');
w.dispatchEvent(new w.CustomEvent('location-changed',
  { detail: { replace: false }, bubbles: true, composed: true }));
```

Dat is letterlijk wat HA's eigen `navigate()` doet. Het is **programmatisch** —
meld dat, net als bij valkuil 11. Alles ná het openen is met echte kliks te doen.

Meten:

```js
const m = await import('/local/meet-afsnijden.js');
m.meet(document.getElementById('frame').contentWindow);
```

En versmallen zonder de toestand kwijt te raken — dit is de breedtesweep die fase 8
niet lukte:

```js
document.getElementById('frame').style.width = '244px';
```

## 5. Wat er op de instance klaarstaat

| | |
|---|---|
| view | `/fase-4a/bubble-echt` — echte Bubble Card-pop-up, standalone formaat |
| wekkers | vijf, waaronder **"Zaterdagochtendzwemtraining"** (26 tekens, één woord) |
| waarom die naam | een lange naam is invoer van de klant en heeft geen bovengrens; hij is wat de bevinding van fase 9 blootlegde. Laat hem staan |
| breedtes | 390 px is de meetconditie (iPhone-portret). 244 px pop-up = **208 px kaart**, strenger dan `/fase-4a/bubble` (dat is 244 px **kaart**) |
