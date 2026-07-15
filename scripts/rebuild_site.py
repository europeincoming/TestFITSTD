"""
rebuild_site.py — v12
Changes from v11:
- Replaced the mark12-fetch brochure pipeline with a data-driven package
  page: one static HTML page per products/<id>.json, paired with a
  prices/<id>-<year>.json file (the only file touched for annual repricing).
- Package pages render client-side from inline PRODUCT/PRICES JSON via the
  shared assets/package-page.js (travel-style / hotel-category / season
  switching, route map, print-to-PDF).
- Modern card design with hero images, clean typography (v10/v11, unchanged)
"""

import os, re, json, urllib.request, urllib.parse, time
from datetime import datetime
import fitz

REPO_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
COORDS_CACHE  = os.path.join(REPO_ROOT, "city_coords_cache.json")

# ── CITY IMAGES (Unsplash, royalty-free) ─────────────────────────────────────
CITY_IMAGES = {
    "Paris":          "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=600&q=75",
    "London":         "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=600&q=75",
    "Lucerne":        "https://images.unsplash.com/photo-1527668752968-14dc70a27c95?w=600&q=75",
    "Zurich":         "https://images.unsplash.com/photo-1515488764276-beab7607c1e6?w=600&q=75",
    "Rome":           "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=600&q=75",
    "Florence":       "https://images.unsplash.com/photo-1541370976299-4d24be63b012?w=600&q=75",
    "Venice":         "https://images.unsplash.com/photo-1534113414509-0eec2bfb493f?w=600&q=75",
    "Amsterdam":      "https://images.unsplash.com/photo-1534351590666-13e3e96b5017?w=600&q=75",
    "Barcelona":      "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=600&q=75",
    "Madrid":         "https://images.unsplash.com/photo-1543783207-ec64e4d95325?w=600&q=75",
    "Prague":         "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=600&q=75",
    "Vienna":         "https://images.unsplash.com/photo-1516550893923-42d28e5677af?w=600&q=75",
    "Budapest":       "https://images.unsplash.com/photo-1592982537447-7440770cbfc9?w=600&q=75",
    "Edinburgh":      "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=75",
    "Dublin":         "https://images.unsplash.com/photo-1590089415225-401ed6f9db8e?w=600&q=75",
    "Inverness":      "https://images.unsplash.com/photo-1541849546-216549ae216d?w=600&q=75",
    "Tromsø":         "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=75",
    "Tromso":         "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=75",
    "Rovaniemi":      "https://images.unsplash.com/photo-1483347756197-71ef80e95f73?w=600&q=75",
    "Kiruna":         "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=75",
    "Abisko":         "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=75",
    "Copenhagen":     "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=600&q=75",
    "Stockholm":      "https://images.unsplash.com/photo-1509356843151-3e7d96241e11?w=600&q=75",
    "Helsinki":       "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=600&q=75",
    "Oslo":           "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=600&q=75",
    "Interlaken":     "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&q=75",
    "Innsbruck":      "https://images.unsplash.com/photo-1570438395701-4e41d57571b0?w=600&q=75",
    "Seville":        "https://images.unsplash.com/photo-1559181567-c3190e770c5c?w=600&q=75",
    "Granada":        "https://images.unsplash.com/photo-1595787572900-7b5552de22d2?w=600&q=75",
    "Bruges":         "https://images.unsplash.com/photo-1491557345352-5929e343eb89?w=600&q=75",
    "default":        "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?w=600&q=75",
}

def get_card_image(cities):
    for c in (cities or []):
        for key, url in CITY_IMAGES.items():
            if key.lower() in c.lower() or c.lower() in key.lower():
                return url
    return CITY_IMAGES["default"]

# ── FOLDER CONFIG (unchanged from v10) ───────────────────────────────────────
FOLDER_CONFIG = {
    "city-break": {"title": "City Breaks Packages", "breadcrumb": "City Breaks", "region": "City Break", "depth": 1},
    "multi-country/italy": {"title": "Italy", "breadcrumb": "Italy", "region": "Italy", "depth": 2},
    "multi-country/eastern-europe": {"title": "Eastern Europe", "breadcrumb": "Eastern Europe", "region": "Eastern Europe", "depth": 2},
    "multi-country/france": {"title": "France", "breadcrumb": "France", "region": "France", "depth": 2},
    "multi-country/scandinavia-iceland": {"title": "Scandinavia & Iceland", "breadcrumb": "Scandinavia & Iceland", "region": "Scandinavia & Iceland", "depth": 2},
    "multi-country/spain-portugal": {"title": "Spain & Portugal", "breadcrumb": "Spain & Portugal", "region": "Spain & Portugal", "depth": 2},
    "multi-country/switzerland": {"title": "Switzerland", "breadcrumb": "Switzerland", "region": "Switzerland", "depth": 2},
    "multi-country/uk-ireland": {"title": "UK & Ireland", "breadcrumb": "UK & Ireland", "region": "UK & Ireland", "depth": 2},
    "multi-country/western-central-europe": {"title": "Western & Central Europe", "breadcrumb": "Western & Central Europe", "region": "Western & Central Europe", "depth": 2},
}

REGION_DISPLAY = {
    "italy": "Italy", "eastern-europe": "Eastern Europe", "france": "France",
    "scandinavia-iceland": "Scandinavia & Iceland", "spain-portugal": "Spain & Portugal",
    "switzerland": "Switzerland", "uk-ireland": "UK & Ireland",
    "western-central-europe": "Western & Central Europe",
}

SEED_COORDS = {
    "Amsterdam": [52.3676, 4.9041], "Athens": [37.9838, 23.7275],
    "Barcelona": [41.3851, 2.1734], "Berlin": [52.5200, 13.4050],
    "Brussels": [50.8503, 4.3517], "Budapest": [47.4979, 19.0402],
    "Copenhagen": [55.6761, 12.5683], "Dublin": [53.3498, -6.2603],
    "Edinburgh": [55.9533, -3.1883], "Florence": [43.7696, 11.2558],
    "Geneva": [46.2044, 6.1432], "Glasgow": [55.8642, -4.2518],
    "Helsinki": [60.1699, 24.9384], "Innsbruck": [47.2692, 11.4041],
    "Interlaken": [46.6863, 7.8632], "London": [51.5074, -0.1278],
    "Lucerne": [47.0502, 8.3093], "Madrid": [40.4168, -3.7038],
    "Milan": [45.4654, 9.1859], "Nice": [43.7102, 7.2620],
    "Oslo": [59.9139, 10.7522], "Paris": [48.8566, 2.3522],
    "Prague": [50.0755, 14.4378], "Rome": [41.9028, 12.4964],
    "Salzburg": [47.8095, 13.0550], "Stockholm": [59.3293, 18.0686],
    "Venice": [45.4408, 12.3155], "Vienna": [48.2082, 16.3738],
    "Zurich": [47.3769, 8.5417], "Bergen": [60.3913, 5.3221],
    "Reykjavik": [64.1265, -21.8174], "Inverness": [57.4778, -4.2247],
    "Manchester": [53.4808, -2.2426], "Fort William": [56.8198, -5.1052],
    "Limerick": [52.6638, -8.6267], "Bayeux": [49.2764, -0.7024],
    "Tours": [47.3941, 0.6848], "Avignon": [43.9493, 4.8055],
    "Montreux": [46.4312, 6.9107], "Naples": [40.8518, 14.2681],
    "Bruges": [51.2093, 3.2247], "Seville": [37.3891, -5.9845],
    "Granada": [37.1773, -3.5986], "Cagliari": [39.2238, 9.1217],
    "Ajaccio": [41.9192, 8.7386], "Bonifacio": [41.3871, 9.1597],
    "Tromso": [69.6489, 18.9551], "Tromsø": [69.6489, 18.9551],
    "Kiruna": [67.8558, 20.2253], "Abisko": [68.3493, 18.8306],
    "Rovaniemi": [66.5039, 25.7294], "Flam": [60.8633, 7.1159],
    "Venice Mestre": [45.4847, 12.2386],
    "Cheltenham": [51.8994, -2.0783], "Barnstaple": [51.0803, -4.0588],
    "Truro": [50.2632, -5.0510], "Plymouth": [50.3755, -4.1427],
    "Exeter": [50.7184, -3.5339], "Bournemouth": [50.7192, -1.8808],
    "Bath": [51.3758, -2.3599], "Belfast": [54.5973, -5.9301],
}

