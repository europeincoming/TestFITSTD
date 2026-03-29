from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request


SEARCH_SCRIPT = """// Global Search Script for Europe Incoming FIT Packages
let allPackages = [];
async function loadPackages() {
  try {
    const depth = getPageDepth();
    const response = await fetch(depth + 'packages.json');
    const data = await response.json();
    allPackages = data.packages || [];
  } catch (error) { console.error('Error loading packages:', error); }
}
function getPageDepth() {
  const parts = window.location.pathname.split('/').filter(Boolean);
  const repoIndex = parts.indexOf('TestFITSTD');
  if (repoIndex === -1) return './';
  const insideRepo = parts.slice(repoIndex + 1);
  const depth = Math.max(insideRepo.length - 1, 0);
  return depth === 0 ? './' : '../'.repeat(depth);
}
function searchPackages(query) {
  if (!query || query.length < 2) return [];
  const searchTerm = query.toLowerCase().trim();
  const results = [];
  allPackages.forEach(pkg => {
    let score = 0;
    const cities = Array.isArray(pkg.cities) ? pkg.cities : [];
    const tags = Array.isArray(pkg.tags) ? pkg.tags : [];
    if ((pkg.name || '').toLowerCase().includes(searchTerm)) score += 10;
    cities.forEach(city => { if ((city || '').toLowerCase().includes(searchTerm)) score += 8; });
    if ((pkg.region || '').toLowerCase().includes(searchTerm)) score += 6;
    tags.forEach(tag => { if ((tag || '').toLowerCase().includes(searchTerm)) score += 5; });
    if ((pkg.type || '').toLowerCase().includes(searchTerm)) score += 4;
    if ((pkg.duration || '').toLowerCase().includes(searchTerm)) score += 3;
    if (score > 0) results.push({ ...pkg, score });
  });
  return results.sort((a, b) => b.score - a.score);
}
function displaySearchResults(results) {
  const depth = getPageDepth();
  let resultsContainer = document.getElementById('globalSearchResults');
  if (!resultsContainer) {
    resultsContainer = document.createElement('div');
    resultsContainer.id = 'globalSearchResults';
    resultsContainer.className = 'search-results-overlay';
    document.body.appendChild(resultsContainer);
  }
  if (!results.length) {
    resultsContainer.innerHTML = '<div class="search-results-container"><div class="search-results-header"><h3>Search Results</h3><button onclick="closeSearchResults()" class="close-btn">✕</button></div><div class="no-results"><p>No packages found matching your search.</p></div></div>';
    resultsContainer.style.display = 'block';
    return;
  }
  const resultsHTML = results.map(pkg => {
    const citiesList = (pkg.cities || []).join(', ');
    const targetUrl = pkg.link ? depth + pkg.link : depth + pkg.folder + '/' + pkg.filename;
    const badge = pkg.link ? 'Page' : 'PDF';
    return `<a href="${targetUrl}" class="search-result-card"><div class="result-header"><h4>${pkg.name}</h4><span class="pdf-badge">${badge}</span></div><div class="result-details"><span class="result-region">${pkg.region || ''}</span><span class="result-separator">•</span><span class="result-duration">${pkg.duration || ''}</span><span class="result-separator">•</span><span class="result-type">${pkg.type || ''}</span></div><div class="result-cities"><strong>Cities:</strong> ${citiesList}</div></a>`;
  }).join('');
  resultsContainer.innerHTML = `<div class="search-results-container"><div class="search-results-header"><h3>Search Results <span class="result-count">(${results.length})</span></h3><button onclick="closeSearchResults()" class="close-btn">✕</button></div><div class="search-results-list">${resultsHTML}</div></div>`;
  resultsContainer.style.display = 'block';
}
function closeSearchResults() {
  const resultsContainer = document.getElementById('globalSearchResults');
  if (resultsContainer) resultsContainer.style.display = 'none';
}
document.addEventListener('DOMContentLoaded', async function () {
  await loadPackages();
  const searchBox = document.getElementById('searchBox');
  if (!searchBox) return;
  let searchTimeout;
  searchBox.addEventListener('input', function (e) {
    clearTimeout(searchTimeout);
    const query = e.target.value;
    if (query.length < 2) { closeSearchResults(); return; }
    searchTimeout = setTimeout(() => displaySearchResults(searchPackages(query)), 300);
  });
  document.addEventListener('click', function (e) {
    const resultsContainer = document.getElementById('globalSearchResults');
    if (resultsContainer && !resultsContainer.contains(e.target) && e.target !== searchBox) closeSearchResults();
  });
});
document.head.insertAdjacentHTML('beforeend', `<style>.search-results-overlay{position:fixed;top:80px;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:9999;display:none;overflow-y:auto;padding:20px}.search-results-container{max-width:900px;margin:0 auto;background:white;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.2);overflow:hidden}.search-results-header{padding:24px;background:#f5f5f5;border-bottom:1px solid #e0e0e0;display:flex;justify-content:space-between;align-items:center}.search-results-list{padding:16px;max-height:600px;overflow-y:auto}.search-result-card{display:block;padding:20px;margin-bottom:12px;background:white;border:1px solid #e0e0e0;border-radius:8px;text-decoration:none;color:inherit}.result-header{display:flex;justify-content:space-between;align-items:start;margin-bottom:8px}.pdf-badge{background:#d32f2f;color:white;padding:4px 10px;border-radius:4px;font-size:.75em;font-weight:600}.result-details{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:.9em;color:#757575}.close-btn{background:none;border:none;font-size:1.5em;color:#757575;cursor:pointer}.no-results{padding:60px 20px;text-align:center}</style>`);
"""


