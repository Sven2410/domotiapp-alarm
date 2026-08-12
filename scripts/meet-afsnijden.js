// MEETFUNCTIE — valt er iets buiten de kaart, of buiten de pop-up?
//
// Fase 8 stelde vast dat `scrollWidth > clientWidth` maar de helft van het
// afsnijden vindt (valkuil 63): het meet alleen overloop naar RECHTS, dus een rij
// met `justify-content: flex-end` spilt naar links zonder dat er iets te melden
// valt, en een veld dat wordt PLATGEKNEPEN heeft niets om over te lopen.
//
// Deze functie doet daarom het enige dat beide vindt: per element de
// `getBoundingClientRect` vergelijken met een referentierechthoek, aan BEIDE
// kanten, over ALLE elementen — ook die in shadow roots.
//
// Fase 9 voegt de tweede referentie toe. Een kaart in een Bubble Card-pop-up kan
// binnen zijn eigen grenzen passen en tóch buiten de pop-up vallen; dat is een
// ander gebrek met een andere oorzaak, dus het wordt apart geteld.
//
// Gebruik (vanuit het venster waarin HA draait, of vanuit de rig met `win`):
//     const m = await import('/local/meet-afsnijden.js');
//     m.meet(window)                       // kaart t.o.v. zichzelf
//     m.meet(frame.contentWindow)          // vanuit de telefoonrig
//
// Installeren op de dev-instance:
//     copy scripts\meet-afsnijden.js .ha-dev-config\www\meet-afsnijden.js

const TOLERANTIE = 0.5; // subpixel; alles daaronder is afronding, geen afsnijding

/** Alle elementen onder `root`, shadow roots inbegrepen. */
export function alleElementen(root, uit = []) {
  const loop = (n) => {
    if (!n || n.nodeType !== 1) return;
    uit.push(n);
    if (n.shadowRoot) for (const k of n.shadowRoot.children) loop(k);
    for (const k of n.children) loop(k);
  };
  loop(root);
  return uit;
}

function beschrijf(el) {
  const klasse = typeof el.className === "string" && el.className
    ? "." + el.className.trim().split(/\s+/)[0]
    : "";
  const tekst = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24);
  return el.tagName.toLowerCase() + klasse + (tekst ? ` "${tekst}"` : "");
}

/**
 * @param {Window} win  het venster waarin HA draait
 * @returns {{kaart, popup, onderzocht, buitenKaart, buitenPopup, tekstLooptUit, teBreed, geknepen}}
 */
