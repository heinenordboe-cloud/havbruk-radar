/* Søket. Lastes BARE av /sok/, og bare der.
 *
 * ## Hvorfor dette ikke er i kystloggen.js
 *
 * Fordi det henter Pagefinds egen modul og en WebAssembly-fil på til
 * sammen ~1 MB, og det skal ikke skje på 2 336 sider der ingen søker.
 * `kystloggen.js` er 5 kB og lastes overalt; dette lastes ett sted.
 *
 * ## Hvorfor søket i det hele tatt er JavaScript
 *
 * Nettstedets regel er at TALLENE skal stå i kildekoden. Et
 * søkeresultat er ikke et tall fra et register — det er en vei til
 * siden der tallet står, og den siden er statisk HTML som kan siteres,
 * arkiveres og leses uten skript.
 *
 * Et søk over 2 337 sider som skal svare uten en server, må kjøre i
 * nettleseren. Alternativet er ingen søk, og /sok/ har derfor en
 * veiviser til de tre flate indeksene som ALLTID står der — også når
 * dette skriptet aldri lastes.
 *
 * ## Ingen bygging, ingen pakkebrønn
 *
 * Pagefind-indeksen bygges av en binær ved bygging, og modulen som
 * lastes her er den Pagefind selv la i `/pagefind/`. Ingen npm, ingen
 * bundler — se `nettsted.skriv_sokeindeks()`.
 */
(function () {
  "use strict";

  var felt = document.getElementById("q");
  var ut = document.getElementById("sokeresultat");
  if (!felt || !ut) return;

  var TAK = 30;           /* treff som vises */
  var pagefind = null;    /* lastes ved første søk, ikke ved sidelast */
  var siste = "";

  function tekst(el, s) { el.textContent = s; }

  function melding(s) {
    ut.innerHTML = "";
    var p = document.createElement("p");
    p.className = "sok-melding";
    tekst(p, s);
    ut.appendChild(p);
  }

  /* MODULEN LASTES VED FØRSTE TASTETRYKK, ikke når siden åpnes. Den er
     ~1 MB med wasm, og en som kom hit ved et uhell skal ikke betale
     for den. */
  function last() {
    if (pagefind) return Promise.resolve(pagefind);
    return import("/pagefind/pagefind.js").then(function (modul) {
      pagefind = modul;
      return modul.init().then(function () { return modul; });
    });
  }

  function vis(treff, q) {
    ut.innerHTML = "";
    var hode = document.createElement("p");
    hode.className = "sok-melding";
    tekst(hode, treff.length
      ? "Viser " + Math.min(treff.length, TAK) + " av " + treff.length
        + " treff på «" + q + "»."
      : "Ingen treff på «" + q + "». Prøv et lokalitetsnummer, et "
        + "kommunenavn eller et selskapsnavn — eller bla i de flate "
        + "listene under.");
    ut.appendChild(hode);
    if (!treff.length) return;

    var liste = document.createElement("ol");
    liste.className = "sokeliste";
    ut.appendChild(liste);

    Promise.all(treff.slice(0, TAK).map(function (t) { return t.data(); }))
      .then(function (data) {
        data.forEach(function (d) {
          var li = document.createElement("li");
          var a = document.createElement("a");
          a.href = d.url;
          /* TITTELEN ER SIDENS EGEN `<title>`, uten «— Kystloggen»:
             hver rad i en trefflista som ender på det samme, sier
             ingenting med de siste tolv tegnene. */
          tekst(a, (d.meta && d.meta.title
                    ? d.meta.title : d.url).replace(/ — Kystloggen$/, ""));
          li.appendChild(a);
          var p = document.createElement("p");
          /* `excerpt` er HTML fra Pagefind, med `<mark>` rundt
             treffet. Den settes som innerHTML fordi merkingen er hele
             poenget — og den er bygget av VÅR egen statiske HTML ved
             bygging, ikke av noe en bruker har skrevet. */
          p.className = "sok-utdrag";
          p.innerHTML = d.excerpt;
          li.appendChild(p);
          var u = document.createElement("p");
          u.className = "sok-url";
          tekst(u, d.url);
          li.appendChild(u);
          liste.appendChild(li);
        });
      });
  }

  function sok() {
    var q = felt.value.trim();
    if (q === siste) return;
    siste = q;
    if (q.length < 2) { ut.innerHTML = ""; return; }
    melding("Søker …");
    last()
      .then(function (m) { return m.search(q); })
      .then(function (r) { if (felt.value.trim() === q) vis(r.results, q); })
      .catch(function () {
        melding("Søkeindeksen kunne ikke lastes. Listene under virker "
                + "uansett.");
      });
  }

  var vent = null;
  felt.addEventListener("input", function () {
    clearTimeout(vent);
    vent = setTimeout(sok, 150);
  });
  felt.closest("form").addEventListener("submit", function (e) {
    e.preventDefault();
    clearTimeout(vent);
    sok();
  });

  /* `?q=` I ADRESSEN. Skjemaet er en `GET`, så en som trykker enter
     uten JavaScript havner på `/sok/?q=oterneset`. Da skal søket
     kjøre av seg selv når skriptet finnes — ellers ville lenka gitt et
     tomt felt.

     Dette er den ENE spørrestrengen på nettstedet, og den bærer ikke
     innhold: den bærer et søkeord, og /sok/ har ingen identitet å
     forveksle den med. Se 2026-09-16-url-struktur.md punkt 3. */
  var fra = new URLSearchParams(window.location.search).get("q");
  if (fra) { felt.value = fra; sok(); }
})();
