/* Kystloggen — visualiseringer som web components.
   <kyst-kart>      kart over kysten, ekte geometri (Natural Earth via world-atlas)
   <luse-graf>      ukesserie 2012–2026 der manglende rapport er tomrom
   <posisjons-kart> Leaflet-kart for én lokalitet
   Ingen build. d3 + topojson forventes lastet i <helmet>. */
(function () {
  if (window.__kystloggenViz) return;
  window.__kystloggenViz = true;

  var SEA = '#06161d', LAND = '#0f2b37', LANDLINE = '#2d5568';
  var PAPIR = '#e7dbd0', RUST = '#aa3e04';
  var FARGE = { 'grønn': '#2f6b4f', 'gul': '#c8992f', 'rød': '#93211c' };
  var TOM = '#4a6875';

  var PO = [
    { nr: 1,  navn: 'Svenskegrensen til Jæren',      farge: 'grønn',        n: 12 },
    { nr: 2,  navn: 'Ryfylke',                      farge: 'ikke oppgitt', n: 48 },
    { nr: 3,  navn: 'Karmøy til Sotra',              farge: 'rød',          n: 88 },
    { nr: 4,  navn: 'Nordhordland til Stadt',        farge: 'gul',          n: 141 },
    { nr: 5,  navn: 'Stadt til Hustadvika',          farge: 'gul',          n: 96 },
    { nr: 6,  navn: 'Nordmøre og Sør-Trøndelag',     farge: 'ikke oppgitt', n: 118 },
    { nr: 7,  navn: 'Nord-Trøndelag med Bindal',     farge: 'ikke oppgitt', n: 84 },
    { nr: 8,  navn: 'Helgeland til Bodø',            farge: 'ikke oppgitt', n: 132 },
    { nr: 9,  navn: 'Vestfjorden og Vesterålen',     farge: 'ikke oppgitt', n: 71 },
    { nr: 10, navn: 'Andøya til Senja',              farge: 'ikke oppgitt', n: 62 },
    { nr: 11, navn: 'Kvaløya til Loppa',             farge: 'ikke oppgitt', n: 58 },
    { nr: 12, navn: 'Vest-Finnmark',                 farge: 'grønn',        n: 32 },
    { nr: 13, navn: 'Øst-Finnmark',                  farge: 'grønn',        n: 27 }
  ];
  window.KYSTLOGGEN_PO = PO;
  window.KYSTLOGGEN_FARGE = FARGE;

  function fargeAv(f) { return FARGE[f] || TOM; }

  /* deterministisk tilfeldighet, så kartet ser likt ut hver gang */
  function rng(seed) {
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  var LEDD1 = ['Oter', 'Kval', 'Rev', 'Sjø', 'Stor', 'Lang', 'Nord', 'Sør', 'Ytre', 'Indre', 'Sand', 'Berg', 'Hav', 'Skog', 'Flat', 'Bratt', 'Gul', 'Svart', 'Hvit', 'Rød', 'Kald', 'Vind', 'Fugle', 'Sel', 'Laks', 'Sild', 'Torsk', 'Måke', 'Ørn', 'Tare', 'Grunn', 'Djup', 'Fjell', 'Stein', 'Ile', 'Fure', 'Hest', 'Geit', 'Ram', 'Skar'];
  var LEDD2 = ['neset', 'vika', 'øya', 'holmen', 'sundet', 'fjorden', 'skjæret', 'våg', 'berget', 'bukta', 'grunnen', 'odden', 'flua', 'straumen', 'hamna', 'leia', 'tangen', 'klubben', 'sanden', 'nakken'];

  function navnFor(r) {
    return (LEDD1[Math.floor(r() * LEDD1.length)] + LEDD2[Math.floor(r() * LEDD2.length)]).toUpperCase();
  }

  var ATLAS = 'https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json';
  var _data = null;

  function vent(test) {
    return new Promise(function (res) {
      (function p() { test() ? res() : setTimeout(p, 60); })();
    });
  }

  function lastData() {
    if (_data) return _data;
    _data = vent(function () { return window.d3 && window.topojson; })
      .then(function () { return fetch(ATLAS).then(function (r) { return r.json(); }); })
      .then(function (topo) {
        var alle = window.topojson.feature(topo, topo.objects.countries).features;
        var norge = alle.filter(function (f) { return f.properties.name === 'Norway'; })[0];
        var naboer = alle.filter(function (f) {
          return ['Sweden', 'Finland', 'Russia', 'Denmark', 'Estonia', 'Latvia'].indexOf(f.properties.name) >= 0;
        });
        return { norge: klippFastland(norge), naboer: naboer };
      });
    return _data;
  }

  function ringer(f) {
    var g = f.geometry, ut = [];
    var polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    polys.forEach(function (p) { p.forEach(function (r) { ut.push(r); }); });
    return ut;
  }

  /* Fastlands-Norge uten Svalbard og Jan Mayen, så projeksjonen kan ramme kysten inn */
  function klippFastland(norge) {
    var g = norge.geometry;
    var polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
    var beholdt = polys.filter(function (p) {
      var r = p[0], lat = 0, lon = 0;
      r.forEach(function (c) { lon += c[0]; lat += c[1]; });
      lat /= r.length; lon /= r.length;
      return lat < 72 && lat > 55 && lon > 3 && lon < 33;
    });
    return { type: 'Feature', properties: {}, geometry: { type: 'MultiPolygon', coordinates: beholdt } };
  }

  /* Kystlinjen hentes fra ekte geometri: for sørlige breddegrader er kysten
     det vestligste punktet i hvert breddebelte, i Finnmark det nordligste
     punktet i hvert lengdebelte. Lokalitetene legges sjøverts ut fra den. */
  function lagPunkter(norge) {
    var vest = {}, nord = {}, sor = {};
    ringer(norge).forEach(function (ring) {
      /* 1:110m har få punkter per ring — segmentene deles opp så kystlinjen
         får jevn punkttetthet før vi plukker ut de ytterste punktene */
      var tett = [];
      for (var i = 0; i < ring.length - 1; i++) {
        var a = ring[i], b = ring[i + 1];
        var n = Math.max(1, Math.ceil(Math.max(Math.abs(b[0] - a[0]) * 0.4, Math.abs(b[1] - a[1])) / 0.012));
        for (var t = 0; t < n; t++) {
          tett.push([a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n]);
        }
      }
      tett.forEach(function (c) {
        var lon = c[0], lat = c[1];
        if (lat < 57.6 || lat > 71.4 || lon < 4 || lon > 31.6) return;
        if (lat < 69.55) {
          var b = Math.round(lat / 0.03);
          if (!vest[b] || lon < vest[b][0]) vest[b] = [lon, lat];
        }
        if (lat > 69.2) {
          var l = Math.round(lon / 0.05);
          if (!nord[l] || lat > nord[l][1]) nord[l] = [lon, lat];
        }
        if (lat < 60.3 && lon > 4.6) {
          var m = Math.round(lon / 0.04);
          if (!sor[m] || lat < sor[m][1]) sor[m] = [lon, lat];
        }
      });
    });
    var kyst = Object.keys(vest).map(function (k) { return vest[k]; })
      .concat(Object.keys(nord).map(function (k) { return nord[k]; }))
      .concat(Object.keys(sor).map(function (k) { return sor[k]; }));

    function omraade(lon, lat) {
      if (lat >= 69.55) { if (lon < 21.9) return 11; if (lon < 26.4) return 12; return 13; }
      if (lat >= 69.0) return 10;
      if (lat >= 67.45) return 9;
      if (lat >= 65.25) return 8;
      if (lat >= 64.15) return 7;
      if (lat >= 62.95) return 6;
      if (lat >= 62.05) return 5;
      if (lat >= 60.55) return 4;
      if (lat >= 59.55) return 3;
      if (lat >= 58.95) return 2;
      return 1;
    }

    var perOmr = {};
    kyst.forEach(function (c) {
      var o = omraade(c[0], c[1]);
      (perOmr[o] = perOmr[o] || []).push(c);
    });

    var r = rng(31397), ut = [], id = 10000;
    PO.forEach(function (po) {
      var base = perOmr[po.nr] || [];
      if (!base.length) return;
      for (var i = 0; i < po.n; i++) {
        var c = base[Math.floor(r() * base.length)];
        var ut_ = 0.012 + r() * 0.16;
        var lon = c[0], lat = c[1];
        if (po.nr >= 11 && lat > 69.5) { lat += ut_ * 0.55; lon += (r() - 0.5) * 0.35; }
        else if (po.nr <= 2 && lat < 59.1) { lat -= ut_ * 0.5; lon += (r() - 0.5) * 0.3; }
        else { lon -= ut_ / Math.cos(lat * Math.PI / 180) * 0.9; lat += (r() - 0.5) * 0.09; }
        id += Math.floor(1 + r() * 37);
        ut.push({ lon: lon, lat: lat, po: po.nr, farge: po.farge, navn: navnFor(r), id: id });
      }
    });
    return ut;
  }

  /* ─────────────────────────── kyst-kart ───────────────────────────
     Produksjonsområdene som bånd langs kysten. Hvert område er en region i
     lon/lat; kystlinjen tegnes som et tykt strøk klippet til regionen, og land
     og naboland legges over, så bare havsiden av båndet synes. */
  var REGION = {
    1:  [[3,56],[14,56],[14,60.3],[7.2,60.3],[7.2,58.95],[3,58.95]],
    2:  [[5.55,58.95],[7.2,58.95],[7.2,59.75],[5.55,59.75]],
    3:  [[2,58.95],[5.55,58.95],[5.55,59.75],[7.2,59.75],[7.2,60.3],[14,60.3],[14,60.55],[2,60.55]],
    4:  [[2,60.55],[16,60.55],[16,62.15],[2,62.15]],
    5:  [[2,62.15],[16,62.15],[16,62.95],[2,62.95]],
    6:  [[2,62.95],[16,62.95],[16,64.15],[2,64.15]],
    7:  [[2,64.15],[18,64.15],[18,65.25],[2,65.25]],
    8:  [[2,65.25],[20,65.25],[20,67.35],[2,67.35]],
    9:  [[2,67.35],[22,67.35],[22,68.95],[2,68.95]],
    10: [[2,68.95],[19.3,68.95],[19.3,69.5],[2,69.5]],
    11: [[19.3,68.95],[21.9,68.95],[21.9,72],[2,72],[2,69.5],[19.3,69.5]],
    12: [[21.9,68.6],[26.4,68.6],[26.4,72],[21.9,72]],
    13: [[26.4,68.6],[33,68.6],[33,72],[26.4,72]]
  };
  /* anker på kysten + hvor etiketten står: 'v' = kolonne i vest, 'n' = rad i nord */
  var ANKER = {
    1: [5.62,58.72,'v'], 2: [5.95,59.2,'v'], 3: [5.05,59.95,'v'], 4: [4.95,61.3,'v'],
    5: [5.5,62.55,'v'], 6: [8.6,63.55,'v'], 7: [10.9,64.75,'v'], 8: [12.7,66.3,'v'],
    9: [13.6,68.15,'v'], 10: [16.6,69.25,'v'], 11: [19.6,70.05,'n'], 12: [24.2,71.0,'n'], 13: [28.8,70.9,'n']
  };

  function ring(c) { var r = c.slice(); r.push(c[0]); return r.reverse(); }

  class KystKart extends HTMLElement {
    static get observedAttributes() { return ['aktiv-po', 'lenke']; }
    connectedCallback() {
      if (this._i) return; this._i = true;
      this.style.cssText = 'position:absolute;inset:0;background:' + SEA;
      this.innerHTML = '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font:400 11px/1 "IBM Plex Sans",system-ui,sans-serif;color:#4e7182">Laster kystlinje …</div>';
      var self = this;
      lastData().then(function (d) { self._d = d; self.tegn(); }).catch(function (e) { console.error(e); });
      this._ro = new ResizeObserver(function () {
        clearTimeout(self._t); self._t = setTimeout(function () { self.tegn(); }, 120);
      });
      this._ro.observe(this);
    }
    disconnectedCallback() { this._ro && this._ro.disconnect(); }
    attributeChangedCallback() { this.marker(); }

    lenkeFor(nr) { return (this.getAttribute('lenke') || '#po-{nr}').replace('{nr}', nr); }

    tegn() {
      var d = this._d, d3 = window.d3, self = this;
      if (!d) return;
      var w = this.clientWidth, h = this.clientHeight;
      if (!w || !h) return;
      this.innerHTML = '';
      var utenEtik = this.getAttribute('etiketter') === 'nei';
      var venstre = utenEtik ? 24 : Math.min(150, w * 0.2);
      var proj = d3.geoMercator().fitExtent([[venstre, 64], [w - 16, h - 18]], d.norge);
      var path = d3.geoPath(proj);
      var NS = 'http://www.w3.org/2000/svg';

      var svg = d3.select(this).append('svg').attr('width', '100%').attr('height', '100%')
        .attr('viewBox', '0 0 ' + w + ' ' + h).style('display', 'block');
      var defs = svg.append('defs');
      defs.append('pattern').attr('id', 'kl-tom').attr('patternUnits', 'userSpaceOnUse')
        .attr('width', 5).attr('height', 5).attr('patternTransform', 'rotate(45)')
        .append('rect').attr('width', 1.3).attr('height', 5).attr('fill', '#6f8a95');

      var bred = Math.max(12, Math.min(22, w / 46));
      var omr = PO.map(function (po) {
        var reg = { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring(REGION[po.nr])] } };
        defs.append('clipPath').attr('id', 'kl-c' + po.nr).append('path').attr('d', path(reg));
        return { po: po, reg: reg };
      });

      var baand = svg.append('g');
      omr.forEach(function (o) {
        var f = o.po.farge, tom = f === 'ikke oppgitt';
        o.baand = baand.append('path').datum(d.norge).attr('d', path)
          .attr('clip-path', 'url(#kl-c' + o.po.nr + ')')
          .attr('fill', 'none').attr('stroke-linejoin', 'round')
          .attr('stroke', tom ? 'url(#kl-tom)' : fargeAv(f))
          .attr('stroke-width', bred * 2);
      });

      svg.append('g').selectAll('path').data(d.naboer).join('path')
        .attr('d', path).attr('fill', '#0b1f28').attr('stroke', '#17313d').attr('stroke-width', 0.5);

      var land = svg.append('g');
      omr.forEach(function (o) {
        o.land = land.append('path').datum(d.norge).attr('d', path)
          .attr('clip-path', 'url(#kl-c' + o.po.nr + ')')
          .attr('fill', LAND).attr('stroke', LANDLINE).attr('stroke-width', 0.7);
      });
      /* etiketter med ledelinjer */
      var etik = [];
      omr.forEach(function (o) {
        var an = ANKER[o.po.nr], p = proj([an[0], an[1]]);
        etik.push({ o: o, ax: p[0], ay: p[1], side: an[2] });
      });
      var vest = etik.filter(function (e) { return e.side === 'v'; }).sort(function (a, b) { return b.ay - a.ay; });
      var bunn = h - 36, min = Math.min(44, (bunn - 96) / 9);
      vest.forEach(function (e, i) {
        e.ly = Math.min(e.ay, i ? vest[i - 1].ly - min : bunn);
      });
      var top = vest[vest.length - 1].ly;
      if (top < 96) { var skift = Math.min(96 - top, bunn - vest[0].ly); vest.forEach(function (e) { e.ly += skift; }); }
      var nord = etik.filter(function (e) { return e.side === 'n'; }).sort(function (a, b) { return a.ax - b.ax; });
      nord.forEach(function (e, i) { e.lx = Math.max(e.ax - 20, i ? nord[i - 1].lx + 112 : venstre + 20); e.ly = 22; });
      for (var j = nord.length - 1; j >= 0; j--) { var maks = (j === nord.length - 1 ? w - 110 : nord[j + 1].lx - 112); if (nord[j].lx > maks) nord[j].lx = maks; }

      var ledere = svg.append('g').attr('fill', 'none').attr('pointer-events', 'none');
      etik.forEach(function (e) {
        var x1, y1;
        if (e.side === 'v') { x1 = 16 + 104; y1 = e.ly; e.leder = ledere.append('polyline').attr('points', [x1, y1, x1 + 14, y1, e.ax - bred * .6, e.ay].join(' ')); }
        else { x1 = e.lx; y1 = e.ly + 30; e.leder = ledere.append('polyline').attr('points', [x1, y1, x1, y1 + 8, e.ax, e.ay - bred * .6].join(' ')); }
        e.leder.attr('stroke', 'rgba(231,219,208,.28)').attr('stroke-width', 0.8);
        e.prikk = ledere.append('circle').attr('cx', e.side === 'v' ? e.ax - bred * .6 : e.ax).attr('cy', e.side === 'v' ? e.ay : e.ay - bred * .6).attr('r', 1.8).attr('fill', 'rgba(231,219,208,.5)');
      });

      var tip = document.createElement('div');
      tip.style.cssText = 'position:absolute;pointer-events:none;opacity:0;transition:opacity .15s;background:#e7dbd0;color:#0b2430;padding:9px 12px 10px;z-index:5;box-shadow:0 6px 24px rgba(0,0,0,.45);min-width:180px';
      this.appendChild(tip);

      etik.forEach(function (e) {
        var po = e.o.po, tom = po.farge === 'ikke oppgitt';
        var a = document.createElement('a');
        a.href = self.lenkeFor(po.nr);
        a.style.cssText = 'position:absolute;z-index:3;display:grid;grid-template-columns:auto 1fr;column-gap:8px;align-items:center;text-decoration:none;color:#e7dbd0;padding:5px 7px;width:104px;box-sizing:border-box;border-left:2px solid transparent';
        if (e.side === 'v') { a.style.left = '16px'; a.style.top = (e.ly - 17) + 'px'; }
        else { a.style.left = (e.lx - 8) + 'px'; a.style.top = (e.ly - 8) + 'px'; }
        var sw = tom ? '<span style="flex:none;width:9px;height:9px;border:1px solid #8a9aa1;box-sizing:border-box"></span>' : '<span style="flex:none;width:9px;height:9px;background:' + fargeAv(po.farge) + '"></span>';
        a.title = po.nr + ' ' + po.navn;
        a.innerHTML = '<span style="font:500 11px/1 \'IBM Plex Sans\',sans-serif;color:#7ba0b1;grid-row:span 2;align-self:start;padding-top:3px">' + (po.nr < 10 ? '0' : '') + po.nr + '</span>' +
          '<span style="font:400 19px/1 Newsreader,Georgia,serif;font-variant-numeric:tabular-nums">' + po.n + '<span style="font:400 10px/1 \'IBM Plex Sans\',sans-serif;color:#7ba0b1;margin-left:5px">lok.</span></span>' +
          '<span style="display:flex;align-items:center;gap:6px;margin-top:5px;font:400 10.5px/1 \'IBM Plex Sans\',sans-serif;color:#9fb9c4;white-space:nowrap">' + sw + po.farge + '</span>';
        self.appendChild(a);
        e.el = a;
      });

      function vis(nr, ev) {
        self._hover = nr; self.marker();
        if (!nr) { tip.style.opacity = 0; return; }
        var po = PO[nr - 1], tom = po.farge === 'ikke oppgitt';
        tip.innerHTML = '<div style="font:500 12.5px/1 \'IBM Plex Sans\',sans-serif;color:#aa3e04">Produksjonsområde ' + nr + '</div>' +
          '<div style="font:400 20px/1.15 Newsreader,Georgia,serif;margin:6px 0 7px">' + po.navn + '</div>' +
          '<div style="display:flex;align-items:center;gap:7px;font:400 12px/1 \'IBM Plex Sans\',sans-serif">' +
          (tom ? '<span style="width:10px;height:10px;border:1px solid rgba(11,36,48,.45)"></span>' : '<span style="width:10px;height:10px;background:' + fargeAv(po.farge) + '"></span>') +
          po.farge + ' · ' + po.n + ' lokaliteter <span style="opacity:.6">(plassholder)</span></div>' +
          '<div style="margin-top:8px;font:400 11px/1 \'IBM Plex Sans\',sans-serif;color:rgba(11,36,48,.6)">Klikk for områdesiden →</div>';
        if (ev) {
          var r = self.getBoundingClientRect();
          var x = ev.clientX - r.left + 18, y = ev.clientY - r.top + 18;
          if (x > w - 220) x -= 240;
          if (y > h - 110) y -= 120;
          tip.style.left = x + 'px'; tip.style.top = y + 'px';
        }
        tip.style.opacity = 1;
      }
      omr.forEach(function (o) {
        [o.baand, o.land].forEach(function (sel) {
          sel.style('cursor', 'pointer')
            .on('mousemove', function (ev) { vis(o.po.nr, ev); })
            .on('mouseleave', function () { vis(0); })
            .on('click', function () { location.href = self.lenkeFor(o.po.nr); });
        });
      });
      etik.forEach(function (e) {
        e.el.addEventListener('mouseenter', function () { self._hover = e.o.po.nr; self.marker(); });
        e.el.addEventListener('mouseleave', function () { self._hover = 0; self.marker(); });
      });
      if (utenEtik) { etik.forEach(function (e) { e.el.style.display = 'none'; e.leder.attr('display', 'none'); e.prikk.attr('display', 'none'); }); }
      this._omr = omr; this._etik = etik;
      this.marker();
    }

    marker() {
      if (!this._omr) return;
      var a = this._hover || parseInt(this.getAttribute('aktiv-po'), 10) || 0;
      this._omr.forEach(function (o) {
        var p = o.po.nr, på = !a || p === a;
        o.baand.attr('opacity', på ? 1 : 0.22);
        o.land.attr('fill', a && p === a ? '#1d4658' : LAND);
      });
      this._etik.forEach(function (e) {
        var p = e.o.po.nr, på = !a || p === a;
        e.el.style.opacity = på ? 1 : 0.4;
        e.el.style.borderLeftColor = a && p === a ? RUST : 'transparent';
        e.el.style.background = a && p === a ? 'rgba(231,219,208,.07)' : 'transparent';
        e.leder.attr('stroke', a && p === a ? RUST : 'rgba(231,219,208,.28)');
      });
    }
  }
  customElements.define('kyst-kart', KystKart);

  /* ─────────────────────────── luse-graf ─────────────────────────── */
  function luseserie() {
    var r = rng(20120401), ut = [], aar, uke;
    for (aar = 2012; aar <= 2026; aar++) {
      var maks = aar === 2026 ? 38 : 52;
      for (uke = 1; uke <= maks; uke++) {
        var brakk = (aar === 2014 && uke > 18 && uke < 44) || (aar === 2019 && uke > 30 && uke < 52) || (aar === 2023 && uke > 6 && uke < 22);
        var hull = brakk || r() < (uke < 9 || uke > 47 ? 0.42 : 0.06);
        if (hull) { ut.push({ aar: aar, uke: uke, v: null, brakk: brakk }); continue; }
        var sesong = 0.16 + 0.34 * Math.max(0, Math.sin((uke - 8) / 52 * Math.PI * 2)) + 0.26 * Math.max(0, Math.sin((uke - 30) / 26 * Math.PI));
        var trend = aar < 2016 ? 0.22 : aar < 2020 ? 0.08 : 0;
        var v = Math.max(0, sesong + trend + (r() - 0.5) * 0.34);
        ut.push({ aar: aar, uke: uke, v: Math.round(v * 100) / 100, brakk: false });
      }
    }
    return ut;
  }

  class LuseGraf extends HTMLElement {
    connectedCallback() {
      if (this._i) return; this._i = true;
      this.style.cssText = 'position:absolute;inset:0';
      this._serie = luseserie();
      this._ro = new ResizeObserver(this.tegn.bind(this));
      this._ro.observe(this);
      this.tegn();
    }
    disconnectedCallback() { this._ro && this._ro.disconnect(); }
    tegn() {
      var w = this.clientWidth, h = this.clientHeight;
      if (!w || !h) return;
      var s = this._serie, n = s.length;
      var pl = 40, pr = 12, pt = 14, pb = 26;
      var iw = w - pl - pr, ih = h - pt - pb;
      var maks = 1.3, bw = iw / n;
      var ink = '#0b2430';
      var svg = ['<svg width="100%" height="100%" viewBox="0 0 ' + w + ' ' + h + '" style="display:block">'];
      [0, 0.5, 1.0].forEach(function (v) {
        var y = pt + ih - v / maks * ih;
        var grense = v === 0.5;
        svg.push('<line x1="' + pl + '" x2="' + (w - pr) + '" y1="' + y + '" y2="' + y + '" stroke="' + (grense ? RUST : 'rgba(11,36,48,.18)') + '" stroke-width="' + (grense ? 1 : 0.6) + '"' + (grense ? ' stroke-dasharray="3 3"' : '') + '/>');
        svg.push('<text x="' + (pl - 8) + '" y="' + (y + 3.5) + '" text-anchor="end" font-family="IBM Plex Sans,system-ui,sans-serif" font-size="9.5" fill="' + (grense ? RUST : 'rgba(11,36,48,.5)') + '">' + v.toFixed(1) + '</text>');
      });
      s.forEach(function (d, i) {
        var x = pl + i * bw;
        if (d.v == null) {
          if (d.brakk) svg.push('<rect x="' + x + '" y="' + (pt + ih - 3) + '" width="' + Math.max(0.7, bw) + '" height="3" fill="rgba(11,36,48,.13)"/>');
          return;
        }
        var bh = Math.max(0.8, d.v / maks * ih);
        var over = d.v > 0.5;
        svg.push('<rect x="' + x + '" y="' + (pt + ih - bh) + '" width="' + Math.max(0.8, bw - 0.35) + '" height="' + bh + '" fill="' + (over ? RUST : '#2f5f74') + '" data-i="' + i + '"/>');
      });
      for (var a = 2012; a <= 2026; a++) {
        var idx = s.findIndex(function (d) { return d.aar === a && d.uke === 1; });
        if (idx < 0) continue;
        var x = pl + idx * bw;
        svg.push('<line x1="' + x + '" x2="' + x + '" y1="' + (pt + ih) + '" y2="' + (pt + ih + 4) + '" stroke="rgba(11,36,48,.35)" stroke-width="0.7"/>');
        svg.push('<text x="' + (x + 3) + '" y="' + (h - 8) + '" font-family="IBM Plex Sans,system-ui,sans-serif" font-size="9.5" fill="rgba(11,36,48,.55)">' + (a % 100 < 10 ? '0' : '') + (a % 100) + '</text>');
      }
      svg.push('<rect x="' + pl + '" y="' + pt + '" width="' + iw + '" height="' + ih + '" fill="transparent" data-flate="1"/>');
      svg.push('</svg>');
      this.innerHTML = svg.join('');

      var les = document.createElement('div');
      les.style.cssText = 'position:absolute;top:0;right:12px;font:500 12px/1.3 "IBM Plex Sans",system-ui,sans-serif;color:' + ink + ';opacity:0;pointer-events:none;text-align:right';
      this.appendChild(les);
      var lin = document.createElement('div');
      lin.style.cssText = 'position:absolute;top:' + pt + 'px;height:' + ih + 'px;width:1px;background:rgba(11,36,48,.45);opacity:0;pointer-events:none';
      this.appendChild(lin);
      var self = this;
      this.onmousemove = function (e) {
        var r = self.getBoundingClientRect();
        var i = Math.floor((e.clientX - r.left - pl) / bw);
        if (i < 0 || i >= n) { les.style.opacity = 0; lin.style.opacity = 0; return; }
        var d = s[i];
        lin.style.left = (pl + i * bw) + 'px'; lin.style.opacity = 1;
        les.style.opacity = 1;
        les.innerHTML = '<span style="opacity:.6">Uke ' + d.uke + ', ' + d.aar + '</span>  ' +
          (d.v == null ? '<span style="color:' + RUST + '">' + (d.brakk ? 'brakklagt' : 'ingen rapport') + '</span>' : '<b>' + d.v.toFixed(2) + '</b> hunnlus');
      };
      this.onmouseleave = function () { les.style.opacity = 0; lin.style.opacity = 0; };
    }
  }
  customElements.define('luse-graf', LuseGraf);

  /* ────────────────────── posisjons-kart (Leaflet) ────────────────────── */
  class PosisjonsKart extends HTMLElement {
    connectedCallback() {
      if (this._i) return; this._i = true;
      this.style.cssText = 'position:absolute;inset:0;background:' + SEA;
      var self = this;
      var lat = parseFloat(this.getAttribute('lat')) || 60.9741;
      var lon = parseFloat(this.getAttribute('lon')) || 5.0338;
      vent(function () { return window.L && self.clientHeight; }).then(function () {
        var d = document.createElement('div');
        d.style.cssText = 'position:absolute;inset:0';
        self.appendChild(d);
        var map = window.L.map(d, { zoomControl: false, attributionControl: false, scrollWheelZoom: false }).setView([lat, lon], 11);
        window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 17 }).addTo(map);
        map.getPane('tilePane').style.filter = 'grayscale(1) invert(1) brightness(.78) contrast(1.15) hue-rotate(178deg) saturate(.55)';
        window.L.control.zoom({ position: 'bottomright' }).addTo(map);
        var ikon = window.L.divIcon({
          className: '', iconSize: [30, 30], iconAnchor: [15, 15],
          html: '<div style="width:30px;height:30px;position:relative">' +
            '<div style="position:absolute;left:14px;top:0;width:2px;height:30px;background:' + RUST + '"></div>' +
            '<div style="position:absolute;top:14px;left:0;height:2px;width:30px;background:' + RUST + '"></div>' +
            '<div style="position:absolute;left:9px;top:9px;width:12px;height:12px;border:2px solid ' + RUST + '"></div></div>'
        });
        window.L.marker([lat, lon], { icon: ikon }).addTo(map);
        var att = document.createElement('div');
        att.style.cssText = 'position:absolute;left:0;bottom:0;z-index:500;font:400 9px/1 "IBM Plex Sans",system-ui,sans-serif;color:#7d9dab;background:rgba(6,22,29,.8);padding:5px 7px';
        att.textContent = '© OpenStreetMap contributors';
        self.appendChild(att);
        setTimeout(function () { map.invalidateSize(); }, 120);
      });
    }
  }
  customElements.define('posisjons-kart', PosisjonsKart);
})();