DESTINATION_EDITORIAL = {
    "London": {
        "experiences": [("Westminster and the South Bank", "Pair the landmarks with a relaxed walk beside the Thames for the city at its most recognisable."), ("Tower of London and Tower Bridge", "A rewarding stop for guests who enjoy royal history, armouries and classic skyline moments.")],
        "food": [("Modern British dining", "A seasonal menu with good produce usually feels more memorable than the obvious tourist addresses."), ("Afternoon tea", "Best taken as a proper pause between visits rather than a rushed box to tick.")],
        "unique": [("Twilight on the Thames", "Evening light along the river gives the city a completely different atmosphere."), ("West End performance", "A theatre night adds an easy, distinctly local flourish to the stay.")],
        "note": "Leave space for the city to breathe between headline sights and quieter corners.",
    },
    "Paris": {
        "experiences": [("Seine-side classics", "The riverside stretch still offers the most elegant first feel of Paris."), ("Le Marais", "Boutiques, courtyards and handsome streets add a more intimate side to the city.")],
        "food": [("Bistro favourites", "Simple French staples often beat overly formal dining for warmth and charm."), ("Patisserie stops", "A good pastry and coffee break can become one of the day’s genuine highlights.")],
        "unique": [("Evening illuminations", "Paris softens beautifully once the day crowds thin and the lights come on."), ("Covered passages", "These tucked-away arcades add a layer many first-time visitors miss.")],
        "note": "Paris rewards a slower pace and a little room for wandering.",
    },
}


GENERIC_EDITORIAL = {
    "experiences": [("Historic centre strolls", "Allow time to explore the old streets on foot rather than moving too quickly between formal visits."), ("A landmark viewpoint", "A city look-out or waterfront often gives the strongest first sense of place.")],
    "food": [("Local specialities", "A regional dish or two gives guests an easy cultural connection without needing a formal food tour."), ("Coffee and pastry pause", "These unhurried stops often become the moments guests remember most fondly.")],
    "unique": [("Golden-hour atmosphere", "Many European cities feel their most memorable once the pace softens in the early evening."), ("Small local discoveries", "Markets and neighbourhood rituals often create the most authentic impressions.")],
    "note": "The best moments often come from leaving a little room for spontaneity.",
}


def patch_module(mod):
    mod.GEO_BLOCK = ""
    mod.MARK12_OWNER = "leviathanyx"
    mod.MARK12_REPO = "mark12"
    mod.MARK12_REF = os.environ.get("MARK12_REF", "automated-pricing-automation-10989447671478572791")
    mod.MARK12_RAW = f"https://raw.githubusercontent.com/{mod.MARK12_OWNER}/{mod.MARK12_REPO}/{mod.MARK12_REF}"
    mod.main = lambda: enhanced_main(mod)


