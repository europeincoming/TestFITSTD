/* Europe Incoming — data-driven package page
   Reads window.PRODUCT + window.PRICES (injected inline per page by rebuild_site.py)
   and renders the whole page client-side. Shared unchanged across every product. */
(function () {
  "use strict";

  var PRODUCT = window.PRODUCT || {};
  var PRICES_BY_YEAR = window.PRICES_BY_YEAR || {};
  var yearKeys = Object.keys(PRICES_BY_YEAR);
  var defaultYear = PRICES_BY_YEAR[window.DEFAULT_RATE_YEAR] ? window.DEFAULT_RATE_YEAR : yearKeys[0];
  var PRICES = PRICES_BY_YEAR[defaultYear] || {};

  var SEASON_LABEL = { summer: "Apr–Oct", winter: "Nov–Mar" };
  var CAT_LABEL = { "3": "3★", "4": "4★" };
  var CARTO_API_KEY = window.CARTO_API_KEY || "";

  var styleKeys = Object.keys(PRODUCT.styles || {});

  var state = {
    style: styleKeys[0],
    year: defaultYear,
    cat: "3",
    season: "summer",
    tcOpen: false,
    mapOpen: false
  };

  var smallMap = null;
  var largeMap = null;

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmtMoney(v) {
    if (v == null) return "—";
    var curr = PRICES.currency || "€";
    return curr + Number(v).toLocaleString("en-GB");
  }
  function row(tagClass, label, text) {
    return '<div class="pkg-pill-row"><span class="pkg-tag ' + tagClass + '">' + label + '</span>' +
      '<span class="pkg-tag-text">' + esc(text) + '</span></div>';
  }

  // ── cheapest twin rate within a style, across every hotel category + season ──
  function cheapestTwin(styleId) {
    var variant = (PRICES.variants || {})[styleId];
    if (!variant) return null;
    var best = null;
    if (variant.paxTiers) {
      Object.keys(variant.paxTiers).forEach(function (season) {
        (variant.paxTiers[season] || []).forEach(function (tier) {
          if (tier["3star"] != null && (best === null || tier["3star"] < best)) best = tier["3star"];
        });
      });
      return best;
    }
    Object.keys(variant).forEach(function (cat) {
      Object.keys(variant[cat] || {}).forEach(function (season) {
        var row = variant[cat][season];
        if (row && row.twin != null && (best === null || row.twin < best)) best = row.twin;
      });
    });
    return best;
  }

  // ───────────────────────────── HERO ─────────────────────────────
  function renderHero() {
    var style = PRODUCT.styles[state.style] || {};
    $("pkgEyebrow").textContent = PRODUCT.eyebrow || "";
    $("pkgHeroTitle").textContent = PRODUCT.title || "";
    $("pkgHeroImg").style.backgroundImage = PRODUCT.heroImage ? "url('" + PRODUCT.heroImage + "')" : "none";
    $("pkgHeroNights").textContent = style.nights || "";
    $("pkgHeroRoute").textContent = style.route || "";
    var from = cheapestTwin(state.style);
    $("pkgHeroPrice").textContent = from != null ? fmtMoney(from) : "…";
  }

  // ─────────────────────────── VARIANT BAR ────────────────────────
  function renderVariantBar() {
    var bar = $("pkgVariantPills");
    bar.innerHTML = "";
    styleKeys.forEach(function (key) {
      var s = PRODUCT.styles[key];
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pkg-pill" + (key === state.style ? " active" : "");
      btn.textContent = s.name;
      btn.addEventListener("click", function () {
        if (state.style === key) return;
        state.style = key;
        renderAll();
      });
      bar.appendChild(btn);
    });
    $("pkgVariantBlurb").textContent = (PRODUCT.styles[state.style] || {}).blurb || "";
  }

  // ───────────────────────────── RATE YEAR TOGGLE ──────────────────
  // Lives next to the rates table (not the top travel-style bar) since it
  // only affects which price data is shown.
  function renderYearBar() {
    var bar = $("pkgYearToggle");
    if (!bar) return;
    bar.innerHTML = "";
    bar.parentElement.style.display = yearKeys.length > 1 ? "" : "none";
    yearKeys.forEach(function (year) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pkg-seg" + (year === state.year ? " active" : "");
      btn.textContent = year;
      btn.addEventListener("click", function () {
        if (state.year === year) return;
        state.year = year;
        PRICES = PRICES_BY_YEAR[state.year] || {};
        renderAll();
      });
      bar.appendChild(btn);
    });
  }

  // ─────────────────────────── DAY BY DAY ─────────────────────────
  function renderDays() {
    var style = PRODUCT.styles[state.style] || {};
    var transport = style.transport || {};
    $("pkgDaySub").textContent = style.name || "";
    var wrap = $("pkgDays");
    wrap.innerHTML = "";
    (PRODUCT.days || []).forEach(function (day) {
      var el = document.createElement("div");
      el.className = "pkg-day";
      var included = transport[String(day.num)] || day.fallbackIncluded || "Day at leisure.";
      var rows = row("pkg-tag-inc", "INCLUDED", included);
      if (day.taste) rows += row("pkg-tag-taste", "LOCAL TASTE", day.taste);
      if (day.experience) rows += row("pkg-tag-exp", "LOCAL EXPERIENCE", day.experience);
      if (day.shopping) rows += row("pkg-tag-shop", "SHOPPING", day.shopping);
      el.innerHTML =
        '<div class="pkg-day-num-col"><div class="pkg-day-num-lbl">Day</div><div class="pkg-day-num">' + day.num + '</div></div>' +
        '<div class="pkg-day-body">' +
          '<div class="pkg-day-title">' + esc(day.title) + '</div>' +
          '<div class="pkg-day-overnight">' + esc(day.overnight || "") + '</div>' +
          '<div class="pkg-day-desc">' + esc(day.desc || "") + '</div>' +
          rows +
        '</div>';
      wrap.appendChild(el);
    });
  }

  // ─────────────────────────── INCLUSIONS ─────────────────────────
  function renderIncludes() {
    var style = PRODUCT.styles[state.style] || {};
    $("pkgIncludesSub").textContent = style.name || "";
    var wrap = $("pkgIncludes");
    wrap.innerHTML = "";
    (style.inclusions || []).forEach(function (item) {
      var el = document.createElement("div");
      el.className = "pkg-inc-item";
      el.innerHTML = '<span class="pkg-check">✓</span>' + esc(item);
      wrap.appendChild(el);
    });
  }

  // ─────────────────────────────── HOTELS ──────────────────────────
  function renderHotels() {
    var wrap = $("pkgHotels");
    wrap.innerHTML = "";
    (PRODUCT.hotels || []).forEach(function (h) {
      var el = document.createElement("div");
      el.className = "pkg-hotel-card";
      el.innerHTML =
        '<div class="pkg-hotel-city">' + esc(h.city) + '</div>' +
        '<div class="pkg-hotel-nights">' + esc(h.nights) + '</div>' +
        '<div class="pkg-hotel-cat">3 STAR</div><div class="pkg-hotel-name">' + esc(h.h3 || "—") + '</div>' +
        '<div class="pkg-hotel-cat">4 STAR</div><div class="pkg-hotel-name">' + esc(h.h4 || "—") + '</div>';
      wrap.appendChild(el);
    });
  }

  // ─────────────────────────────── RATES ───────────────────────────
  function availableSeasons(variant) {
    var seasons = {};
    ["3", "4"].forEach(function (cat) {
      Object.keys(variant[cat] || {}).forEach(function (s) { seasons[s] = true; });
    });
    return Object.keys(seasons);
  }

  function renderRateToggles(seasons) {
    var catWrap = $("pkgCatToggle");
    catWrap.innerHTML = "";
    ["3", "4"].forEach(function (cat) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pkg-seg" + (state.cat === cat ? " active" : "");
      btn.textContent = CAT_LABEL[cat];
      btn.addEventListener("click", function () { state.cat = cat; renderRates(); });
      catWrap.appendChild(btn);
    });
    var seasonWrap = $("pkgSeasonToggle");
    seasonWrap.innerHTML = "";
    seasonWrap.style.display = seasons.length > 1 ? "" : "none";
    if (seasons.length > 1) {
      ["summer", "winter"].forEach(function (season) {
        if (seasons.indexOf(season) === -1) return;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "pkg-seg" + (state.season === season ? " active" : "");
        btn.textContent = SEASON_LABEL[season];
        btn.addEventListener("click", function () { state.season = season; renderRates(); });
        seasonWrap.appendChild(btn);
      });
    }
  }

  function renderPaxTable(tiers) {
    var body = (tiers || []).map(function (t) {
      return "<tr><td>" + t.pax + "</td><td>" + fmtMoney(t["3star"]) + "</td><td>" + fmtMoney(t["4star"]) + "</td></tr>";
    }).join("");
    return '<table class="pkg-pax-table"><thead><tr><th>Min Pax</th><th>3★ per adult</th><th>4★ per adult</th></tr></thead><tbody>' + body + '</tbody></table>';
  }

  function renderRates() {
    var styleName = (PRODUCT.styles[state.style] || {}).name || "";
    $("pkgRateSub").textContent = "Per person · " + styleName + " · Valid " +
      (PRICES.validFrom || "") + " – " + (PRICES.validTo || "");
    var variant = (PRICES.variants || {})[state.style] || {};
    var isPax = !!variant.paxTiers;
    $("pkgRateToggles").style.display = isPax ? "none" : "";
    $("pkgPaxRates").style.display = isPax ? "" : "none";
    $("pkgRateTable").style.display = isPax ? "none" : "";
    $("pkgRateNote").textContent = "All rates net, per person, in " + (PRICES.currency || "€") +
      ". Valid " + (PRICES.validFrom || "") + " – " + (PRICES.validTo || "") + ".";

    if (isPax) {
      var cols = '<div class="pkg-pax-col"><div class="pkg-pax-season-label">Nov–Mar</div>' + renderPaxTable(variant.paxTiers.winter) + '</div>';
      if (variant.paxTiers.summer) {
        cols += '<div class="pkg-pax-col"><div class="pkg-pax-season-label">Apr–Oct</div>' + renderPaxTable(variant.paxTiers.summer) + '</div>';
      }
      $("pkgPaxRates").style.gridTemplateColumns = variant.paxTiers.summer ? "" : "1fr";
      $("pkgPaxRates").innerHTML = cols;
      return;
    }
    $("pkgPaxRates").style.gridTemplateColumns = "";

    var seasons = availableSeasons(variant);
    if (seasons.indexOf(state.season) === -1) state.season = seasons.indexOf("winter") !== -1 ? "winter" : seasons[0];
    renderRateToggles(seasons);
    $("pkgRateColHeading").textContent = "Rate — " + CAT_LABEL[state.cat] + " · " + SEASON_LABEL[state.season];
    var catRow = variant[state.cat] || {};
    var rates = catRow[state.season] || {};
    var tbody = $("pkgRatesBody");
    tbody.innerHTML =
      "<tr><td>Single</td><td>" + fmtMoney(rates.single) + "</td></tr>" +
      "<tr><td>Twin / Double</td><td>" + fmtMoney(rates.twin) + "</td></tr>" +
      "<tr><td>Child (2–11)</td><td>" + fmtMoney(rates.child) + "</td></tr>";
  }

  // ───────────────────────────── OPTIONAL TOURS ─────────────────────
  function renderOptionals() {
    var wrap = $("pkgOptionals");
    wrap.innerHTML = "";
    (PRICES.optionalTours || []).forEach(function (o) {
      var el = document.createElement("div");
      el.className = "pkg-opt-item";
      el.innerHTML = '<span class="pkg-opt-name">' + esc(o.name) + '</span><span class="pkg-opt-price">' + fmtMoney(o.price) + ' <span class="pkg-opt-pp">pp</span></span>';
      wrap.appendChild(el);
    });
  }

  // ───────────────────────────── GOOD TO KNOW ───────────────────────
  function renderGoodToKnow() {
    var wrap = $("pkgGoodToKnow");
    wrap.innerHTML = "";
    (PRODUCT.goodToKnow || []).forEach(function (item) {
      if (item.styles && item.styles.indexOf(state.style) === -1) return;
      var el = document.createElement("div");
      el.className = "pkg-gtk-card";
      el.innerHTML = '<div class="pkg-gtk-title">' + esc(item.title) + '</div><div class="pkg-gtk-body">' + esc(item.body) + '</div>';
      wrap.appendChild(el);
    });
  }

  // ───────────────────────────── T&C ────────────────────────────────
  function renderTerms() {
    var list = $("pkgTerms");
    list.innerHTML = "";
    (PRODUCT.terms || []).forEach(function (t) {
      var li = document.createElement("li");
      li.textContent = t;
      list.appendChild(li);
    });
    $("pkgTcBody").classList.toggle("open", state.tcOpen);
    $("pkgTcArrow").textContent = state.tcOpen ? "▲" : "▼";
  }

  function toggleTC() {
    state.tcOpen = !state.tcOpen;
    renderTerms();
  }

  // ───────────────────────────── SIDEBAR ────────────────────────────
  function renderSidebar() {
    var style = PRODUCT.styles[state.style] || {};
    $("pkgAboutDuration").textContent = style.aboutNights || style.nights || "";
    $("pkgAboutRoute").textContent = style.route || "";
    var wrap = $("pkgAboutFacts");
    wrap.innerHTML = "";
    (PRODUCT.about || []).forEach(function (fact) {
      var row = document.createElement("div");
      row.className = "pkg-fact-row";
      row.innerHTML = '<div class="pkg-fact-title">' + esc(fact.title) + '</div><div class="pkg-fact-body">' + esc(fact.body) + '</div>';
      wrap.appendChild(row);
    });
  }

  // ───────────────────────────── MAPS (Leaflet) ─────────────────────
  // Square gold badges with the night count, navy squares for pass-through stops -
  // same skin at every size, per design_handoff_metro's route-map spec.
  function markerIcon(size, nights) {
    return L.divIcon({
      className: "pkg-badge-icon",
      html: '<div class="pkg-badge" style="width:' + size + 'px;height:' + size + 'px;line-height:' + size + 'px;font-size:' + (size > 20 ? 11 : 9) + 'px;">' + nights + "N</div>",
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2]
    });
  }

  function passThroughIcon(size) {
    return L.divIcon({
      className: "pkg-quiet-icon",
      html: '<div class="pkg-quiet-dot" style="width:' + size + 'px;height:' + size + 'px;"></div>',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2]
    });
  }

  function buildMap(containerId, interactive) {
    var points = (PRODUCT.map || {}).points || [];
    if (!points.length || typeof L === "undefined") return null;
    var map = L.map(containerId, {
      zoomControl: interactive,
      scrollWheelZoom: interactive,
      dragging: interactive,
      touchZoom: interactive,
      doubleClickZoom: interactive,
      boxZoom: interactive,
      keyboard: interactive,
      attributionControl: false
    });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=" + CARTO_API_KEY, { maxZoom: 18 }).addTo(map);

    var lats = points.map(function (p) { return p.lat; });
    var lngs = points.map(function (p) { return p.lng; });
    var pad = 0.4;
    map.fitBounds([[Math.min.apply(null, lats) - pad, Math.min.apply(null, lngs) - pad],
                   [Math.max.apply(null, lats) + pad, Math.max.apply(null, lngs) + pad]]);

    var latlngs = points.map(function (p) { return [p.lat, p.lng]; });
    if ((PRODUCT.map || {}).closeLoop && latlngs.length > 1) latlngs.push(latlngs[0]);
    if (latlngs.length > 1) {
      L.polyline(latlngs, { color: "#0B1733", weight: 2, dashArray: "5,4", opacity: 0.85 }).addTo(map);
    }

    var badgeSize = interactive ? 20 : 16;
    var passSize = interactive ? 8 : 6;
    points.forEach(function (p) {
      if (p.nights > 0) {
        L.marker([p.lat, p.lng], { icon: markerIcon(badgeSize, p.nights) })
          .addTo(map)
          .bindTooltip(p.label + " · " + p.nights + "N", { permanent: true, direction: "top", className: "pkg-map-tip", offset: [0, -badgeSize / 2] });
      } else {
        L.marker([p.lat, p.lng], { icon: passThroughIcon(passSize) })
          .addTo(map)
          .bindTooltip(p.label, { permanent: true, direction: "top", className: "pkg-map-tip", offset: [0, -passSize / 2] });
      }
    });
    return map;
  }

  function openMapModal() {
    state.mapOpen = true;
    $("pkgMapModal").classList.add("open");
    $("pkgMapModalTitle").textContent = "ROUTE MAP — " + (PRODUCT.title || "").toUpperCase();
    setTimeout(function () {
      largeMap = buildMap("pkgMapModalCanvas", true);
      if (largeMap) largeMap.invalidateSize();
    }, 50);
    document.addEventListener("keydown", onMapEsc);
  }

  function closeMapModal() {
    state.mapOpen = false;
    $("pkgMapModal").classList.remove("open");
    if (largeMap) { largeMap.remove(); largeMap = null; }
    document.removeEventListener("keydown", onMapEsc);
  }

  function onMapEsc(e) { if (e.key === "Escape") closeMapModal(); }

  // ───────────────────────────── PDF / PRINT ─────────────────────────
  function downloadPDF() {
    state.tcOpen = true;
    renderTerms();
    setTimeout(function () { window.print(); }, 150);
  }

  // ───────────────────────────── FULL RENDER ─────────────────────────
  function renderAll() {
    renderHero();
    renderVariantBar();
    renderYearBar();
    renderDays();
    renderIncludes();
    renderHotels();
    renderRates();
    renderOptionals();
    renderGoodToKnow();
    renderSidebar();
    renderTerms();
  }

  function init() {
    renderAll();
    if (!smallMap) smallMap = buildMap("pkgMapSmall", false);

    $("pkgDownloadBtn").addEventListener("click", downloadPDF);
    $("pkgTcBtn").addEventListener("click", toggleTC);
    $("pkgMapBox").addEventListener("click", openMapModal);
    $("pkgMapModalClose").addEventListener("click", function (e) {
      e.stopPropagation();
      closeMapModal();
    });
    $("pkgMapModal").addEventListener("click", function (e) {
      if (e.target === $("pkgMapModal")) closeMapModal();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
