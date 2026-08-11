/**
 * Waar het overloopmenu komt te staan (SPEC 3.2). Puur.
 *
 * ## Waarom dit een eigen berekening is en geen HA-component
 *
 * De opdracht van fase 6b was uitdrukkelijk: gebruik HA's eigen menu-component als
 * die er is, want die heeft de plaatsing, het wegklikken en het toetsenbord al
 * opgelost. **GEMETEN op `/fase-4a/0` in HA 2026.8.1**, vier seconden na het laden
 * en met een verse pagina:
 *
 * | Component | `customElements.get(...)` |
 * |---|---|
 * | `ha-md-menu`, `ha-md-menu-item` | **niet gedefinieerd** |
 * | `ha-button-menu`, `ha-md-button-menu`, `ha-menu` | **niet gedefinieerd** |
 * | `ha-card`, `ha-form`, `ha-select`, `ha-switch`, `ha-list-item` | gedefinieerd |
 *
 * Geen enkele menu-component is er dus. Dat is valkuil 44 en 50: een HA-component
 * wordt lui geladen, en een dashboard met alleen deze kaart erop haalt niets binnen
 * dat een menu meebrengt. Een `<ha-button-menu>` in ons template zou renderen als
 * een leeg inline-element — een onzichtbaar menu, zonder fout in de console.
 *
 * Dus: eigen menu, maar mét de plaatsing die een echte menu-component ook doet.
 *
 * ## Wat er mis was
 *
 * Het menu stond `position: absolute` in de rij, altijd 40 px onder de knop. Bij de
 * onderste rij stak het daarmee **onder de kaart uit**, over wat er op het dashboard
 * onder stond. Op een telefoon — waar de kaart smal is en de rijen dicht op elkaar —
 * was dat wat de eigenaar zag.
 *
 * ## De regel
 *
 * **Het menu blijft binnen de kaart.** Dat is het meetbare criterium: `top` niet
 * boven de bovenrand, `top + hoogte` niet onder de onderrand. Past het niet ónder de
 * knop, dan klapt het erboven — precies wat een echte menu-component doet.
 *
 * Past het in geen van beide richtingen binnen de kaart (een kaart met één rij is
 * lager dan het menu hoog is), dan wint het **venster**: liever een menu dat een
 * stukje over de kaartrand steekt dan een menu dat half buiten beeld valt en
 * onbereikbaar is.
 */

/** Ruimte tussen de knop en het menu, en tot de rand van het venster. */
export const MENU_MARGE = 4;

/**
 * Bereken de plek van het menu in viewport-coördinaten.
 *
 * Alles in CSS-pixels — dezelfde eenheid als `getBoundingClientRect`, en
 * uitdrukkelijk **niet** de schermafdrukcoördinaten waarin de browsertool klikt
 * (valkuil 43). De omrekening hoort bij het klikken, niet hier.
 *
 * @param {{top:number,bottom:number,right:number}} anker  de ⋮-knop
 * @param {{top:number,bottom:number}} kaart               de `ha-card`
 * @param {{breedte:number,hoogte:number}} menu            gemeten, niet geraden
 * @param {{breedte:number,hoogte:number}} venster
 * @returns {{left:number, top:number, richting:"onder"|"boven", binnenKaart:boolean}}
 */
export function plaatsMenu(anker, kaart, menu, venster) {
  const onder = anker.bottom + MENU_MARGE;
  const boven = anker.top - menu.hoogte - MENU_MARGE;

  const pastOnder = onder + menu.hoogte <= kaart.bottom;
  const pastBoven = boven >= kaart.top;

  let top;
  let richting;
  if (pastOnder) {
    top = onder;
    richting = "onder";
  } else if (pastBoven) {
    top = boven;
    richting = "boven";
  } else {
    // Past in geen van beide richtingen binnen de kaart. Dan telt alleen nog of het
    // menu bereikbaar blijft; het venster is de laatste grens.
    top = onder;
    richting = "onder";
  }

  const binnenKaart = pastOnder || pastBoven;

  // Het venster wint altijd van de kaart: een menu dat buiten beeld valt is niet
  // aan te klikken, en dat is erger dan een menu dat een randje overlapt.
  top = klem(top, MENU_MARGE, venster.hoogte - menu.hoogte - MENU_MARGE);

  // Rechts uitgelijnd op de knop, want daar staat hij: in het rechterdeel van de
  // rij. Links uitlijnen zou het menu over de schakelaar en de naam heen leggen.
  const left = klem(
    anker.right - menu.breedte,
    MENU_MARGE,
    venster.breedte - menu.breedte - MENU_MARGE,
  );

  return { left, top, richting, binnenKaart };
}

/**
 * `min` wint van `max`. Dat is geen slordigheid maar de keuze die hoort bij een
 * venster dat kleiner is dan het menu: dan is `max` kleiner dan `min` en levert de
 * gewone volgorde een negatieve `top` op — het menu begint dan buiten beeld. Zo
 * begint het op de marge en is de bovenkant in elk geval te zien.
 */
function klem(waarde, min, max) {
  return Math.max(min, Math.min(waarde, max));
}