COMPOUND_NAMES = {
    'East Europe', 'Eastern Europe', 'Western Europe', 'Central Europe',
    'Costa Smeralda', 'Cala Gonone', 'Fort William', 'Venice Mestre',
}

GEO_BLOCK = """<script>
(async function(){try{const r=await fetch('https://api.country.is/');const d=await r.json();
if(['US','CA','AU','NZ'].includes(d.country)){document.body.innerHTML='<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#f5f5f5;text-align:center"><h1 style="font-size:48px">🌍</h1><h2>Service Not Available</h2><p style="color:#757575">This site is not available in your region.</p></div>';}}catch(e){}}
)();</script>"""

GA = """<script async src="https://www.googletagmanager.com/gtag/js?id=G-04BZKH6574"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-04BZKH6574');</script>"""

LEAFLET_HEAD = """<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>"""

HTML2PDF = """<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>"""

GF_FONTS = """<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:ital,wght@0,700;1,400&display=swap" rel="stylesheet">"""

# ── SHARED NAV CSS ────────────────────────────────────────────────────────────
BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#212121;line-height:1.6;padding-top:72px;}
.top-nav{position:fixed;top:0;left:0;right:0;background:white;box-shadow:0 1px 3px rgba(0,0,0,0.08);z-index:1000;padding:12px 0;}
.nav-container{max-width:1200px;margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:24px;}
.logo{height:44px;width:auto;}
.logo:hover{opacity:0.8;}
.search-wrap{flex:1;max-width:420px;position:relative;}
.search-box{width:100%;padding:9px 18px;font-size:0.92em;border:1px solid #e0e0e0;border-radius:24px;background:#fafafa;transition:all 0.2s;font-family:'Inter',sans-serif;}
.search-box::placeholder{color:#aaa;}
.search-box:focus{outline:none;border-color:#1a3a5c;background:white;box-shadow:0 2px 8px rgba(26,58,92,0.12);}
.header-right{display:flex;align-items:center;gap:24px;margin-left:auto;}
.site-title-main{font-size:1.0em;font-weight:600;color:#212121;}
.site-title-sub{font-size:0.82em;color:#757575;}
.contact-info{text-align:right;padding-left:24px;border-left:1px solid #e0e0e0;}
.contact-prompt{font-size:0.78em;color:#757575;margin-bottom:2px;}
.contact-email{font-size:0.85em;color:#1a3a5c;text-decoration:none;font-weight:500;}
.contact-email:hover{text-decoration:underline;}
.breadcrumb{max-width:1200px;margin:0 auto;padding:20px 24px 0;font-size:0.88em;color:#757575;}
.breadcrumb a{color:#1a3a5c;text-decoration:none;}
.breadcrumb a:hover{text-decoration:underline;}
.container{max-width:1200px;margin:0 auto;padding:28px 24px 48px;}
h1{font-family:'Playfair Display',serif;font-size:2.0em;font-weight:700;color:#1a1a2e;margin-bottom:28px;}
footer{text-align:center;margin-top:60px;padding:28px 0;color:#9e9e9e;font-size:0.88em;border-top:1px solid #e8e8e8;}
@media(max-width:768px){body{padding-top:140px;}.nav-container{flex-wrap:wrap;gap:12px;}.header-right{width:100%;justify-content:center;}.search-wrap{max-width:100%;}.contact-info{border-left:none;border-top:1px solid #e0e0e0;padding-left:0;padding-top:12px;text-align:center;}}
"""

# ── MODERN CARD CSS ───────────────────────────────────────────────────────────
CARD_CSS = """
.brochures{display:grid;grid-template-columns:repeat(2,1fr);gap:24px;}
.brochure-card{background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.07);border:1px solid #ebebeb;transition:all 0.3s cubic-bezier(0.4,0,0.2,1);display:flex;flex-direction:column;text-decoration:none;color:inherit;}
.brochure-card:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,0.12);border-color:#d0d0d0;}
.card-hero{position:relative;height:170px;overflow:hidden;background:#1a3a5c;}
.card-hero img{width:100%;height:100%;object-fit:cover;opacity:0.75;transition:opacity 0.3s;}
.brochure-card:hover .card-hero img{opacity:0.85;}
.card-hero-overlay{position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,0.55) 0%,rgba(0,0,0,0.0) 60%);}
.card-season{position:absolute;top:12px;right:12px;font-size:0.68em;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:3px 10px;border-radius:20px;}
.season-winter{background:rgba(2,119,189,0.85);color:#fff;}
.season-summer{background:rgba(230,81,0,0.85);color:#fff;}
.season-allyear{background:rgba(46,125,50,0.85);color:#fff;}
.card-tour-type{position:absolute;top:12px;left:12px;font-size:0.68em;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:3px 10px;border-radius:20px;background:rgba(26,58,92,0.85);color:#fff;}
.card-body{padding:18px 20px 16px;flex:1;display:flex;flex-direction:column;gap:6px;}
.card-title{font-family:'Playfair Display',serif;font-size:1.08em;font-weight:700;color:#1a1a2e;line-height:1.3;}
.card-duration{font-size:0.78em;color:#888;font-weight:500;letter-spacing:0.3px;}
.card-route{font-size:0.80em;color:#555;margin-top:2px;}
.card-desc{font-size:0.80em;color:#666;font-style:italic;line-height:1.5;margin-top:4px;}
.card-price{font-size:0.92em;font-weight:700;color:#1a3a5c;margin-top:auto;padding-top:8px;}
.card-actions{display:flex;gap:8px;padding:0 20px 16px;margin-top:4px;}
.btn-view{flex:1;background:#1a3a5c;color:#fff;border:none;padding:9px 0;border-radius:6px;font-family:'Inter',sans-serif;font-size:0.82em;font-weight:600;letter-spacing:0.5px;cursor:pointer;text-align:center;text-decoration:none;transition:background 0.2s;}
.btn-view:hover{background:#0d2238;}
.btn-pdf{background:transparent;color:#1a3a5c;border:1.5px solid #1a3a5c;padding:9px 14px;border-radius:6px;font-family:'Inter',sans-serif;font-size:0.82em;font-weight:600;cursor:pointer;text-decoration:none;transition:all 0.2s;white-space:nowrap;}
.btn-pdf:hover{background:#f0f4f8;}
.card-valid{font-size:0.73em;padding:0 20px 14px;color:#888;}
.card-valid.expired{color:#e65100;}
.leaflet-tooltip.city-tip{background:transparent!important;border:none!important;box-shadow:none!important;font-size:9px;font-weight:700;color:#1a1a2e;white-space:nowrap;padding:0;text-shadow:-1px -1px 0 white,1px -1px 0 white,-1px 1px 0 white,1px 1px 0 white;}
.leaflet-tooltip.city-tip::before{display:none!important;}
@media(max-width:900px){.brochures{grid-template-columns:1fr;}}
"""

REGION_CSS = """
.categories{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:24px;max-width:1000px;margin:0 auto;}
.category-card{background:white;padding:28px 32px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);transition:all 0.3s cubic-bezier(0.4,0,0.2,1);text-decoration:none;color:inherit;display:block;border:1px solid #f5f5f5;}
.category-card:hover{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,0.12);border-color:#e0e0e0;}
.category-card h2{font-family:'Playfair Display',serif;font-size:1.4em;color:#1a1a2e;margin-bottom:8px;}
.category-meta{font-size:0.82em;color:#757575;margin-bottom:6px;}
.category-types{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;}
.type-tag{font-size:0.72em;font-weight:600;padding:2px 9px;border-radius:12px;background:#eef2f8;color:#1a3a5c;}
.arrow{float:right;color:#1a3a5c;font-size:1.4em;transition:transform 0.2s;}
.category-card:hover .arrow{transform:translateX(4px);}
@media(max-width:768px){.categories{grid-template-columns:1fr;}}
"""

NAV_TPL = """<nav class="top-nav"><div class="nav-container">
<a href="{lh}"><img src="{ls}" alt="Europe Incoming" class="logo"></a>
<div class="search-wrap"><input type="text" class="search-box" placeholder="Search packages — city, country, landmark" id="searchBox"></div>
<div class="header-right">
  <div><div class="site-title-main">Europe Incoming</div><div class="site-title-sub">FIT Packages</div></div>
  <div class="contact-info"><div class="contact-prompt">Can't find what you're looking for? Email us at:</div>
  <a href="mailto:fitsales@europeincoming.com" class="contact-email">fitsales@europeincoming.com</a></div>
</div></div></nav>"""


# ── COORDS ────────────────────────────────────────────────────────────────────
def load_coords_cache():
    cache = dict(SEED_COORDS)
    if os.path.exists(COORDS_CACHE):
        with open(COORDS_CACHE) as f:
            cache.update(json.load(f))
    return cache

def save_coords_cache(cache):
    to_save = {k: v for k, v in cache.items() if k not in SEED_COORDS}
    with open(COORDS_CACHE, 'w') as f:
        json.dump(to_save, f, indent=2)

def geocode_city(city):
    for q in [city, f"{city} Europe"]:
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "EuropeIncomingFIT/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                res = json.loads(r.read())
                if res: return [float(res[0]["lat"]), float(res[0]["lon"])]
            time.sleep(1)
        except: pass
    return None

def get_coords(city, cache):
    if city in cache: return cache[city]
    for k, v in cache.items():
        if k.lower() == city.lower(): return v
    coords = geocode_city(city)
    cache[city] = coords
    time.sleep(1)
    return coords


# ── TITLE / PDF UTILS (unchanged from v10) ───────────────────────────────────
def smart_destination(words):
    if not words: return ""
    if len(words) == 1: return words[0]
    two = ' '.join(words[:2])
    if len(words) == 2:
        return two if two in COMPOUND_NAMES else f"{words[0]} & {words[1]}"
    if len(words) == 3: return f"{words[0]}, {words[1]} & {words[2]}"
    if len(words) == 4: return f"{words[0]}, {words[1]}, {words[2]} & {words[3]}"
    return f"{', '.join(words[:-1])} & {words[-1]}"

def make_title(filename):
    name = re.sub(r'\s+', ' ', filename.replace('.pdf','').replace('_',' ')).strip()
    m = re.search(r'(\d+)\s*nights?,\s*(\d+)\s*days?\s+(.+)', name, re.IGNORECASE)
    if m:
        duration = f"{m.group(1)} nights, {m.group(2)} days"
        rest = m.group(3).strip()
    else:
        m2 = re.search(r'(\d+)\s*nights?\s*[/]?\s*(\d+)\s*days?', name, re.IGNORECASE)
        if m2:
            duration = f"{m2.group(1)} nights, {m2.group(2)} days"
            rest = name[m2.end():].strip()
        else:
            m3 = re.search(r'(\d+)\s*[Dd]ays?\s+(.+)', name, re.IGNORECASE)
            if m3:
                duration = f"{m3.group(1)} days"; rest = m3.group(2).strip()
            else: return name
    rest = re.sub(r'\b(Private|Regular|Self.?[Dd]rive)\b', '', rest, flags=re.IGNORECASE)
    rest = re.sub(r'\d{4}-\d{2,4}', '', rest)
    rest = re.sub(r'Europe\s+Incoming', '', rest, flags=re.IGNORECASE)
    rest = re.sub(r'\s+', ' ', rest).strip().strip('-').strip()
    return f"{duration} {smart_destination(rest.split())}".strip()

def parse_date(d):
    for fmt in ['%d.%m.%Y','%d.%m.%y','%d/%m/%Y','%d/%m/%y']:
        try: return datetime.strptime(d, fmt)
        except: pass
    return None

def detect_seasons(date_pairs):
    SUMMER={4,5,6,7,8,9,10}; WINTER={11,12,1,2,3}; hs=hw=False
    for s,e in date_pairs:
        sd=parse_date(s); ed=parse_date(e)
        if sd and ed:
            if sd.month in SUMMER or ed.month in SUMMER: hs=True
            if sd.month in WINTER or ed.month in WINTER: hw=True
    if hs and hw: return "all-year"
    elif hs: return "summer"
    elif hw: return "winter"
    return "all-year"

def extract_price(txt, lines):
    currency = "£" if ("£" in txt and "€" not in txt) else "€"
    amt_pattern = r'[€£]\s*([\d,]+)'
    if re.search(r'Min\s*Pax', txt, re.IGNORECASE):
        section = re.search(r'Min\s*Pax.*?(?:Sample Hotels|Terms)', txt, re.DOTALL|re.IGNORECASE)
        if section:
            amounts = re.findall(amt_pattern, section.group(0))
            prices = [int(a.replace(',','')) for a in amounts if int(a.replace(',',''))>500]
            return (min(prices), currency) if prices else (None, currency)
        return (None, currency)
    ti = next((i for i,l in enumerate(lines) if 'Twin' in l and 'Do' in l), None)
    if ti:
        ep=[]
        for l in lines[ti:ti+30]:
            m=re.match(amt_pattern,l)
            if m: ep.append(int(m.group(1).replace(',','')))
        twins=ep[1::3] if len(ep)>=3 else ep[1:2] if len(ep)>=2 else []
        return (min(twins),currency) if twins else (None,currency)
    return (None,currency)

def extract_pdf_data(pdf_path, filename):
    r={"duration":None,"tour_type":None,"cities":[],"price_twin":None,"currency":"€","season":"all-year","valid_till":None,"is_expired":False,"includes":[]}
    name=filename.replace('_',' ')
    dur=re.search(r'(\d+)\s*nights?\s*/?,?\s*(\d+)\s*days?',name,re.IGNORECASE)
    if dur: r["duration"]=f"{dur.group(1)} nights / {dur.group(2)} days"
    else:
        d=re.search(r'(\d+)\s*days?',name,re.IGNORECASE)
        if d: r["duration"]=f"{d.group(1)} days"
    t=re.search(r'(Self.?[Dd]rive|Private|Regular)',name)
    if t: r["tour_type"]=t.group(1).replace('-',' ').title()
    try:
        doc=fitz.open(pdf_path); txt="\n".join(p.get_text() for p in doc)
        lines=[l.strip() for l in txt.split('\n')]
        oc=re.findall(r'Overnight in ([A-Z][a-zA-Z\s]+?)[\.\n,]',txt)
        r["cities"]=list(dict.fromkeys([c.strip() for c in oc]))[:6]
        all_dates_raw=re.findall(r'\b(\d{2}[./]\d{2}[./]\d{2,4})\b',txt)
        valid_dates=[(d,parse_date(d)) for d in all_dates_raw if parse_date(d)]
        if valid_dates:
            strs=[v[0] for v in valid_dates]; objs=[v[1] for v in valid_dates]
            dp=[(strs[i],strs[i+1]) for i in range(0,len(strs)-1,2)]
            if dp: r["season"]=detect_seasons(dp)
            latest=max(objs); r["valid_till"]=latest.strftime("%b %Y"); r["is_expired"]=latest<datetime.now()
        price,currency=extract_price(txt,lines)
        r["price_twin"]=price; r["currency"]=currency
        im=re.search(r'price includes:(.*?)(?:Sample Tours|Terms|Sample Hotels)',txt,re.DOTALL|re.IGNORECASE)
        if im:
            il=[l.strip().lstrip('•').strip() for l in im.group(1).split('\n') if l.strip() and len(l.strip())>5]
            r["includes"]=il[:3]
    except Exception as e: print(f"  WARNING {filename}: {e}")
    return r

def extract_itinerary(pdf_path):
    try:
        doc=fitz.open(pdf_path); txt="\n".join(p.get_text() for p in doc)
        m=re.search(r'(Day\s*1\s*[,:\-\s].+?)(?:This package price includes|Sample Tours|Terms\s*[&\n]|Sample Hotels|$)',txt,re.DOTALL|re.IGNORECASE)
        if m:
            raw=m.group(1).strip()
            raw=re.sub(r'Optional:.*?(?=Day\s*\d|$)','',raw,flags=re.DOTALL)
            return re.sub(r'\s+',' ',raw).strip()[:1500]
    except: pass
    return ""

def generate_description(cities, region, tour_type, season, pdf_path, cached_desc=None):
    FALLBACK=["Curated","The best of","elegance meets","unmissable stops","handpicked experiences","curated and ready"]
    if cached_desc and not any(m in cached_desc for m in FALLBACK):
        return cached_desc
    itinerary=extract_itinerary(pdf_path)
    if not GITHUB_TOKEN or not itinerary:
        return _fallback_desc(cities,region,tour_type)
    season_hint="" if season=="all-year" else f"This is a {'winter' if season=='winter' else 'summer'} package. "
    prompt=(f"Tour itinerary:\n{itinerary}\n\n{season_hint}"
            "Write ONE punchy sentence (max 12 words) capturing the ESSENCE of this specific tour. "
            "Don't list city names. Don't say 'explore' or 'journey'. Vivid and specific. Just the sentence.")
    payload=json.dumps({"model":"gpt-4o-mini","messages":[
        {"role":"system","content":"You write punchy one-sentence travel vibes. Specific, sensory. Never generic. Never list city names. Good examples: 'Cliffside drives, Bronze Age towers and Neptune's hidden sea caves.' 'D-Day beaches, Loire chateaux and Montmartre twilight strolls.'"},
        {"role":"user","content":prompt}],"max_tokens":80,"temperature":0.9}).encode()
    try:
        req=urllib.request.Request("https://models.inference.ai.azure.com/chat/completions",data=payload,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {GITHUB_TOKEN}"})
        with urllib.request.urlopen(req,timeout=20) as r:
            desc=json.loads(r.read())["choices"][0]["message"]["content"].strip().strip('"')
            time.sleep(2); return desc
    except: return _fallback_desc(cities,region,tour_type)

def _fallback_desc(cities,region,tour_type):
    if not cities: return f"Curated {region} package with handpicked experiences."
    if len(cities)==1: return f"The best of {cities[0]}, curated and ready to explore."
    elif len(cities)==2: return f"{cities[0]} elegance meets {cities[1]} charm."
    return f"{cities[0]}, {cities[1]} and {len(cities)-2} more unmissable stops."


# ── MAP JS ────────────────────────────────────────────────────────────────────
def make_map_js(map_id, cities, coords_cache):
    points=[]
    for city in cities:
        c=get_coords(city,coords_cache)
        if c: points.append([c[0],c[1],city])
    if not points: return ""
    cjs=json.dumps(points)
    return f"""(function(){{var pts={cjs};if(!pts.length)return;
  var lats=pts.map(p=>p[0]),lngs=pts.map(p=>p[1]),pad=0.4;
  var bounds=[[Math.min(...lats)-pad,Math.min(...lngs)-pad],[Math.max(...lats)+pad,Math.max(...lngs)+pad]];
  var map=L.map('{map_id}',{{zoomControl:false,scrollWheelZoom:false,dragging:false,touchZoom:false,doubleClickZoom:false,boxZoom:false,keyboard:false,attributionControl:false}});
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{maxZoom:13}}).addTo(map);
  map.fitBounds(bounds,{{padding:[10,10]}});
  if(pts.length>1)L.polyline(pts.map(p=>[p[0],p[1]]),{{color:'#1a3a5c',weight:2,dashArray:'5,4',opacity:0.8}}).addTo(map);
  pts.forEach((p,i)=>{{
    var color=i===0?'#e53935':(i===pts.length-1?'#43a047':'#1a3a5c');
    L.circleMarker([p[0],p[1]],{{radius:5,fillColor:color,color:'white',weight:2,fillOpacity:1}}).addTo(map)
     .bindTooltip(p[2],{{permanent:true,direction:'top',className:'city-tip',offset:[0,-5]}});
  }});
}})();"""


# ── MODERN CARD ───────────────────────────────────────────────────────────────
def make_brochure_card(pdf_filename, pdf_data, title, description, map_id, coords_cache, brochure_page=None):
    tt     = pdf_data.get("tour_type","")
    dur    = pdf_data.get("duration","")
    cities = pdf_data.get("cities",[])
    price  = pdf_data.get("price_twin")
    curr   = pdf_data.get("currency","€")
    season = pdf_data.get("season","all-year")
    valid  = pdf_data.get("valid_till")
    exp    = pdf_data.get("is_expired",False)
    img    = get_card_image(cities)

    season_cls  = {"winter":"season-winter","summer":"season-summer"}.get(season,"season-allyear")
    season_lbl  = {"winter":"❄️ Winter","summer":"☀️ Summer"}.get(season,"🌍 All Year")
    route       = " → ".join(cities) if cities else ""
    price_html  = f'<div class="card-price">From {curr}{price:,} pp</div>' if price else ""
    valid_html  = f'<div class="card-valid{" expired" if exp else ""}">{"⚠️ Expired" if exp else "✓ Valid till"} {valid}</div>' if valid else ""

    view_btn = (f'<a href="{brochure_page}" class="btn-view">View Package</a>'
                if brochure_page else '<span class="btn-view" style="opacity:0.4;cursor:default">View Package</span>')
    pdf_btn  = f'<a href="{pdf_filename}" class="btn-pdf" target="_blank">↓ PDF</a>'

    return f"""<div class="brochure-card">
  <div class="card-hero">
    <img src="{img}" alt="{title}" loading="lazy">
    <div class="card-hero-overlay"></div>
    {f'<div class="card-tour-type">{tt}</div>' if tt else ''}
    <div class="card-season {season_cls}">{season_lbl}</div>
  </div>
  <div class="card-body">
    <div class="card-title">{title}</div>
    {f'<div class="card-duration">🕐 {dur}</div>' if dur else ''}
    {f'<div class="card-route">📍 {route}</div>' if route else ''}
    {f'<div class="card-desc">{description}</div>' if description else ''}
    {price_html}
  </div>
  {valid_html}
  <div class="card-actions">{view_btn}{pdf_btn}</div>
</div>"""


# ── REGION CARD ───────────────────────────────────────────────────────────────
def make_region_card(slug, display_name, pkg_count, tour_types):
    types_html=''.join(f'<span class="type-tag">{t}</span>' for t in tour_types)
    return f"""<a href="{slug}/" class="category-card">
  <span class="arrow">→</span>
  <h2>{display_name}</h2>
  <div class="category-meta">{pkg_count} package{'s' if pkg_count!=1 else ''}</div>
  <div class="category-types">{types_html}</div>
</a>"""


# ── PACKAGE PAGE (products/*.json + prices/*.json) ───────────────────────────
# Replaces the old mark12-fetch brochure pipeline. Each product JSON is paired
# with a prices JSON (product["pricesFile"]); rebuild_site.py renders one
# static HTML page per product using PACKAGE_PAGE_CSS + assets/package-page.js.
# Editing only the prices file updates that product's page on next rebuild.

PRODUCTS_DIR = os.path.join(REPO_ROOT, "products")
PRICES_DIR   = os.path.join(REPO_ROOT, "prices")

PACKAGE_PAGE_CSS = """
:root{--navy:#0B1733;--gold:#F2B91D;--gold-hover:#E0A810;--gold-dark:#B8870A;
--ink:#1A1D2E;--body:#4B5563;--muted:#6B7280;--faint:#9AA1AE;--line:#E5E7EC;
--faint-line:#F2F4F7;--offwhite:#FAFAF8;--green:#1F8A5B;--green-bg:#EEF5F0;
--taste-bg:#FEF7DC;--exp-bg:#EEF1F8;--shop-bg:#F2F4F7;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Open Sans',Arial,sans-serif;color:var(--ink);background:#fff;line-height:1.6;padding-top:64px;}
a{color:inherit;}
.pkg-wrap{max-width:1200px;margin:0 auto;padding:0 48px;}

/* Top bar */
.pkg-topbar{position:fixed;top:0;left:0;right:0;height:64px;background:#fff;border-bottom:1px solid var(--line);z-index:300;}
.pkg-topbar-inner{max-width:1200px;margin:0 auto;height:100%;padding:0 48px;display:flex;align-items:center;justify-content:space-between;gap:24px;}
.pkg-topbar-left{display:flex;align-items:center;gap:20px;}
.pkg-logo{height:38px;width:auto;display:block;}
.pkg-back-link{font-size:13px;font-weight:600;color:var(--body);text-decoration:none;transition:color .22s cubic-bezier(.22,.61,.36,1);}
.pkg-back-link:hover{color:var(--navy);}
.pkg-topbar-right{display:flex;align-items:center;gap:20px;}
.pkg-trade{font-size:12px;color:var(--muted);}
.pkg-trade a{color:var(--navy);font-weight:600;text-decoration:none;}
.pkg-dl-btn{background:var(--gold);color:var(--navy);border:none;padding:11px 20px;border-radius:6px;font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;transition:background .22s cubic-bezier(.22,.61,.36,1);white-space:nowrap;}
.pkg-dl-btn:hover{background:var(--gold-hover);}

/* Hero */
.pkg-hero{position:relative;height:420px;background:var(--navy);overflow:hidden;}
.pkg-hero-img{position:absolute;inset:0;background-size:cover;background-position:center;opacity:.65;}
.pkg-hero-overlay{position:absolute;inset:0;background:linear-gradient(to top,rgba(3,7,20,.75),rgba(3,7,20,.05) 65%);}
.pkg-hero-content{position:absolute;left:0;right:0;bottom:0;max-width:1200px;margin:0 auto;padding:0 48px 32px;}
.pkg-eyebrow{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);margin-bottom:10px;}
.pkg-hero-title{font-family:'Montserrat',sans-serif;font-size:56px;font-weight:900;letter-spacing:.01em;text-transform:uppercase;color:#fff;line-height:1.05;margin-bottom:12px;}
.pkg-hero-meta{display:flex;align-items:center;gap:14px;font-size:13px;color:rgba(255,255,255,.85);}
.pkg-hero-meta .sep{width:1px;height:12px;background:rgba(255,255,255,.3);}
.pkg-hero-price{color:var(--gold);font-weight:700;}

/* Variant bar */
.pkg-variantbar{position:sticky;top:64px;z-index:290;background:#fff;border-bottom:1px solid var(--line);}
.pkg-variantbar-inner{max-width:1200px;margin:0 auto;padding:14px 48px;display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;}
.pkg-variantbar-left{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.pkg-variant-label{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}
.pkg-pills{display:flex;gap:8px;flex-wrap:wrap;}
.pkg-pill{font-family:'Montserrat',sans-serif;font-size:12px;font-weight:700;letter-spacing:.03em;padding:8px 18px;border-radius:999px;border:1px solid #CBD0DA;background:#fff;color:var(--body);cursor:pointer;transition:background .22s cubic-bezier(.22,.61,.36,1),color .22s cubic-bezier(.22,.61,.36,1),border-color .22s cubic-bezier(.22,.61,.36,1);}
.pkg-pill.active{background:var(--navy);color:#fff;border-color:var(--navy);}
.pkg-variant-blurb{font-size:13px;color:var(--muted);text-align:right;}

/* Body columns */
.pkg-body{max-width:1200px;margin:0 auto;padding:0 48px;display:flex;gap:48px;align-items:flex-start;}
.pkg-main{flex:1;min-width:0;padding:36px 0;}
.pkg-sidebar{width:300px;flex-shrink:0;position:sticky;top:132px;padding:36px 0;}

.pkg-section{margin-bottom:40px;}
.pkg-section-label{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding-bottom:8px;margin-bottom:18px;border-bottom:1px solid var(--line);}

/* Day by day */
.pkg-day{display:grid;grid-template-columns:56px 1fr;gap:18px;padding:20px 0;border-bottom:1px solid var(--faint-line);}
.pkg-day:first-child{border-top:1px solid var(--faint-line);}
.pkg-day-num-col{text-align:center;}
.pkg-day-num-lbl{font-family:'Montserrat',sans-serif;font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:2px;}
.pkg-day-num{font-family:'Montserrat',sans-serif;font-size:34px;font-weight:900;color:var(--navy);line-height:1;}
.pkg-day-title{font-family:'Montserrat',sans-serif;font-size:16px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;color:var(--ink);margin-bottom:4px;}
.pkg-day-overnight{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gold-dark);margin-bottom:8px;}
.pkg-day-desc{font-size:14px;color:var(--body);line-height:1.75;margin-bottom:10px;}
.pkg-pill-row{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px;margin-top:6px;}
.pkg-tag{flex:0 0 auto;font-family:'Montserrat',sans-serif;font-size:10px;font-weight:700;letter-spacing:.05em;padding:4px 10px;border-radius:4px;white-space:nowrap;}
.pkg-tag-inc{background:var(--green-bg);color:var(--green);}
.pkg-tag-taste{background:var(--taste-bg);color:var(--gold-dark);}
.pkg-tag-exp{background:var(--exp-bg);color:var(--navy);}
.pkg-tag-shop{background:var(--shop-bg);color:var(--body);}
.pkg-tag-text{flex:1 1 220px;min-width:0;font-size:13px;color:var(--body);}

/* Includes */
.pkg-inc-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px;}
.pkg-inc-item{font-size:13.5px;color:var(--body);display:flex;gap:8px;align-items:flex-start;}
.pkg-check{color:var(--green);font-weight:700;}

/* Hotels */
.pkg-hotels-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden;}
.pkg-hotel-card{background:#fff;padding:18px;}
.pkg-hotel-city{font-family:'Montserrat',sans-serif;font-size:14px;font-weight:700;color:var(--ink);}
.pkg-hotel-nights{font-size:12px;color:var(--muted);margin-bottom:10px;}
.pkg-hotel-cat{font-family:'Montserrat',sans-serif;font-size:10px;font-weight:700;letter-spacing:.05em;color:var(--navy);margin-top:6px;}
.pkg-hotel-name{font-size:13px;color:var(--body);}

/* Rates */
.pkg-rate-toggles{display:flex;gap:24px;margin-bottom:18px;flex-wrap:wrap;}
.pkg-seg-group{display:inline-flex;border:1px solid var(--line);border-radius:6px;overflow:hidden;}
.pkg-seg{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.04em;padding:8px 16px;border:none;background:#fff;color:var(--body);cursor:pointer;transition:background .22s cubic-bezier(.22,.61,.36,1),color .22s cubic-bezier(.22,.61,.36,1);}
.pkg-seg.active{background:var(--navy);color:#fff;}
.pkg-rate-table{width:100%;border-collapse:collapse;margin-bottom:10px;}
.pkg-rate-table th{background:var(--navy);color:#fff;font-family:'Montserrat',sans-serif;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;text-align:left;padding:10px 16px;}
.pkg-rate-table td{padding:11px 16px;font-size:13.5px;border-bottom:1px solid var(--line);}
.pkg-rate-table td:last-child{text-align:right;font-weight:700;color:var(--navy);}
.pkg-pax-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:10px;}
.pkg-pax-season-label{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;}
.pkg-pax-table{width:100%;border-collapse:collapse;}
.pkg-pax-table th{background:var(--navy);color:#fff;font-family:'Montserrat',sans-serif;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;text-align:left;padding:8px 12px;}
.pkg-pax-table td{padding:8px 12px;font-size:13px;border-bottom:1px solid var(--line);}
.pkg-pax-table td:not(:first-child){text-align:right;font-weight:700;color:var(--navy);}
.pkg-rate-note{font-size:12px;color:var(--muted);font-style:italic;}
@media(max-width:960px){.pkg-pax-grid{grid-template-columns:1fr;}}

/* Optional tours */
.pkg-opt-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 24px;}
.pkg-opt-item{display:flex;justify-content:space-between;gap:12px;font-size:13.5px;padding:8px 0;border-bottom:1px solid var(--faint-line);}
.pkg-opt-price{font-weight:700;color:var(--ink);white-space:nowrap;}

/* Good to know */
.pkg-gtk-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px 24px;}
.pkg-gtk-title{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--gold-dark);margin-bottom:6px;}
.pkg-gtk-body{font-size:13px;color:var(--body);line-height:1.6;}

/* T&C accordion */
.pkg-tc-btn{width:100%;display:flex;justify-content:space-between;align-items:center;background:var(--faint-line);border:1px solid var(--line);border-radius:6px;padding:14px 18px;font-family:'Montserrat',sans-serif;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--ink);cursor:pointer;}
.pkg-tc-body{display:none;padding:16px 4px 4px;}
.pkg-tc-body.open{display:block;}
.pkg-tc-body li{font-size:12.5px;color:var(--body);padding:6px 0;list-style:disc;margin-left:18px;}

/* Sidebar */
.pkg-sb-card{background:var(--offwhite);border:1px solid var(--line);border-radius:10px;padding:22px;margin-bottom:20px;}
.pkg-sb-title{font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gold-dark);margin-bottom:14px;}
.pkg-map-box{position:relative;height:180px;border-radius:8px;overflow:hidden;margin-bottom:16px;background:var(--faint-line);cursor:zoom-in;}
.pkg-map-box #pkgMapSmall{pointer-events:none;}
.pkg-map-enlarge{position:absolute;right:8px;bottom:8px;z-index:10;background:var(--navy);color:#fff;font-size:10px;font-weight:700;letter-spacing:.04em;padding:5px 10px;border-radius:4px;cursor:zoom-in;border:none;font-family:'Montserrat',sans-serif;pointer-events:none;}
.pkg-fact-row{padding:9px 0;border-bottom:1px solid var(--line);}
.pkg-fact-row:last-child{border-bottom:none;}
.pkg-fact-title{font-size:13px;font-weight:600;color:var(--ink);}
.pkg-fact-body{font-size:12px;color:var(--muted);margin-top:2px;}
.pkg-sb-quote{background:var(--navy);}
.pkg-sb-quote .pkg-sb-title{color:var(--gold);}
.pkg-sb-quote-body{font-size:13px;color:rgba(255,255,255,.8);margin-bottom:16px;line-height:1.6;}
.pkg-sb-quote-btn{display:block;text-align:center;width:100%;background:var(--gold);color:var(--navy);font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:12px;border-radius:6px;text-decoration:none;transition:background .22s cubic-bezier(.22,.61,.36,1);}
.pkg-sb-quote-btn:hover{background:var(--gold-hover);}
.pkg-sb-footer{background:var(--navy);color:rgba(255,255,255,.55);font-size:12px;padding:20px 0;text-align:center;}

/* Map markers */
.pkg-badge-icon{background:transparent;border:none;}
.pkg-badge{background:var(--navy);color:#fff;border-radius:50%;text-align:center;font-family:'Montserrat',sans-serif;font-weight:700;box-shadow:0 0 0 2px var(--gold);}
.leaflet-tooltip.pkg-map-tip{background:transparent!important;border:none!important;box-shadow:none!important;font-family:'Montserrat',sans-serif;font-size:10px;font-weight:700;color:var(--navy);white-space:nowrap;padding:0!important;text-shadow:-1px -1px 0 #fff,1px -1px 0 #fff,-1px 1px 0 #fff,1px 1px 0 #fff;}
.leaflet-tooltip.pkg-map-tip::before{display:none!important;}

/* Map modal */
.pkg-map-modal{display:none;position:fixed;inset:0;background:rgba(11,23,51,.65);z-index:1000;align-items:center;justify-content:center;}
.pkg-map-modal.open{display:flex;}
.pkg-map-modal-panel{background:#fff;border-radius:10px;box-shadow:0 24px 64px rgba(11,23,51,.35);width:min(960px,100%);height:min(640px,100%);display:flex;flex-direction:column;overflow:hidden;}
.pkg-map-modal-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--line);}
.pkg-map-modal-header h3{font-family:'Montserrat',sans-serif;font-size:13px;font-weight:700;letter-spacing:.06em;color:var(--ink);}
.pkg-map-modal-close{background:none;border:none;font-size:18px;color:var(--muted);cursor:pointer;line-height:1;}
.pkg-map-modal-canvas{flex:1;}

@media(max-width:960px){
  .pkg-body{flex-direction:column;}
  .pkg-sidebar{width:100%;position:static;}
  .pkg-hero-title{font-size:38px;}
  .pkg-inc-grid,.pkg-opt-grid,.pkg-gtk-grid,.pkg-hotels-grid{grid-template-columns:1fr;}
}

@media print{
  .no-print{display:none!important;}
  body{padding-top:0;}
  .pkg-body{display:block;padding:0;max-width:none;}
  .pkg-main{padding:16px 0;}
  .pkg-hero{height:auto;}
}
"""

def _cheapest_twin(prices, style_id):
    variant = (prices.get("variants") or {}).get(style_id) or {}
    best = None
    if "paxTiers" in variant:
        for tiers in variant["paxTiers"].values():
            for tier in tiers or []:
                val = tier.get("3star")
                if val is not None and (best is None or val < best):
                    best = val
        return best
    for cat_rates in variant.values():
        for row in (cat_rates or {}).values():
            twin = row.get("twin")
            if twin is not None and (best is None or twin < best):
                best = twin
    return best

def _fmt_money(val, curr):
    if val is None: return "—"
    return f"{curr}{val:,.0f}"

def render_package_page(product, prices, depth, back_href):
    """Render one static package page. depth = folder depth for relative asset paths."""
    root_rel = "../" * depth
    logo_src = root_rel + "logo.png"
    js_src   = root_rel + "assets/package-page.js"
    title    = product.get("title", "")
    style_keys = list(product.get("styles", {}).keys())
    first_style = style_keys[0] if style_keys else ""
    currency = prices.get("currency", "€")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} | Europe Incoming FIT Packages</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;900&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>{PACKAGE_PAGE_CSS}</style>
{LEAFLET_HEAD}{GA}
</head>
<body>
{GEO_BLOCK}
<div class="pkg-topbar no-print"><div class="pkg-topbar-inner">
  <div class="pkg-topbar-left">
    <a href="{root_rel}"><img class="pkg-logo" src="{logo_src}" alt="Europe Incoming"></a>
    <a class="pkg-back-link" href="{back_href}">← All packages</a>
  </div>
  <div class="pkg-topbar-right">
    <div class="pkg-trade">Trade enquiries / <a href="mailto:fitsales@europeincoming.com">fitsales@europeincoming.com</a></div>
    <button class="pkg-dl-btn" id="pkgDownloadBtn">↓ DOWNLOAD PDF</button>
  </div>
</div></div>

<div class="pkg-hero">
  <div class="pkg-hero-img" id="pkgHeroImg"></div>
  <div class="pkg-hero-overlay"></div>
  <div class="pkg-hero-content">
    <div class="pkg-eyebrow" id="pkgEyebrow"></div>
    <h1 class="pkg-hero-title" id="pkgHeroTitle"></h1>
    <div class="pkg-hero-meta">
      <span id="pkgHeroNights"></span><span class="sep"></span>
      <span id="pkgHeroRoute"></span><span class="sep"></span>
      <span class="pkg-hero-price" id="pkgHeroPrice"></span>
    </div>
  </div>
</div>

<div class="pkg-variantbar no-print"><div class="pkg-variantbar-inner">
  <div class="pkg-variantbar-left">
    <div class="pkg-variant-label">Travel style</div>
    <div class="pkg-pills" id="pkgVariantPills"></div>
  </div>
  <div class="pkg-variant-blurb" id="pkgVariantBlurb"></div>
</div></div>

<div class="pkg-body">
  <div class="pkg-main">
    <div class="pkg-section">
      <div class="pkg-section-label" id="pkgDayHeading"></div>
      <div id="pkgDays"></div>
    </div>
    <div class="pkg-section">
      <div class="pkg-section-label" id="pkgIncludesHeading"></div>
      <div class="pkg-inc-grid" id="pkgIncludes"></div>
    </div>
    <div class="pkg-section">
      <div class="pkg-section-label">Sample hotels</div>
      <div class="pkg-hotels-grid" id="pkgHotels"></div>
    </div>
    <div class="pkg-section">
      <div class="pkg-section-label">Package rates</div>
      <div class="pkg-rate-toggles no-print" id="pkgRateToggles">
        <div class="pkg-seg-group" id="pkgCatToggle"></div>
        <div class="pkg-seg-group" id="pkgSeasonToggle"></div>
      </div>
      <table class="pkg-rate-table" id="pkgRateTable">
        <thead><tr><th>Category</th><th style="text-align:right">Rate per person</th></tr></thead>
        <tbody id="pkgRatesBody"></tbody>
      </table>
      <div class="pkg-pax-grid" id="pkgPaxRates"></div>
      <div class="pkg-rate-note">All rates net, per person, in {currency}. Valid {prices.get("validFrom","")} – {prices.get("validTo","")}.</div>
    </div>
    <div class="pkg-section">
      <div class="pkg-section-label">Optional tours &amp; extras</div>
      <div class="pkg-opt-grid" id="pkgOptionals"></div>
    </div>
    <div class="pkg-section">
      <div class="pkg-section-label">Good to know</div>
      <div class="pkg-gtk-grid" id="pkgGoodToKnow"></div>
    </div>
    <div class="pkg-section pkg-tc-wrap no-print">
      <button class="pkg-tc-btn" id="pkgTcBtn"><span>Terms &amp; conditions</span><span id="pkgTcArrow">▼</span></button>
      <div class="pkg-tc-body" id="pkgTcBody"><ul id="pkgTerms"></ul></div>
    </div>
  </div>

  <div class="pkg-sidebar no-print">
    <div class="pkg-sb-card">
      <div class="pkg-sb-title">About this tour</div>
      <div class="pkg-map-box" id="pkgMapBox">
        <div id="pkgMapSmall" style="height:100%;"></div>
        <button class="pkg-map-enlarge" id="pkgMapEnlarge">⤢ ENLARGE</button>
      </div>
      <div class="pkg-fact-row">
        <div class="pkg-fact-title" id="pkgAboutDuration"></div>
        <div class="pkg-fact-body" id="pkgAboutRoute"></div>
      </div>
      <div id="pkgAboutFacts"></div>
    </div>
    <div class="pkg-sb-card pkg-sb-quote">
      <div class="pkg-sb-title">Ready to quote?</div>
      <div class="pkg-sb-quote-body">Get in touch with the FIT team for availability and a tailored quotation.</div>
      <a class="pkg-sb-quote-btn" href="mailto:fitsales@europeincoming.com?subject=Quote request — {title}">Email the FIT team</a>
    </div>
  </div>
</div>

<div class="pkg-sb-footer no-print">Europe Incoming Holdings Ltd · Company Reg. England &amp; Wales 07053949 · <a href="mailto:fitsales@europeincoming.com" style="color:inherit">fitsales@europeincoming.com</a></div>

<div class="pkg-map-modal no-print" id="pkgMapModal">
  <div class="pkg-map-modal-panel">
    <div class="pkg-map-modal-header">
      <h3 id="pkgMapModalTitle"></h3>
      <button class="pkg-map-modal-close" id="pkgMapModalClose">✕</button>
    </div>
    <div class="pkg-map-modal-canvas" id="pkgMapModalCanvas"></div>
  </div>
</div>

<script>
window.PRODUCT = {json.dumps(product)};
window.PRICES = {json.dumps(prices)};
</script>
<script src="{js_src}"></script>
</body></html>"""


def make_package_card(product, prices, out_filename):
    style_keys = list(product.get("styles", {}).keys())
    first_style = style_keys[0] if style_keys else ""
    style = product.get("styles", {}).get(first_style, {})
    price = _cheapest_twin(prices, first_style)
    curr = prices.get("currency", "€")
    cities = [p.get("label") for p in (product.get("map") or {}).get("points", []) if p.get("nights", 0) > 0]
    img = get_card_image(cities)
    title = product.get("title", "").rstrip(".")
    price_html = f'<div class="card-price">From {_fmt_money(price, curr)} pp</div>' if price else ""
    return f"""<div class="brochure-card">
  <div class="card-hero">
    <img src="{img}" alt="{title}" loading="lazy">
    <div class="card-hero-overlay"></div>
  </div>
  <div class="card-body">
    <div class="card-title">{title}</div>
    <div class="card-duration">🕐 {style.get("nights","")}</div>
    <div class="card-route">📍 {style.get("route","")}</div>
    {price_html}
  </div>
  <div class="card-actions">
    <a href="{out_filename}" class="btn-view">View Package</a>
  </div>
</div>"""


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_products():
    products = []
    if not os.path.isdir(PRODUCTS_DIR):
        return products
    for fname in sorted(os.listdir(PRODUCTS_DIR)):
        if not fname.endswith(".json"): continue
        product = load_json(os.path.join(PRODUCTS_DIR, fname))
        products.append(product)
    return products


# ── INDEX BUILDERS ────────────────────────────────────────────────────────────
def build_brochure_index(title, breadcrumb, cards_html, maps_js, logo_src, logo_href, search_js):
    nav = NAV_TPL.format(lh=logo_href, ls=logo_src)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} | Europe Incoming</title>
{GF_FONTS}<style>{BASE_CSS}{CARD_CSS}</style>
{LEAFLET_HEAD}{GA}
</head>
<body>
{GEO_BLOCK}{nav}
<div class="breadcrumb">{breadcrumb}</div>
<div class="container">
<h1>{title}</h1>
<div class="brochures" id="brochuresList">{cards_html}</div>
<footer><p>Browse packages below and click View Package for full details.</p></footer>
</div>
<script src="{search_js}"></script>
<script>window.addEventListener('load',function(){{{maps_js}}});</script>
</body></html>"""

def build_multicountry_index(region_cards_html, logo_href, search_js):
    nav = NAV_TPL.format(lh=logo_href, ls=logo_href+"logo.png")
    breadcrumb = f'<a href="{logo_href}">Home</a> › Multi-City & Country Packages'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Multi-City & Country Packages | Europe Incoming</title>
{GF_FONTS}<style>{BASE_CSS}{REGION_CSS}</style>{GA}
</head>
<body>
{GEO_BLOCK}{nav}
<div class="breadcrumb">{breadcrumb}</div>
<div class="container">
<h1>Multi-City & Country Packages</h1>
<div class="categories" id="categoriesList">{region_cards_html}</div>
<footer><p>All packages available with full details and PDF download.</p></footer>
</div>
<script src="{search_js}"></script>
</body></html>"""


# ── PACKAGES JSON ─────────────────────────────────────────────────────────────
def load_existing_packages(packages_path):
    existing={}
    if os.path.exists(packages_path):
        with open(packages_path) as f:
            for pkg in json.load(f).get("packages",[]):
                existing[pkg.get("folder","")+"/"+pkg.get("filename","")]=pkg
    return existing

def update_packages_json(packages_path, all_found, desc_cache):
    existing=load_existing_packages(packages_path)
    new_pkgs=[]
    for item in all_found:
        key=item["folder"]+"/"+item["filename"]
        if key in existing:
            pkg=existing[key].copy()
            pkg["description"]=desc_cache.get(key,pkg.get("description",""))
            new_pkgs.append(pkg)
        else:
            pd=item["pdf_data"]
            new_pkgs.append({
                "id":re.sub(r'[^a-z0-9]','-',item["filename"].lower().replace('.pdf',''))[:30],
                "name":item["title"],"filename":item["filename"],
                "region":item["region"],"folder":item["folder"],
                "cities":pd.get("cities",[]),"duration":pd.get("duration",""),
                "type":pd.get("tour_type",""),"season":pd.get("season","all-year"),
                "price_twin":pd.get("price_twin"),"currency":pd.get("currency","€"),
                "valid_till":pd.get("valid_till"),"description":desc_cache.get(key,""),"tags":pd.get("cities",[])
            })
    with open(packages_path,'w') as f:
        json.dump({"packages":new_pkgs},f,indent=2)
    print(f"  packages.json: {len(new_pkgs)} entries")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    packages_path = os.path.join(REPO_ROOT, "packages.json")
    all_found=[];region_stats={};desc_cache={}
    coords_cache=load_coords_cache();coords_dirty=False
    existing_pkgs=load_existing_packages(packages_path)

    # ── Load products/*.json (paired prices/*.json) ──────────────────────────
    products = load_products()

    # ── PDF loop: city-break only. Multi-country uses products/*.json ────────
    for folder_rel, config in FOLDER_CONFIG.items():
        folder_abs=os.path.join(REPO_ROOT,folder_rel)
        if not os.path.isdir(folder_abs): continue
        # Skip multi-country folders - handled by the products/*.json loop below
        if folder_rel.startswith("multi-country"):
            continue
        pdfs=sorted([f for f in os.listdir(folder_abs) if f.lower().endswith('.pdf')])
        if not pdfs: continue
        print(f"\n{folder_rel} — {len(pdfs)} PDFs")
        depth=config["depth"]
        logo_src="../"*depth+"logo.png"
        logo_href="../"*depth
        search_js="../"*depth+"global-search.js"
        breadcrumb=(f'<a href="../">Home</a> › {config["breadcrumb"]}' if depth==1
                    else f'<a href="../../">Home</a> › <a href="../">Multi-Country</a> › {config["breadcrumb"]}')
        cards=[];maps_js_parts=[];tour_types_seen=[]

        for idx,pdf in enumerate(pdfs):
            print(f"  {pdf}")
            pkg_key=folder_rel+"/"+pdf
            pdf_data=extract_pdf_data(os.path.join(folder_abs,pdf),pdf)
            title=make_title(pdf)
            cached_desc=existing_pkgs.get(pkg_key,{}).get("description",None)
            desc=generate_description(pdf_data.get("cities",[]),config["region"],
                pdf_data.get("tour_type",""),pdf_data.get("season","all-year"),
                os.path.join(folder_abs,pdf),cached_desc)
            desc_cache[pkg_key]=desc

            for city in pdf_data.get("cities",[]):
                was_missing=city not in coords_cache
                get_coords(city,coords_cache)
                if was_missing and city in coords_cache: coords_dirty=True

            map_id=f"map_{re.sub(r'[^a-z0-9]','_',pdf.lower()[:18])}_{idx}"
            all_found.append({"filename":pdf,"title":title,"folder":folder_rel,"region":config["region"],"pdf_data":pdf_data})

            cards.append(make_brochure_card(pdf,pdf_data,title,desc,map_id,coords_cache,None))
            js=make_map_js(map_id,pdf_data.get("cities",[]),coords_cache)
            if js: maps_js_parts.append(js)
            tt2=pdf_data.get("tour_type","")
            if tt2 and tt2 not in tour_types_seen: tour_types_seen.append(tt2)

        html=build_brochure_index(config["title"],breadcrumb,"\n".join(cards),
            "\n".join(maps_js_parts),logo_src,logo_href,search_js)
        with open(os.path.join(folder_abs,"index.html"),'w',encoding='utf-8') as f:
            f.write(html)
        print(f"  Rebuilt {folder_rel}/index.html")
        if depth==2:
            slug=folder_rel.replace("multi-country/","")
            region_stats[slug]={"count":len(pdfs),"tour_types":tour_types_seen}

    # ── Generate package pages + region index pages from products/*.json ─────
    print(f"\nGenerating package pages from {len(products)} products...")

    region_packages = {}
    for product in products:
        folder_rel = f'multi-country/{product.get("region","")}'
        region_packages.setdefault(folder_rel, []).append(product)

    for folder_rel, pkgs in region_packages.items():
        folder_abs = os.path.join(REPO_ROOT, folder_rel)
        os.makedirs(folder_abs, exist_ok=True)
        config = FOLDER_CONFIG.get(folder_rel, {})
        depth = config.get('depth', 2)
        logo_src = "../"*depth + "logo.png"
        logo_href = "../"*depth
        search_js = "../"*depth + "global-search.js"
        breadcrumb = (f'<a href="../../">Home</a> › <a href="../">Multi-Country</a> › {config.get("breadcrumb","")}')

        cards = []
        maps_js_parts = []
        tour_types_seen = [s.get("name","") for p in pkgs for s in p.get("styles",{}).values()]
        tour_types_seen = sorted(set(tour_types_seen))

        for product in sorted(pkgs, key=lambda p: p.get("id","")):
            prices_path = os.path.join(REPO_ROOT, product.get("pricesFile",""))
            prices = load_json(prices_path)

            cities = [p.get("label") for p in (product.get("map") or {}).get("points", []) if p.get("nights", 0) > 0]
            for city in cities:
                was_missing = city not in coords_cache
                get_coords(city, coords_cache)
                if was_missing and city in coords_cache: coords_dirty = True

            brochure_fname = f'{product.get("id")}_brochure.html'
            page_html = render_package_page(product, prices, depth, back_href="./")
            out_path = os.path.join(folder_abs, brochure_fname)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            print(f"  ✓ {folder_rel}/{brochure_fname}")

            cards.append(make_package_card(product, prices, brochure_fname))

            map_id = f'map_{product.get("id","").replace(".","_")}'
            js = make_map_js(map_id, cities, coords_cache)
            if js: maps_js_parts.append(js)

        html = build_brochure_index(
            config.get('title',''), breadcrumb,
            "\n".join(cards), "\n".join(maps_js_parts),
            logo_src, logo_href, search_js
        )
        with open(os.path.join(folder_abs,"index.html"),'w',encoding='utf-8') as f:
            f.write(html)
        print(f"  Rebuilt {folder_rel}/index.html ({len(cards)} packages)")

        slug = folder_rel.replace("multi-country/","")
        region_stats[slug] = {"count": len(cards), "tour_types": tour_types_seen}

    if coords_dirty:
        save_coords_cache(coords_cache)
        print("\n  Saved city_coords_cache.json")

    # ── multi-country index ────────────────────────────────────────────────
    print("\nRebuilding multi-country/index.html...")
    mc_folder=os.path.join(REPO_ROOT,"multi-country")
    if os.path.isdir(mc_folder):
        region_cards=[]
        for slug,display in REGION_DISPLAY.items():
            stats=region_stats.get(slug,{"count":0,"tour_types":[]})
            if stats["count"]>0:
                region_cards.append(make_region_card(slug,display,stats["count"],stats["tour_types"]))
        mc_html=build_multicountry_index("\n".join(region_cards),"../","../global-search.js")
        with open(os.path.join(mc_folder,"index.html"),'w',encoding='utf-8') as f:
            f.write(mc_html)
        print("  Rebuilt multi-country/index.html")

    print(f"\nUpdating packages.json...")
    update_packages_json(packages_path,all_found,desc_cache)
    print("\nDone!")

if __name__=="__main__":
    main()