export function meet(win) {
  const d = win.document;
  const kaart = alleElementen(d.body)
    .find((e) => e.tagName.toLowerCase() === "domotiapp-alarm-card");
  if (!kaart) throw new Error("geen domotiapp-alarm-card gevonden");

  const popup = alleElementen(d.body).find(
    (e) => typeof e.className === "string" && e.className.includes("bubble-pop-up ")
  ) || null;

  const kr = kaart.getBoundingClientRect();
  const pr = popup ? popup.getBoundingClientRect() : null;

  const elementen = alleElementen(kaart).filter((e) => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  });

  const buiten = (r, ref) => {
    const links = ref.left - r.left;
    const rechts = r.right - ref.right;
    return { links: links > TOLERANTIE ? Math.round(links) : 0,
             rechts: rechts > TOLERANTIE ? Math.round(rechts) : 0 };
  };

  const buitenKaart = [];
  const buitenPopup = [];
  for (const e of elementen) {
    const r = e.getBoundingClientRect();
    const bk = buiten(r, kr);
    if (bk.links || bk.rechts) buitenKaart.push({ el: beschrijf(e), ...bk, breedte: Math.round(r.width) });
    if (pr) {
      const bp = buiten(r, pr);
      if (bp.links || bp.rechts) buitenPopup.push({ el: beschrijf(e), ...bp, breedte: Math.round(r.width) });
    }
  }

  // TEKST die uit zijn EIGEN element loopt. De rechthoekvergelijking hierboven
  // ziet dit NIET: bij een tekst die niet kan afbreken blijft het element zelf
  // netjes op zijn plek en steekt alleen de tekst eruit — de rect is ongewijzigd.
  //
  // Gemeten in fase 9, bij een wekker met een naam van 46 tekens in één woord op
  // een kaart van 208 px: `clientWidth 174, scrollWidth 284`, dus 110 px tekst
  // buiten het element en ver buiten de kaart, terwijl `buitenKaart` leeg bleef.
  //
  // Dit is valkuil 63 in spiegelbeeld. Daar was `scrollWidth` het gereedschap dat
  // te weinig vond en de rectvergelijking het antwoord; hier is het andersom. Ze
  // vinden elk iets dat de ander niet ziet, dus ze staan er allebei.
  //
  // Alleen wanneer de tekst er ook werkelijk UIT kan. Een element met
  // `overflow-x: hidden` en een ellips kapt met opzet af — dat is een keuze, geen
  // gebrek, en `.naam` in de wekkerlijst doet het bewust. Zonder deze filter
  // meldde de eerste versie er in fase 9 dertien op een rij, allemaal terecht
  // afgekapt, en dan is de lijst niets meer waard.
  // De maat is NIET "loopt de tekst uit zijn eigen element" — dat doet in een
  // flexindeling van alles een paar pixels, en zo'n lijst leest niemand meer. De
  // maat is waar de tekst UITKOMT: valt het einde ervan buiten de KAART, dan is
  // het afgesneden, en anders niet.
  const tekstLooptUit = elementen
    .filter((e) => e.scrollWidth > e.clientWidth + TOLERANTIE)
    .filter((e) => win.getComputedStyle(e).overflowX === "visible")
    .map((e) => {
      const r = e.getBoundingClientRect();
      return { el: beschrijf(e), client: e.clientWidth, scroll: e.scrollWidth,
               eindigtOp: Math.round(r.left + e.scrollWidth),
               voorbijKaart: Math.round(r.left + e.scrollWidth - kr.right) };
    })
    .filter((x) => x.voorbijKaart > TOLERANTIE);

  // TE BREED GETEKEND — de getekende breedte tegen de beschikbare breedte, per
  // element, in plaats van de POSITIE tegen de kaart.
  //
  // Waarom dit er los naast staat. De drie controles hierboven kijken allemaal
  // naar waar iets UITKOMT, en dat betekent dat ze het pas zien als het aan de
  // buitenkant zichtbaar wordt. Een element dat 26 px te breed is maar binnen een
  // ouder met ruimte staat, valt nergens buiten en blijft dus onzichtbaar — tot
  // een andere engine er nét iets anders mee omgaat.
  //
  // Fase 10 kwam hierop uit doordat iOS `box-sizing: border-box` NIET toepast op
  // `input[type="time"]`: `width: 100%` gold daar voor de contentbox, en onze
  // padding en rand kwamen er bovenop. Gemeten op de telefoon van de eigenaar:
  // 324 px beschikbaar, 348,9 px getekend. Op Chrome was datzelfde veld 324 px en
  // viel er niets te vinden — de fout is per engine anders, de OORZAAK niet.
  //
  // Deze controle meet de oorzaak: past de borderbox van het kind in de contentbox
  // van zijn ouder? Zo nee, dan is het element te breed getekend, ongeacht welke
  // engine het uiteindelijk waar afknipt.
  const teBreed = [];
  for (const e of elementen) {
    const ouder = e.parentElement || (e.getRootNode() && e.getRootNode().host);
    if (!ouder || ouder === kaart) continue;
    const st = win.getComputedStyle(e);
    // Absoluut/vast gepositioneerde kinderen en negatieve marges mogen breder
    // zijn dan hun ouder; dat is een keuze en geen fout.
    if (st.position === "absolute" || st.position === "fixed") continue;
    if (parseFloat(st.marginLeft) < 0 || parseFloat(st.marginRight) < 0) continue;
    const os = win.getComputedStyle(ouder);
    const beschikbaar =
      ouder.clientWidth - parseFloat(os.paddingLeft) - parseFloat(os.paddingRight);
    const getekend = e.getBoundingClientRect().width;
    if (beschikbaar > 0 && getekend > beschikbaar + TOLERANTIE) {
      teBreed.push({
        el: beschrijf(e),
        getekend: Math.round(getekend * 10) / 10,
        beschikbaar: Math.round(beschikbaar * 10) / 10,
        teveel: Math.round((getekend - beschikbaar) * 10) / 10,
        boxSizing: st.boxSizing,
        breedteRegel: st.width,
      });
    }
  }

  // Platgeknepen invoervelden: die lopen nergens over, dus ze staan in geen van
  // beide lijsten. Fase 8 vond zo een zoekveld van 27 px.
  const geknepen = elementen
    .filter((e) => ["input", "select", "textarea"].includes(e.tagName.toLowerCase()))
    .map((e) => ({ el: beschrijf(e), breedte: Math.round(e.getBoundingClientRect().width) }))
    .filter((x) => x.breedte < 60);

  return {
    kaart: { l: Math.round(kr.left), r: Math.round(kr.right), w: Math.round(kr.width) },
    popup: pr ? { l: Math.round(pr.left), r: Math.round(pr.right), w: Math.round(pr.width) } : null,
    onderzocht: elementen.length,
    buitenKaart,
    buitenPopup,
    tekstLooptUit,
    teBreed,
    geknepen,
  };
}
