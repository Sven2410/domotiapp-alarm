/**
 * De tekst van de verwijderbevestiging (SPEC 3.2). Puur.
 *
 * ## Waarom hier geen `ha-dialog` staat, en dat is gemeten en niet aangenomen
 *
 * De opdracht van fase 7 was: gebruik HA's eigen dialoogcomponent als die er is.
 * Dat is in twee stappen nagegaan, en de tweede stap is de interessante.
 *
 * **Stap 1 — bestaat hij?** Ja. Gemeten op HA 2026.8.1, verse pagina, zonder een
 * enkele klik en nog eens vijf seconden later: `ha-dialog`, `ha-alert`,
 * `ha-button` en `ha-icon-button` zijn gedefinieerd op een gewoon dashboard
 * (`ha-md-dialog` niet). Dat is een ander antwoord dan fase 6b voor de
 * menu-componenten kreeg.
 *
 * **Stap 2 — werkt hij?** Nee, niet met de aanroep die je uit de HA-broncode van
 * een jaar geleden zou overschrijven. Een `ha-dialog` met
 * `slot="primaryAction"` en `slot="secondaryAction"` — de mwc-namen — leverde een
 * dialoog op met onze tekst en een kruisje, en **zonder knoppen**: de twee
 * `ha-button`s waren gedefinieerd, hadden een shadow root, en maten `0 × 0`.
 *
 * De oorzaak, uit de shadow root van `ha-dialog` zelf:
 *
 * ```
 * shadow: [wa-dialog]
 * slots:  header, headerNavigationIcon, headerTitle, headerSubtitle,
 *         headerActionItems, (default), footer
 * mwc-button gedefinieerd: false
 * ```
 *
 * `ha-dialog` is in 2026.8 van mwc naar Web Awesome gegaan. `primaryAction` en
 * `secondaryAction` **bestaan niet meer**; wat er is heet `footer`. Onze knoppen
 * landden daardoor in de default-slot, waar de dialoog ze geen plaatsing geeft.
 *
 * ## De keuze
 *
 * De bevestiging is een **regel binnen de kaart**, altijd. Geen dialoog.
 *
 * Dat is een afwijking van de opdracht en hij staat als aanname in het rapport.
 * De reden staat hierboven: de sloten van `ha-dialog` zijn een contract dat net
 * onder onze voeten is veranderd, het faalgeval is **stil** (een dialoog met een
 * onbeantwoordbare vraag erin), en er is geen unittest die het vangt — jsdom is
 * hier verboden, dus de enige bewaker zou een browsermeting per HA-versie zijn.
 *
 * Voor een bevestiging op een **onomkeerbare** handeling weegt "aantoonbaar
 * bedienbaar" zwaarder dan "mooiere chroom". De regel in de kaart is van onszelf,
 * overlapt niets, en staat er sinds fase 4a — hij was de terugval en is nu het
 * hele antwoord.
 */

/**
 * De vraag die de klant te zien krijgt (SPEC 3.2).
 *
 * **Naam én tijd**, want een lijst met vier wekkers heeft er zo twee van "Werk".
 * Alleen de naam maakt de vraag onbeantwoordbaar op precies het moment dat hij
 * onomkeerbaar wordt.
 *
 * Een wekker zonder naam is geen reden om de vraag niet te stellen: dan staat er
 * alleen een tijd. Een verzonnen naam zou erger zijn — die verwijst naar een
 * wekker die de klant niet herkent.
 */
export function bevestigingsTekst(wekker) {
  const naam = typeof wekker?.name === "string" ? wekker.name.trim() : "";
  const tijd = typeof wekker?.time === "string" ? wekker.time.trim() : "";
  if (naam && tijd) {
    return `Wil je de wekker "${naam}" van ${tijd} verwijderen?`;
  }
  if (naam) {
    return `Wil je de wekker "${naam}" verwijderen?`;
  }
  if (tijd) {
    return `Wil je de wekker van ${tijd} verwijderen?`;
  }
  return "Wil je deze wekker verwijderen?";
}