def enhanced_main(mod):
    _write_search_script(mod)
    packages_path = os.path.join(mod.REPO_ROOT, "packages.json")
    all_found = []
    region_stats = {}
    desc_cache = {}
    coords_cache = mod.load_coords_cache()
    coords_dirty = False
    existing_pkgs = mod.load_existing_packages(packages_path)
    mark12_pkgs = fetch_mark12_packages(mod)

    for folder_rel, config in mod.FOLDER_CONFIG.items():
        folder_abs = os.path.join(mod.REPO_ROOT, folder_rel)
        if not os.path.isdir(folder_abs) or folder_rel.startswith("multi-country"):
            continue
        pdfs = sorted([f for f in os.listdir(folder_abs) if f.lower().endswith(".pdf")])
        if not pdfs:
            continue
        depth = config["depth"]
        logo_src = "../" * depth + "logo.png"
        logo_href = "../" * depth
        search_js = "../" * depth + "global-search.js"
        breadcrumb = f'<a href="../">Home</a> › {config["breadcrumb"]}' if depth == 1 else f'<a href="../../">Home</a> › <a href="../">Multi-Country</a> › {config["breadcrumb"]}'
        cards, maps_js_parts, tour_types_seen = [], [], []

        for idx, pdf in enumerate(pdfs):
            pkg_key = folder_rel + "/" + pdf
            pdf_data = mod.extract_pdf_data(os.path.join(folder_abs, pdf), pdf)
            title = mod.make_title(pdf)
            cached_desc = existing_pkgs.get(pkg_key, {}).get("description")
            desc = mod.generate_description(pdf_data.get("cities", []), config["region"], pdf_data.get("tour_type", ""), pdf_data.get("season", "all-year"), os.path.join(folder_abs, pdf), cached_desc)
            desc_cache[pkg_key] = desc
            for city in pdf_data.get("cities", []):
                was_missing = city not in coords_cache
                mod.get_coords(city, coords_cache)
                if was_missing and city in coords_cache:
                    coords_dirty = True
            map_id = f"map_{re.sub(r'[^a-z0-9]', '_', pdf.lower()[:18])}_{idx}"
            all_found.append({"filename": pdf, "title": title, "folder": folder_rel, "region": config["region"], "pdf_data": pdf_data})
            brochure_page = None
            tt = (pdf_data.get("tour_type") or "").lower().replace(" ", "_").replace("-", "_")
            for sid, mpkg in mark12_pkgs.items():
                mpkg_region = mod.MARK12_REGION_MAP.get(mpkg.get("region", ""), "")
                if mpkg_region != folder_rel:
                    continue
                variants = mpkg.get("variants", {})
                if ("self" in tt and "self_drive" in variants) or ("private" in tt and "private" in variants) or ("regular" in tt and "regular_fit" in variants) or (not tt and variants):
                    brochure_page = f"{sid}_brochure.html"
                    break
            cards.append(mod.make_brochure_card(pdf, pdf_data, title, desc, map_id, coords_cache, brochure_page))
            js = mod.make_map_js(map_id, pdf_data.get("cities", []), coords_cache)
            if js:
                maps_js_parts.append(js)
            tt2 = pdf_data.get("tour_type", "")
            if tt2 and tt2 not in tour_types_seen:
                tour_types_seen.append(tt2)

        html_out = mod.build_brochure_index(config["title"], breadcrumb, "\n".join(cards), "\n".join(maps_js_parts), logo_src, logo_href, search_js)
        with open(os.path.join(folder_abs, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_out)
        if depth == 2:
            slug = folder_rel.replace("multi-country/", "")
            region_stats[slug] = {"count": len(pdfs), "tour_types": tour_types_seen}

    brochure_names_used = {}
    region_packages = {}
    for sid, mpkg in mark12_pkgs.items():
        folder_rel = mod.MARK12_REGION_MAP.get(mpkg.get("region", ""))
        if folder_rel:
            region_packages.setdefault(folder_rel, []).append((sid, mpkg))

    for folder_rel, pkgs in region_packages.items():
        folder_abs = os.path.join(mod.REPO_ROOT, folder_rel)
        os.makedirs(folder_abs, exist_ok=True)
        config = mod.FOLDER_CONFIG.get(folder_rel, {})
        depth = config.get("depth", 2)
        logo_src = "../" * depth + "logo.png"
        logo_href = "../" * depth
        search_js = "../" * depth + "global-search.js"
        breadcrumb = f'<a href="../../">Home</a> › <a href="../">Multi-Country</a> › {config.get("breadcrumb", "")}'
        cards, maps_js_parts, tour_types_seen = [], [], []

        for sid, mpkg in sorted(pkgs, key=lambda x: x[0]):
            cities = get_itinerary_cities(mpkg)
            for city in cities:
                was_missing = city not in coords_cache
                mod.get_coords(city, coords_cache)
                if was_missing and city in coords_cache:
                    coords_dirty = True
            page_html = generate_brochure_page_v2(mod, mpkg, coords_cache, depth)
            base_slug = str(mpkg.get("id") or sid.split("_")[0])
            used_count = brochure_names_used.get(base_slug, 0)
            brochure_names_used[base_slug] = used_count + 1
            brochure_stem = base_slug if used_count == 0 else f"{base_slug}_{re.sub(r'[^a-z0-9]+', '_', mpkg.get('title', '').lower()).strip('_')[:28] or str(used_count + 1)}"
            brochure_fname = f"{brochure_stem}_brochure.html"
            with open(os.path.join(folder_abs, brochure_fname), "w", encoding="utf-8") as f:
                f.write(page_html)
            variants = mpkg.get("variants", {})
            price = first_twin_price(variants)
            desc = mpkg.get("description", "") or fallback_desc(mpkg, config.get("region", ""))
            route = " → ".join(cities)
            img = mod.get_card_image(cities)
            dur = f"{mpkg.get('nights')} nights" if mpkg.get("nights") else ""
            winter_only = mpkg.get("winter_only", False)
            season_cls = "season-winter" if winter_only else "season-allyear"
            season_lbl = "❄️ Winter" if winter_only else "🌍 All Year"
            curr_sym = "£" if mpkg.get("currency", "EUR") == "GBP" else "€"
            price_html = f'<div class="card-price">From {curr_sym}{price:,.0f} pp</div>' if price else ""
            for vk in variants:
                vl = {"regular_fit": "Regular", "private": "Private", "self_drive": "Self Drive"}.get(vk, "")
                if vl and vl not in tour_types_seen:
                    tour_types_seen.append(vl)
            cards.append(f"""<div class=\"brochure-card\"><div class=\"card-hero\"><img src=\"{img}\" alt=\"{html.escape(mpkg.get('title', ''))}\" loading=\"lazy\"><div class=\"card-hero-overlay\"></div><div class=\"card-season {season_cls}\">{season_lbl}</div></div><div class=\"card-body\"><div class=\"card-title\">{html.escape(mpkg.get('title', ''))}</div>{\"<div class='card-duration'>🕐 \" + dur + \"</div>\" if dur else \"\"}{\"<div class='card-route'>📍 \" + html.escape(route) + \"</div>\" if route else \"\"}{\"<div class='card-desc'>\" + html.escape(desc) + \"</div>\" if desc else \"\"}{price_html}</div><div class=\"card-actions\"><a href=\"{brochure_fname}\" class=\"btn-view\">View Package</a></div></div>""")
            js = mod.make_map_js(f"map_{sid.replace('.', '_')}", cities, coords_cache)
            if js:
                maps_js_parts.append(js)
            all_found.append({"filename": brochure_fname, "title": mpkg.get("title", ""), "folder": folder_rel, "region": config.get("region", ""), "pdf_data": {"cities": cities, "duration": f"{mpkg.get('nights')} nights" if mpkg.get("nights") else "", "tour_type": "", "season": "winter" if winter_only else "all-year", "price_twin": None, "currency": mpkg.get("currency", "EUR"), "valid_till": ""}, "link": f"{folder_rel}/{brochure_fname}"})
            desc_cache[f"{folder_rel}/{brochure_fname}"] = desc

        html_out = mod.build_brochure_index(config.get("title", ""), breadcrumb, "\n".join(cards), "\n".join(maps_js_parts), logo_src, logo_href, search_js)
        with open(os.path.join(folder_abs, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_out)
        slug = folder_rel.replace("multi-country/", "")
        region_stats[slug] = {"count": len(cards), "tour_types": tour_types_seen}

    if coords_dirty:
        mod.save_coords_cache(coords_cache)
    mc_folder = os.path.join(mod.REPO_ROOT, "multi-country")
    if os.path.isdir(mc_folder):
        region_cards = []
        for slug, display in mod.REGION_DISPLAY.items():
            stats = region_stats.get(slug, {"count": 0, "tour_types": []})
            if stats["count"] > 0:
                region_cards.append(mod.make_region_card(slug, display, stats["count"], stats["tour_types"]))
        with open(os.path.join(mc_folder, "index.html"), "w", encoding="utf-8") as f:
            f.write(mod.build_multicountry_index("\n".join(region_cards), "../", "../global-search.js"))

    rewrite_static_page(os.path.join(mod.REPO_ROOT, "index.html"))
    rewrite_static_page(os.path.join(mod.REPO_ROOT, "city-break", "index.html"))
    update_packages_json(mod, packages_path, all_found, desc_cache)


def _write_search_script(mod):
    with open(os.path.join(mod.REPO_ROOT, "global-search.js"), "w", encoding="utf-8") as f:
        f.write(SEARCH_SCRIPT)


def rewrite_static_page(path):
    if not os.path.exists(path):
        return
    text = open(path, encoding="utf-8").read()
    text = re.sub(r'<script>.*?Service Not Available.*?</script>', '', text, flags=re.S)
    text = text.replace("/FITGlobal/", "/TestFITSTD/")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def fetch_mark12_index(mod):
    url = f"https://api.github.com/repos/{mod.MARK12_OWNER}/{mod.MARK12_REPO}/contents/packages?ref={urllib.parse.quote(mod.MARK12_REF)}"
    req = urllib.request.Request(url, headers={"User-Agent": "EuropeIncomingFIT/1.0", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_mark12_packages(mod):
    items = fetch_mark12_index(mod)
    pkgs = {}
    for item in items:
        name = item.get("name", "")
        if not name.endswith(".json"):
            continue
        with urllib.request.urlopen(item["download_url"], timeout=20) as r:
            pkgs[os.path.splitext(name)[0]] = json.loads(r.read().decode("utf-8"))
    return pkgs


def get_itinerary_cities(pkg):
    cities = []
    for hotel in pkg.get("hotels", []):
        city = hotel.get("city")
        if city and city not in cities:
            cities.append(city)
    routing = pkg.get("routing", "")
    if routing:
        for bit in re.split(r"\s*→\s*|\s*-\s*", routing):
            candidate = re.sub(r"^\d+\s*", "", bit).strip()
            if candidate and candidate not in cities:
                cities.append(candidate)
    return cities


def build_day_city_sequence(pkg):
    sequence = []
    for hotel in pkg.get("hotels", []):
        city = hotel.get("city")
        try:
            nights = int(hotel.get("nights", 0))
        except Exception:
            nights = 0
        if city and nights:
            sequence.extend([city] * nights)
    return sequence or get_itinerary_cities(pkg)


def get_destination_editorial(city):
    for key, payload in DESTINATION_EDITORIAL.items():
        if key.lower() in city.lower() or city.lower() in key.lower():
            return payload
    return GENERIC_EDITORIAL


def first_twin_price(variants):
    for vkey in ["regular_fit", "private", "self_drive"]:
        vdata = variants.get(vkey, {})
        pricing = vdata.get("pricing", {})
        for market in ["Standard", "Premium"]:
            for skey in ["winter", "summer"]:
                sp = pricing.get(market, {}).get(skey)
                if isinstance(sp, dict):
                    twin = sp.get("3star", {}).get("twin") or sp.get("4star", {}).get("twin")
                    if twin:
                        return float(twin)
    return None


def fallback_desc(pkg, region):
    cities = get_itinerary_cities(pkg)
    if cities:
        return f"{cities[0]} and {max(len(cities) - 1, 0)} more well-paced stops across {region or 'Europe'}."
    return pkg.get("title", "")


def build_day_description(city, day_number, total_days, services):
    edit = get_destination_editorial(city)
    lead = f"Today is devoted to {city}, giving guests time to settle into the rhythm of the itinerary and enjoy the destination at their own pace."
    service_line = "Included arrangements today may cover " + ", ".join(html.escape(s.replace("_", " ")) for s in services[:3]) + "." if services else "The day is designed to balance included arrangements with time for independent exploration."
    close = "It is a good point in the journey to keep the pace comfortable and leave room for spontaneous local discoveries." if day_number < total_days else "It rounds out the programme with a sense of place rather than a rushed checklist."
    return " ".join([lead, edit["note"], service_line, close])


def build_sidebar_sections(cities):
    groups = {"experiences": [], "food": [], "unique": []}
    for city in cities[:3]:
        payload = get_destination_editorial(city)
        for key in groups:
            groups[key].extend(payload[key][:2])
    labels = {"experiences": "Top Experiences", "food": "Local Must-Tries", "unique": "Distinctive Moments"}
    rendered = []
    for key, title in labels.items():
        lis = "".join(f"<li><strong>{html.escape(head)}</strong><span>{html.escape(body)}</span></li>" for head, body in groups[key][:5])
        rendered.append(f'<section class="side-section"><h3>{title}</h3><ul class="side-list">{lis}</ul></section>')
    return "".join(rendered)


def render_pricing_tables(pkg):
    out = []
    for variant_key, label in [("regular_fit", "Regular FIT"), ("private", "Private Tour"), ("self_drive", "Self Drive")]:
        variant = pkg.get("variants", {}).get(variant_key)
        if not variant:
            continue
        rows = []
        for market, market_data in variant.get("pricing", {}).items():
            for season, season_data in market_data.items():
                if not isinstance(season_data, dict):
                    continue
                for star in ["3star", "4star"]:
                    star_data = season_data.get(star)
                    if not star_data:
                        continue
                    rows.append(f"<tr><td>{market}</td><td>{season.title()}</td><td>{star.replace('star', ' Star')}</td><td>{star_data.get('single', '')}</td><td>{star_data.get('twin', '')}</td><td>{star_data.get('child', '')}</td></tr>")
        if rows:
            out.append(f"""<section class=\"variant-panel\"><h3>{label}</h3><table class=\"rates-table\"><thead><tr><th>Market</th><th>Season</th><th>Hotel</th><th>Single</th><th>Twin / Double</th><th>Child</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>""")
    return "".join(out)


def generate_brochure_page_v2(mod, pkg, coords_cache, depth=2):
    title = html.escape(pkg.get("title", ""))
    cities = get_itinerary_cities(pkg)
    route = html.escape(" → ".join(cities))
    nights = pkg.get("nights", "")
    map_id = f"route_map_{re.sub(r'[^a-z0-9]+', '_', pkg.get('id', 'route').lower())}"
    day_sequence = build_day_city_sequence(pkg)
    service_lookup = {}
    for service in pkg.get("services", []):
        day = service.get("day")
        if day:
            service_lookup.setdefault(day, []).append(service.get("name", ""))
    day_blocks = []
    for idx, city in enumerate(day_sequence, start=1):
        services = service_lookup.get(idx, [])
        desc = build_day_description(city, idx, len(day_sequence), services)
        day_blocks.append(f"""<article class=\"day-card\"><div class=\"day-label\">Day {idx}</div><div class=\"day-copy\"><h3>{html.escape(city)}</h3><div class=\"day-overnight\">Overnight: {html.escape(city)}</div><p class=\"day-desc\">{html.escape(desc)}</p>{\"<ul class='day-includes'>\" + \"\".join(f\"<li>{html.escape(s)}</li>\" for s in services) + \"</ul>\" if services else \"\"}</div></article>""")
    hotels = "".join(f"<div class='hotel-card'><h4>{html.escape(h.get('city', ''))}</h4><div>{html.escape(str(h.get('nights', '')))} nights</div><div>3 Star: {html.escape(h.get('3star', 'TBC'))}</div><div>4 Star: {html.escape(h.get('4star', 'TBC'))}</div></div>" for h in pkg.get("hotels", []))
    services_all = "".join(f"<li>{html.escape(s.get('name', ''))}</li>" for s in pkg.get("services", []))
    map_js = mod.make_map_js(map_id, cities, coords_cache) or ""
    css = "body{font-family:'Inter',sans-serif;background:#f6f7fb;color:#1f2430;margin:0}.page-shell{max-width:1320px;margin:0 auto;padding:32px 24px 48px}.page-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;gap:20px}.page-back{color:#1a3a5c;text-decoration:none;font-size:14px;font-weight:600}.page-title h1{font-family:'Playfair Display',serif;font-size:40px;margin:0;color:#16213b}.page-title p{margin:8px 0 0;color:#61697a}.download-link{background:#1a3a5c;color:#fff;text-decoration:none;padding:12px 16px;border-radius:8px;font-weight:600}.content-grid{display:grid;grid-template-columns:320px minmax(0,1fr);gap:28px;align-items:start}.sidebar{position:sticky;top:24px;background:#fff;border:1px solid #e6e8ef;border-radius:18px;padding:22px}.side-section+.side-section{margin-top:22px}.side-section h3{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#7b8397;margin:0 0 12px}.side-list{list-style:none;margin:0;padding:0;display:grid;gap:12px}.side-list li{display:grid;gap:4px}.side-list strong{color:#1b2333;font-size:14px}.side-list span{color:#5f6779;font-size:14px;line-height:1.55}.main-col{display:grid;gap:28px}.panel{background:#fff;border:1px solid #e6e8ef;border-radius:18px;padding:24px}.panel h2{font-family:'Playfair Display',serif;font-size:26px;margin:0 0 16px;color:#16213b}.route-map{height:300px;border-radius:14px;overflow:hidden;background:#eef1f6}.day-card+.day-card{margin-top:18px;padding-top:18px;border-top:1px solid #eef1f6}.day-card{display:grid;grid-template-columns:80px minmax(0,1fr);gap:18px}.day-label{font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#7b8397;padding-top:4px}.day-copy h3{margin:0;font-size:26px;color:#16213b;font-family:'Playfair Display',serif}.day-overnight{margin-top:6px;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:#b07c3a}.day-desc{margin:14px 0 0;color:#4d5568;line-height:1.8}.day-includes{margin:14px 0 0;padding-left:18px;color:#4d5568}.hotel-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.hotel-card{border:1px solid #e6e8ef;border-radius:14px;padding:16px;background:#fbfcff;color:#4d5568}.hotel-card h4{margin:0 0 8px;color:#16213b}.rates-table{width:100%;border-collapse:collapse;font-size:14px}.rates-table th,.rates-table td{border-bottom:1px solid #e8ebf2;padding:12px 10px;text-align:left}.variant-panel+.variant-panel{margin-top:24px}@media (max-width:960px){.content-grid{grid-template-columns:1fr}.sidebar{position:static}.day-card{grid-template-columns:1fr}}"
    return f"""<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><title>{title} | Europe Incoming FIT Packages</title>{mod.GF_FONTS}<style>{css}</style>{mod.LEAFLET_HEAD}{mod.HTML2PDF}{mod.GA}</head><body><div class=\"page-shell\"><div class=\"page-top\"><a class=\"page-back\" href=\"../index.html\">← All Packages</a><a class=\"download-link\" href=\"javascript:window.print()\">Download / Print</a></div><div class=\"page-title\"><h1>{title}</h1><p>{html.escape(str(nights))} nights · {route}</p></div><div class=\"content-grid\"><aside class=\"sidebar\">{build_sidebar_sections(cities)}</aside><main class=\"main-col\"><section class=\"panel\"><h2>Route Map</h2><div class=\"route-map\" id=\"{map_id}\"></div></section><section class=\"panel\"><h2>Day by Day</h2>{''.join(day_blocks)}</section><section class=\"panel\"><h2>Package Includes</h2><ul class=\"day-includes\">{services_all}</ul></section><section class=\"panel\"><h2>Sample Hotels</h2><div class=\"hotel-grid\">{hotels}</div></section><section class=\"panel\"><h2>Package Rates</h2>{render_pricing_tables(pkg)}</section></main></div></div><script>{map_js}</script></body></html>"""


def update_packages_json(mod, packages_path, all_found, desc_cache):
    existing = mod.load_existing_packages(packages_path)
    new_pkgs = []
    for item in all_found:
        key = item["folder"] + "/" + item["filename"]
        if key in existing:
            pkg = existing[key].copy()
            pkg["description"] = desc_cache.get(key, pkg.get("description", ""))
            if item.get("link"):
                pkg["link"] = item["link"]
            new_pkgs.append(pkg)
        else:
            pd = item["pdf_data"]
            new_pkgs.append({"id": re.sub(r"[^a-z0-9]", "-", item["filename"].lower().replace(".pdf", ""))[:30], "name": item["title"], "filename": item["filename"], "region": item["region"], "folder": item["folder"], "cities": pd.get("cities", []), "duration": pd.get("duration", ""), "type": pd.get("tour_type", ""), "season": pd.get("season", "all-year"), "price_twin": pd.get("price_twin"), "currency": pd.get("currency", "€"), "valid_till": pd.get("valid_till"), "description": desc_cache.get(key, ""), "tags": pd.get("cities", []), "link": item.get("link")})
    with open(packages_path, "w", encoding="utf-8") as f:
        json.dump({"packages": new_pkgs}, f, indent=2)
