"""
rebuild_site.py — v11
Changes from v10:
- Modern card design with hero images, clean typography
- Full brochure HTML pages generated per package (from mark12 JSONs)
- Cards link to brochure pages + PDF download
- mark12 integration: fetches package JSONs at build time
- pricing_locked respected: locked packages keep stored prices
- All v10 functionality preserved
"""

import os, re, json, urllib.request, urllib.parse, time
from datetime import datetime
import fitz

REPO_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
COORDS_CACHE  = os.path.join(REPO_ROOT, "city_coords_cache.json")
MARK12_RAW    = "https://raw.githubusercontent.com/europeincoming/mark12/main"

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

# map12 region slug → folder_rel
MARK12_REGION_MAP = {
    "uk-ireland":             "multi-country/uk-ireland",
    "western-central-europe": "multi-country/western-central-europe",
    "italy":                  "multi-country/italy",
    "france":                 "multi-country/france",
    "switzerland":            "multi-country/switzerland",
    "spain-portugal":         "multi-country/spain-portugal",
    "eastern-europe":         "multi-country/eastern-europe",
    "scandinavia":            "multi-country/scandinavia-iceland",
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


# ── mark12 INTEGRATION ────────────────────────────────────────────────────────
# Known package filenames in mark12 (update when new packages added)
MARK12_FILES = [
    "1.1_3_London_private.json",
    "1.2_3_London_-_2_Manchester-_2_Edinburgh_-_2.json",
    "1.3_3_London_-_1_Glasgow_-_2_Inverness_-_2_E.json",
    "1.4_2_Edinburgh_-_2_Inverness_-_1_Fort_Willi.json",
    "1.5_2_Dublin_-_3_Limerick_-_1_Dublin.json",
    "2.1_3_Paris_-_3_Lucerne_-_1_Zurich.json",
    "2.2_2_Paris_-_3_Lucerne_-_2_Innsbruck_-_2_Vi.json",
    "2.3_2_Paris_-_3_Lucerne_-_2_Venice_-_1_Flore.json",
    "2.4_2_Amsterdam_-_2_Paris_-_3_Lucerne_-_1_Zu.json",
    "2.5_2_Amsterdam_-_2_Paris_-_3_Lucerne_-_2_Ve.json",
    "2.6_3_Lucerne_-_2_Venice_-_1_Florence_-_2_Ro.json",
    "3.1_2_Venice_-_2_Florence_-_2_Rome.json",
    "3.2_2_Rome_-_2_Naples_-_2_Florence_-_2_Venic.json",
    "4.1_2_Lucerne_-_2_Interlaken_-_1_Zurich.json",
    "4.2_2_Lucerne_-_2_Interlaken_-_2_Montreux_-_.json",
    "5.1_2_Paris_-_2_Avignon_-_2_Aix_-_2_Nice.json",
    "5.2_2_Paris_-_2_Bayeux_-_2_Tours_-_1_Paris.json",
    "6.1_2_Madrid_-_2_Granada_-_2_Seville_-_2_Bar.json",
    "7.1_2_Prague_-_2_Vienna_-_2_Budapest.json",
    "9.1_1_CPH_-_1_Ferry_-_1_Oslo_-_1_Stockholm_-.json",
    "10.1_4_Rovaniemi_(Helsinki_pre_post)_winter.json",
    "10.3_4_Tromso_(Oslo_pre_post)_winter.json",
    "10.4_7_Tromso_(Oslo_pre_post)_winter.json",
    "10.5_4_Kiruna_(Stockholm_pre_post)_winter.json",
    "10.6_4_Kiruna_-_3_Abisko_(Stockholm_Pre_post).json",
]

# Also fix fetch_mark12_package to URL-encode parentheses


def fetch_mark12_index():
    """Try GitHub API first, fall back to hardcoded list"""
    try:
        url = "https://api.github.com/repos/europeincoming/mark12/contents/packages"
        req = urllib.request.Request(url, headers={
            "User-Agent": "EuropeIncomingFIT/1.0",
            "Accept": "application/vnd.github.v3+json"
        })
        with urllib.request.urlopen(req, timeout=20) as r:
            files = json.loads(r.read())
            if isinstance(files, list):
                names = [f["name"] for f in files if f.get("name","").endswith(".json")]
                print(f"  mark12 API: found {len(names)} files")
                return names
    except Exception as e:
        print(f"  mark12 API failed ({e}), using hardcoded list")
    return MARK12_FILES

def fetch_mark12_package(filename):
    """Fetch a single package JSON from mark12"""
    try:
        url = f"{MARK12_RAW}/packages/{urllib.parse.quote(filename, safe='')}"
        req = urllib.request.Request(url, headers={"User-Agent":"EuropeIncomingFIT/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Failed to fetch {filename}: {e}")
        return None

def fetch_mark12_packages():
    """Returns dict of sheet_id -> package JSON"""
    print("\nFetching packages from mark12...")
    files = fetch_mark12_index()
    packages = {}
    for fname in files:
        sid = fname.split('_')[0]
        pkg = fetch_mark12_package(fname)
        if pkg:
            packages[sid] = pkg
            print(f"  ✓ {sid}: {pkg.get('title','')[:50]}")
    print(f"  Fetched {len(packages)} packages from mark12")
    return packages


# ── BROCHURE PAGE GENERATOR ───────────────────────────────────────────────────
def fmt_price(val, curr="€"):
    if val is None: return "—"
    try: return f"{curr}{float(val):,.0f}"
    except: return str(val)

def make_brochure_map_js(map_id, cities, coords_cache):
    return make_map_js(map_id, cities, coords_cache)

def render_day_services(services):
    if not services: return ""
    tags = []
    for s in services:
        if s.get('rate',0) == 0 and 'pass' not in s.get('description','').lower():
            continue
        label = s.get('description','')
        rt    = s.get('rate_type','')
        rate  = s.get('rate',0)
        curr  = s.get('currency','EUR')
        curr_sym = '£' if curr=='GBP' else '€'
        if rt=='PP' and rate:
            tags.append(f'<span class="tag tag-inc">✓ {label}</span>')
        elif rt=='PI' and rate:
            tags.append(f'<span class="tag tag-inc">✓ {label}</span>')
    return '<div class="tags">' + ''.join(tags) + '</div>' if tags else ''

def render_regular_pricing(pricing, curr_sym):
    html = '<table class="price-table"><thead><tr><th>Hotel</th><th>Single</th><th>Twin / Double</th><th>Child</th></tr></thead><tbody>'
    for market in ['Premium','Standard']:
        mp = pricing.get(market,{})
        for season_key in ['winter','summer']:
            sp = mp.get(season_key)
            if not sp: continue
            label = sp.get('date_start','') + ' – ' + sp.get('date_end','')
            html += f'<tr class="ssep"><td colspan="4">{label}</td></tr>'
            for star in ['3star','4star']:
                sd = sp.get(star,{})
                if not sd: continue
                s_lbl = '3★ Standard' if star=='3star' else '4★ Superior'
                html += (f'<tr><td><span class="stag">{"3★" if star=="3star" else "4★"}</span>{s_lbl}</td>'
                         f'<td>{curr_sym}{sd.get("single",0):,.0f}</td>'
                         f'<td class="twin">{curr_sym}{sd.get("twin",0):,.0f}</td>'
                         f'<td>{curr_sym}{sd.get("child",0):,.0f}</td></tr>')
    html += '</tbody></table>'
    return html

def render_private_pricing(pricing, curr_sym):
    blocks = []
    for market in ['Premium','Standard']:
        mp = pricing.get(market,{})
        for season_key in ['winter','summer']:
            rows = mp.get(season_key,[])
            if not rows: continue
            season_label = 'Winter 2025/26' if season_key=='winter' else 'Summer 2026'
            tbl = f'<div class="priv-block"><div class="priv-season">{season_label}</div>'
            tbl += '<table class="priv-table"><thead><tr><th>Min Pax</th><th>3★ per adult</th><th>4★ per adult</th></tr></thead><tbody>'
            for row in rows:
                r3 = f'{curr_sym}{row["3star"]:,.0f}' if row.get('3star') else '—'
                r4 = f'{curr_sym}{row["4star"]:,.0f}' if row.get('4star') else '—'
                tbl += f'<tr><td>{row["pax"]}</td><td>{r3}</td><td>{r4}</td></tr>'
            tbl += '</tbody></table></div>'
            blocks.append(tbl)
    if not blocks: return ''
    return '<div class="priv-grids">' + ''.join(blocks) + '</div>'

def render_hotels(hotels, curr_sym):
    if not hotels: return ''
    cards = ''
    for h in hotels:
        city    = h.get('city','')
        nights  = h.get('nights','')
        h3      = h.get('hotel_3star') or '—'
        h4      = h.get('hotel_4star') or '—'
        cards += f'''<div class="hotel-card">
  <div class="hc-city">{city}</div>
  <div class="hc-nights">{nights} Night{"s" if nights!=1 else ""}</div>
  <div class="hc-cat">3 Star</div><div class="hc-name">{h3}</div>
  <div class="hc-cat">4 Star</div><div class="hc-name">{h4}</div>
</div>'''
    return f'<div class="hotels-grid">{cards}</div>'

def render_optionals(optionals):
    if not optionals: return ''
    items = ''
    for o in optionals:
        curr = '£' if o.get('currency','EUR')=='GBP' else '€'
        rate = o.get('rate',0)
        items += f'<div class="opt-item"><span class="opt-name">{o["description"]}</span><span class="opt-price">{curr}{rate:,.0f} <span class="opt-pp">pp</span></span></div>'
    return f'<div class="opt-grid">{items}</div>'

BROCHURE_PAGE_CSS = """
body{font-family:'Inter',sans-serif;background:#fff;color:#1a1a1a;font-size:15px;line-height:1.65;padding-top:0;}
.hero-header{position:sticky;top:0;z-index:200;height:68px;overflow:hidden;}
.hero-header-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 40%;}
.hero-header-overlay{position:absolute;inset:0;background:linear-gradient(to right,rgba(0,0,0,0.82),rgba(0,0,0,0.35));}
.hero-header-inner{position:relative;z-index:1;height:100%;display:flex;align-items:center;justify-content:space-between;padding:0 28px;gap:16px;}
.hero-back{color:rgba(255,255,255,0.75);font-size:12px;font-weight:500;text-decoration:none;display:flex;align-items:center;gap:6px;white-space:nowrap;transition:color 0.2s;}
.hero-back:hover{color:#fff;}
.hero-title-wrap{display:flex;flex-direction:column;align-items:center;}
.hero-title-main{font-family:'Playfair Display',serif;font-size:20px;font-weight:700;color:#fff;white-space:nowrap;}
.hero-title-sub{font-size:10px;color:rgba(255,255,255,0.5);letter-spacing:1.5px;margin-top:2px;text-align:center;}
.hero-search-wrap{position:relative;flex:0 0 260px;}
.hero-search{width:100%;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.25);color:#fff;padding:7px 14px 7px 32px;border-radius:4px;font-family:'Inter',sans-serif;font-size:12px;outline:none;}
.hero-search::placeholder{color:rgba(255,255,255,0.45);}
.search-icon-hero{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:rgba(255,255,255,0.5);font-size:13px;pointer-events:none;}
.search-results{display:none;position:absolute;top:calc(100%+6px);right:0;background:#fff;border:1px solid #e8e8e8;border-radius:4px;width:340px;max-height:300px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,0.12);z-index:300;}
.sri{padding:11px 16px;border-bottom:1px solid #f0f0f0;cursor:pointer;}
.sri:last-child{border-bottom:none;}
.sri:hover{background:#f9f9f9;}
.sri-title{font-size:13px;font-weight:500;color:#1a1a1a;}
.sri-meta{font-size:11px;color:#888;margin-top:2px;}
.variant-bar{position:sticky;top:68px;z-index:190;background:#fff;border-bottom:1px solid #e8e8e8;display:flex;align-items:center;justify-content:space-between;padding:0 48px;}
.vtabs{display:flex;}
.vtab{padding:14px 20px;font-size:13px;font-weight:500;color:#888;border:none;background:none;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color 0.2s,border-color 0.2s;letter-spacing:0.2px;}
.vtab.active{color:#1a3a5c;border-bottom-color:#1a3a5c;}
.vtab:hover:not(.active){color:#1a1a1a;}
.dl-btn{background:#1a3a5c;color:#fff;border:none;padding:9px 18px;font-family:'Inter',sans-serif;font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;cursor:pointer;border-radius:3px;transition:opacity 0.2s;}
.dl-btn:hover{opacity:0.85;}
.hero-full{height:380px;position:relative;overflow:hidden;background:#1a3a5c;}
.hero-full-img{width:100%;height:100%;object-fit:cover;opacity:0.6;display:block;}
.hero-full-overlay{position:absolute;inset:0;background:linear-gradient(to right,rgba(0,0,0,0.65) 0%,rgba(0,0,0,0.15) 70%);}
.hero-full-content{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;padding:36px 48px;}
.hero-eyebrow{font-size:10px;font-weight:500;letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,0.5);margin-bottom:8px;}
.hero-h1{font-family:'Playfair Display',serif;font-size:52px;font-weight:700;color:#fff;line-height:1.0;margin-bottom:8px;}
.hero-meta{display:flex;align-items:center;gap:14px;}
.hero-nights{font-size:13px;color:rgba(255,255,255,0.7);font-weight:300;}
.hero-route{font-size:12px;color:rgba(255,255,255,0.45);}
.hero-div{width:1px;height:12px;background:rgba(255,255,255,0.25);}
.body-wrap{display:flex;align-items:flex-start;max-width:1200px;margin:0 auto;padding:0 48px;}
.main-col{flex:1;min-width:0;padding:36px 48px 36px 0;}
.sidebar{width:300px;flex-shrink:0;padding:36px 0;position:sticky;top:116px;max-height:calc(100vh - 116px);overflow-y:auto;}
.vc{display:none;}
.vc.active{display:block;}
.section-label{font-size:10px;font-weight:600;letter-spacing:2.5px;text-transform:uppercase;color:#888;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #e8e8e8;}
.map-wrap{margin-bottom:32px;}
#map-r,#map-p,#map-s{height:200px;border-radius:3px;border:1px solid #e8e8e8;}
.day-card{display:grid;grid-template-columns:48px 1fr;gap:18px;padding:24px 0;border-bottom:1px solid #e8e8e8;}
.day-card:first-of-type{border-top:1px solid #e8e8e8;}
.day-num-col{text-align:center;padding-top:2px;}
.day-num-lbl{font-size:9px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#888;}
.day-num{font-family:'Playfair Display',serif;font-size:34px;font-weight:700;color:#1a3a5c;line-height:1;}
.day-body{}
.day-title{font-size:15px;font-weight:600;color:#1a1a1a;margin-bottom:3px;}
.day-overnight{font-size:11px;font-weight:500;letter-spacing:1px;text-transform:uppercase;color:#9a7230;margin-bottom:8px;}
.day-photo{width:100%;height:150px;object-fit:cover;border-radius:3px;margin-bottom:10px;display:block;}
.day-desc{font-size:13.5px;line-height:1.8;color:#555;margin-bottom:10px;}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;}
.tag{font-size:11px;padding:3px 10px;border-radius:2px;font-weight:500;}
.tag-inc{background:#edf4ed;color:#2a6a2a;}
.tag-opt{background:#fdf5e0;color:#7a5800;}
.inc-grid{display:grid;grid-template-columns:1fr 1fr;gap:0;margin-bottom:32px;}
.inc-item{font-size:13px;color:#555;padding:8px 0 8px 16px;border-bottom:1px solid #e8e8e8;position:relative;}
.inc-item::before{content:'✓';position:absolute;left:0;color:#2a6a2a;font-size:11px;font-weight:700;}
.hotels-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#e8e8e8;margin-bottom:32px;}
.hotel-card{background:#fff;padding:18px;}
.hc-city{font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#888;margin-bottom:3px;}
.hc-nights{font-size:13px;font-weight:600;color:#1a1a1a;margin-bottom:10px;}
.hc-cat{font-size:10px;font-weight:700;letter-spacing:1px;color:#1a3a5c;margin-bottom:2px;}
.hc-name{font-size:12px;color:#555;margin-bottom:7px;line-height:1.4;}
.price-note{font-size:12px;color:#888;font-style:italic;margin-bottom:12px;}
.price-table{width:100%;border-collapse:collapse;margin-bottom:32px;}
.price-table th{background:#1a3a5c;color:#fff;padding:10px 14px;font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;text-align:left;}
.price-table td{padding:11px 14px;font-size:13px;border-bottom:1px solid #e8e8e8;}
.price-table .ssep td{background:#f7f7f5;font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#888;padding:6px 14px;border-bottom:1px solid #e8e8e8;}
.price-table .twin{font-weight:700;color:#1a3a5c;}
.stag{display:inline-block;background:#1a3a5c;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:2px;margin-right:8px;}
.priv-grids{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#e8e8e8;margin-bottom:32px;}
.priv-block{background:#fff;padding:18px;}
.priv-season{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#888;margin-bottom:12px;}
.priv-table{width:100%;border-collapse:collapse;}
.priv-table th{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#1a1a1a;padding:5px 8px;border-bottom:1px solid #e8e8e8;text-align:left;}
.priv-table td{padding:7px 8px;font-size:12.5px;border-bottom:1px solid #e8e8e8;color:#555;}
.priv-table td:last-child{font-weight:700;color:#1a3a5c;}
.priv-table tr:last-child td{border-bottom:none;}
.opt-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#e8e8e8;margin-bottom:32px;}
.opt-item{background:#fff;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;gap:10px;}
.opt-name{font-size:12.5px;color:#555;}
.opt-price{font-size:14px;font-weight:700;color:#1a1a1a;white-space:nowrap;}
.opt-pp{font-size:11px;font-weight:400;color:#888;}
.highlights{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#e8e8e8;margin-bottom:36px;}
.highlight-block{background:#fff;padding:24px;}
.hb-label{font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#9a7230;margin-bottom:10px;}
.hb-items{list-style:none;}
.hb-items li{padding:7px 0;border-bottom:1px solid #f0f0f0;font-size:13px;color:#555;line-height:1.5;}
.hb-items li:last-child{border-bottom:none;}
.hb-items li strong{color:#1a1a1a;font-weight:500;}
.sb-section{margin-bottom:28px;}
.sb-label{font-size:9px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#9a7230;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #e8e8e8;}
.sb-photo{width:100%;height:110px;object-fit:cover;border-radius:3px;margin-bottom:12px;display:block;}
.sb-item{padding:9px 0;border-bottom:1px solid #f0f0f0;}
.sb-item:last-child{border-bottom:none;}
.sb-item-title{font-size:12.5px;font-weight:500;color:#1a1a1a;margin-bottom:2px;}
.sb-item-desc{font-size:12px;color:#666;line-height:1.55;}
.tc-wrap{margin-bottom:36px;}
.tc-btn{width:100%;background:#f7f7f5;border:1px solid #e8e8e8;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;font-family:'Inter',sans-serif;font-size:12.5px;font-weight:500;color:#1a1a1a;border-radius:3px;text-align:left;}
.tc-body{display:none;border:1px solid #e8e8e8;border-top:none;padding:18px;border-radius:0 0 3px 3px;}
.tc-body.open{display:block;}
.tc-body li{font-size:12px;color:#666;padding:6px 0 6px 14px;border-bottom:1px solid #f0f0f0;list-style:none;position:relative;line-height:1.5;}
.tc-body li::before{content:'·';position:absolute;left:4px;}
.tc-body li:last-child{border-bottom:none;}
.brochure-footer{background:#1a1a1a;color:#666;padding:18px 48px;font-size:11.5px;display:flex;justify-content:space-between;align-items:center;}
.brochure-footer a{color:#888;text-decoration:none;}
.leaflet-tooltip.city-tip{background:transparent!important;border:none!important;box-shadow:none!important;font-size:9px;font-weight:700;color:#1a1a2e;white-space:nowrap;padding:0;text-shadow:-1px -1px 0 white,1px -1px 0 white,-1px 1px 0 white,1px 1px 0 white;}
.leaflet-tooltip.city-tip::before{display:none!important;}
@media print{.hero-header,.variant-bar,.sidebar,.dl-btn,.brochure-footer{display:none!important;}.body-wrap{display:block;padding:0;}.main-col{padding:16px 0;}}
"""

TC_HTML = """<ul>
<li>All rates are net and per person for the package.</li>
<li>Child rates apply for children aged 2 to 11 years old. One child sharing a room with 2 adults, subject to hotel policy.</li>
<li>All rates are subject to availability at the time of booking. Europe Incoming will endeavour to match the rates quoted.</li>
<li>Rates are not applicable during trade fair periods, major European public holidays, and other major events.</li>
<li>City taxes are not included in the price.</li>
<li>If certain attractions are closed during specific periods, alternative options will be arranged.</li>
<li>All bookings must be confirmed at least 60 working days prior to arrival.</li>
<li>100% pre-payment required by bank transfer or credit card (Visa or Mastercard). All bank transfer charges covered by the Agent.</li>
<li>Vouchers will be issued after receipt of full payment.</li>
</ul>"""

def generate_brochure_page(pkg, coords_cache, depth=2):
    """Generate full HTML brochure page from a mark12 package JSON"""
    pkg_id   = pkg.get('id','')
    title    = pkg.get('title','')
    nights   = pkg.get('nights','')
    hotels   = pkg.get('hotels',[])
    variants = pkg.get('variants',{})
    optionals= pkg.get('optionals',[])
    curr_sym = '£' if pkg.get('currency','EUR')=='GBP' else '€'

    # Cities from hotels
    cities = [h.get('city','') for h in hotels if h.get('city')]
    route  = ' → '.join(cities)
    hero_img = get_card_image(cities)

    # Back link depth
    back_href = '../' * depth
    logo_src  = back_href + 'logo.png'

    # Build variant tabs and content
    variant_tabs_html = ''
    variant_content_html = ''
    maps_js = ''
    variant_labels = {'regular_fit':'Regular FIT','private':'Private Tour','self_drive':'Self Drive'}
    first = True

    for vkey in ['regular_fit','private','self_drive']:
        if vkey not in variants: continue
        vdata   = variants[vkey]
        services= vdata.get('services',[])
        pricing = vdata.get('pricing',{})
        active  = 'active' if first else ''
        vlabel  = variant_labels[vkey]
        map_id  = f'map-{vkey[0]}'

        variant_tabs_html += f'<button class="vtab {active}" onclick="switchVariant(\'{vkey}\',this)">{vlabel}</button>'

        # Map
        map_html = f'<div class="map-wrap"><div class="section-label">Route Map</div><div id="{map_id}"></div></div>'
        maps_js += f'initMap("{map_id}",{json.dumps([[get_coords(c,coords_cache) or [0,0],c] for c in cities if get_coords(c,coords_cache)])});\n'

        # Day-by-day from services
        days_html = '<div class="section-label" style="margin-top:8px">Day by Day</div>'
        current_day = None
        day_services = {}
        for s in services:
            d = s.get('day','')
            if d and d != current_day:
                current_day = d
            if d not in day_services: day_services[d] = []
            day_services[d].append(s)

        # Group by day number
        day_cards = ''
        day_num = 0
        for d, svcs in day_services.items():
            day_num += 1
            day_match = re.search(r'\d+', d) if d else None
            dn = day_match.group(0) if day_match else str(day_num)

            # Find overnight city for this day
            overnight = ''
            if hotels and day_num <= len(cities):
                overnight = cities[min(day_num-1, len(cities)-1)]
            overnight_html = f'<div class="day-overnight">Overnight: {overnight}</div>' if overnight else ''

            # Day photo
            day_img = get_card_image([overnight] if overnight else cities)
            photo_html = f'<img class="day-photo" src="{day_img}" alt="{overnight}" loading="lazy">'

            # Services as tags
            tags_html = render_day_services(svcs)
            desc_items = [s['description'] for s in svcs if s.get('description')]
            desc_text = '. '.join(desc_items[:2]) if desc_items else ''

            day_cards += f'''<div class="day-card">
  <div class="day-num-col"><div class="day-num-lbl">Day</div><div class="day-num">{dn}</div></div>
  <div class="day-body">
    <div class="day-title">{overnight or f"Day {dn}"}</div>
    {overnight_html}
    {photo_html}
    <div class="day-desc">{desc_text}</div>
    {tags_html}
  </div>
</div>'''

        # Inclusions
        inc_items = [s for s in services if s.get('rate_type') in ('PP','PI') and s.get('rate',0)>0]
        inc_html = ''
        if inc_items:
            items_html = ''.join(f'<div class="inc-item">{s["description"]}</div>' for s in inc_items[:10])
            inc_html = f'<div class="section-label" style="margin-top:32px">Package Includes</div><div class="inc-grid" style="margin-bottom:32px">{items_html}</div>'

        # Hotels
        hotels_html = f'<div class="section-label">Sample Hotels</div>{render_hotels(hotels,curr_sym)}'

        # Pricing
        pricing_html = f'<div class="section-label">Package Rates — Per Person</div>'
        if vkey == 'private':
            pricing_html += render_private_pricing(pricing, curr_sym)
        else:
            pricing_html += f'<p class="price-note">All rates in {curr_sym}. Twin/double occupancy unless stated.</p>'
            pricing_html += render_regular_pricing(pricing, curr_sym)

        # Optionals
        opt_html = ''
        if optionals:
            opt_html = f'<div class="section-label">Optional Extras</div>{render_optionals(optionals)}'

        # T&C
        tc_html = f'''<div class="tc-wrap">
  <button class="tc-btn" onclick="toggleTC(this)"><span>Terms & Conditions</span><span>▼</span></button>
  <div class="tc-body">{TC_HTML}</div>
</div>'''

        content = map_html + days_html + day_cards + inc_html + hotels_html + pricing_html + opt_html + tc_html
        variant_content_html += f'<div class="vc {active}" id="vc-{vkey}">{content}</div>'
        first = False

    # Sidebar highlights (generic, can be enhanced per destination later)
    sidebar_html = f'''<div class="sidebar">
  <div class="sb-section">
    <div class="sb-label">About This Tour</div>
    <img class="sb-photo" src="{hero_img}" alt="{title}">
    <div class="sb-item">
      <div class="sb-item-title">{nights} nights across {len(cities)} destinations</div>
      <div class="sb-item-desc">Route: {route}</div>
    </div>
    {"".join(f'<div class="sb-item"><div class="sb-item-title">{c}</div></div>' for c in cities)}
  </div>
</div>'''

    # Map init JS
    map_init_js = f'''
function initMap(id, pts) {{
  if(!pts.length) return;
  var lats=pts.map(p=>p[0][0]),lngs=pts.map(p=>p[0][1]),pad=0.5;
  var bounds=[[Math.min(...lats)-pad,Math.min(...lngs)-pad],[Math.max(...lats)+pad,Math.max(...lngs)+pad]];
  var map=L.map(id,{{zoomControl:false,scrollWheelZoom:false,dragging:false,attributionControl:false}});
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{maxZoom:13}}).addTo(map);
  map.fitBounds(bounds,{{padding:[14,14]}});
  if(pts.length>1)L.polyline(pts.map(p=>p[0]),{{color:'#1a3a5c',weight:2,dashArray:'5,4'}}).addTo(map);
  pts.forEach((p,i)=>{{
    var color=i===0?'#e53935':(i===pts.length-1?'#43a047':'#1a3a5c');
    L.circleMarker(p[0],{{radius:5,fillColor:color,color:'white',weight:2,fillOpacity:1}}).addTo(map)
     .bindTooltip(p[1],{{permanent:true,direction:'top',className:'city-tip',offset:[0,-5]}});
  }});
}}
window.addEventListener('load',function(){{ {maps_js} }});
'''

    search_demos = json.dumps([
        {"title":"Paris & Switzerland","nights":"7N/8D","routing":"Paris → Lucerne → Zurich"},
        {"title":"UK Grand Tour","nights":"10N/11D","routing":"London → Manchester → Edinburgh"},
        {"title":"Paris Switzerland Italy","nights":"10N/11D","routing":"Paris → Lucerne → Venice → Rome"},
        {"title":"Ireland Discovery","nights":"6N/7D","routing":"Dublin → Limerick → Dublin"},
        {"title":"Spain Explorer","nights":"8N/9D","routing":"Madrid → Granada → Seville → Barcelona"},
        {"title":"Swiss Lakes & Alps","nights":"5N/6D","routing":"Lucerne → Interlaken → Zurich"},
        {"title":"Nordic Capitals","nights":"6N/7D","routing":"Copenhagen → Oslo → Stockholm → Helsinki"},
        {"title":"Scottish Highlands","nights":"6N/7D","routing":"Edinburgh → Inverness → Glasgow"},
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} | Europe Incoming FIT Packages</title>
{GF_FONTS}
<style>{BROCHURE_PAGE_CSS}</style>
{LEAFLET_HEAD}{HTML2PDF}{GA}
</head>
<body>
{GEO_BLOCK}
<div class="hero-header">
  <img class="hero-header-img" src="{hero_img}" alt="{title}">
  <div class="hero-header-overlay"></div>
  <div class="hero-header-inner">
    <a class="hero-back" href="{back_href}">← All Packages</a>
    <div class="hero-title-wrap">
      <div class="hero-title-main">{title}</div>
      <div class="hero-title-sub">{nights} NIGHTS · {route.upper()}</div>
    </div>
    <div class="hero-search-wrap">
      <span class="search-icon-hero">⌕</span>
      <input class="hero-search" id="searchInput" type="text" placeholder="Search packages…" autocomplete="off">
      <div class="search-results" id="searchResults"></div>
    </div>
  </div>
</div>
<div class="hero-full">
  <img class="hero-full-img" src="{hero_img}" alt="{title}">
  <div class="hero-full-overlay"></div>
  <div class="hero-full-content">
    <div class="hero-eyebrow">Europe Incoming · FIT Packages</div>
    <h1 class="hero-h1">{title}</h1>
    <div class="hero-meta">
      <span class="hero-nights">{nights} Nights</span>
      <span class="hero-div"></span>
      <span class="hero-route">{route}</span>
    </div>
  </div>
</div>
<div class="variant-bar">
  <div class="vtabs">{variant_tabs_html}</div>
  <button class="dl-btn" onclick="downloadPDF()">↓ Download PDF</button>
</div>
<div class="body-wrap">
  <div class="main-col">{variant_content_html}</div>
  {sidebar_html}
</div>
<div class="brochure-footer">
  <span>Europe Incoming Holdings Ltd · Reg. England & Wales 07053949</span>
  <span><a href="mailto:fitsales@europeincoming.com">fitsales@europeincoming.com</a> · +44 208 994 5001</span>
</div>
<script>
function switchVariant(v,btn){{
  document.querySelectorAll('.vc').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.vtab').forEach(el=>el.classList.remove('active'));
  document.getElementById('vc-'+v).classList.add('active');
  btn.classList.add('active');
}}
function toggleTC(btn){{
  var body=btn.nextElementSibling;
  body.classList.toggle('open');
  btn.querySelector('span:last-child').textContent=body.classList.contains('open')?'▲':'▼';
}}
function downloadPDF(){{
  var hide=['.hero-header','.variant-bar','.sidebar','.brochure-footer','.dl-btn'];
  hide.forEach(s=>document.querySelectorAll(s).forEach(el=>el.style.display='none'));
  document.querySelectorAll('.tc-body').forEach(el=>el.classList.add('open'));
  document.querySelector('.body-wrap').style.display='block';
  document.querySelector('.main-col').style.padding='16px 0';
  html2pdf().set({{margin:[8,8,8,8],filename:'{title.replace(" ","_")}.pdf',image:{{type:'jpeg',quality:0.9}},html2canvas:{{scale:2,useCORS:true}},jsPDF:{{unit:'mm',format:'a4',orientation:'portrait'}}}}).from(document.body).save().then(()=>{{
    hide.forEach(s=>document.querySelectorAll(s).forEach(el=>el.style.display=''));
    document.querySelector('.body-wrap').style.display='';
    document.querySelector('.main-col').style.padding='';
  }});
}}
var demos={search_demos};
var si=document.getElementById('searchInput'),sr=document.getElementById('searchResults');
si.addEventListener('input',function(){{
  var q=this.value.trim().toLowerCase();
  if(q.length<2){{sr.style.display='none';return;}}
  var m=demos.filter(p=>p.title.toLowerCase().includes(q)||p.routing.toLowerCase().includes(q));
  sr.innerHTML=m.length?m.map(p=>`<div class="sri"><div class="sri-title">${{p.title}}</div><div class="sri-meta">${{p.nights}} · ${{p.routing}}</div></div>`).join(''):'<div style="padding:14px 16px;font-size:13px;color:#888">No packages found</div>';
  sr.style.display='block';
}});
document.addEventListener('click',e=>{{if(!e.target.closest('.hero-search-wrap'))sr.style.display='none';}});
{map_init_js}
</script>
</body></html>"""


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

    # ── Fetch mark12 packages ──────────────────────────────────────────────
    mark12_pkgs = fetch_mark12_packages()

    # ── PDF loop: city-break only. Multi-country uses mark12 JSONs ──────────
    for folder_rel, config in FOLDER_CONFIG.items():
        folder_abs=os.path.join(REPO_ROOT,folder_rel)
        if not os.path.isdir(folder_abs): continue
        # Skip multi-country folders - handled by mark12 JSON loop below
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

            # Check if a brochure page exists for this PDF
            brochure_page = None
            tt = (pdf_data.get("tour_type") or "").lower().replace(" ","_").replace("-","_")
            for sid, mpkg in mark12_pkgs.items():
                mpkg_region = MARK12_REGION_MAP.get(mpkg.get('region',''), '')
                if mpkg_region == folder_rel:
                    variants = mpkg.get('variants',{})
                    # Match variant type to PDF tour type
                    variant_key = None
                    if 'self' in tt and 'self_drive' in variants: variant_key = 'self_drive'
                    elif 'private' in tt and 'private' in variants: variant_key = 'private'
                    elif 'regular' in tt and 'regular_fit' in variants: variant_key = 'regular_fit'
                    elif not tt and variants: variant_key = list(variants.keys())[0]
                    if variant_key:
                        brochure_page = f"{sid}_brochure.html"
                        break

            cards.append(make_brochure_card(pdf,pdf_data,title,desc,map_id,coords_cache,brochure_page))
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

    # ── Generate brochure pages + region index pages from mark12 ────────────
    print("\nGenerating brochure pages from mark12...")

    # Group packages by region folder
    region_packages = {}
    for sid, mpkg in mark12_pkgs.items():
        folder_rel = MARK12_REGION_MAP.get(mpkg.get('region',''))
        if not folder_rel: continue
        if folder_rel not in region_packages:
            region_packages[folder_rel] = []
        region_packages[folder_rel].append((sid, mpkg))

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
        tour_types_seen = []

        for sid, mpkg in sorted(pkgs, key=lambda x: x[0]):
            # Ensure coords
            cities = [h.get('city','') for h in mpkg.get('hotels',[]) if h.get('city')]
            for city in cities:
                was_missing = city not in coords_cache
                get_coords(city, coords_cache)
                if was_missing and city in coords_cache: coords_dirty = True

            # Generate brochure page
            page_html = generate_brochure_page(mpkg, coords_cache, depth)
            brochure_fname = f"{sid}_brochure.html"
            out_path = os.path.join(folder_abs, brochure_fname)
            with open(out_path,'w',encoding='utf-8') as f:
                f.write(page_html)
            print(f"  ✓ {folder_rel}/{brochure_fname}")

            # Build card for index page
            variants = mpkg.get('variants',{})
            title = mpkg.get('title','')
            nights = mpkg.get('nights','')
            winter_only = mpkg.get('winter_only', False)
            season = 'winter' if winter_only else 'all-year'
            curr_sym = '£' if mpkg.get('currency','EUR')=='GBP' else '€'

            # Get lowest twin price from first available variant
            price = None
            for vkey in ['regular_fit','private','self_drive']:
                vdata = variants.get(vkey,{})
                pricing = vdata.get('pricing',{})
                for market in ['Standard','Premium']:
                    for skey in ['winter','summer']:
                        sp = pricing.get(market,{}).get(skey)
                        if isinstance(sp, dict):
                            t = sp.get('3star',{}).get('twin') or sp.get('4star',{}).get('twin')
                            if t:
                                price = float(t)
                                break
                        elif isinstance(sp, list) and sp:
                            t = sp[0].get('3star') or sp[0].get('4star')
                            if t:
                                price = float(t)
                                break
                    if price: break
                if price: break

            desc = mpkg.get('description','') or _fallback_desc(cities, config.get('region',''), '')
            route = ' → '.join(cities)
            img = get_card_image(cities)
            dur = f"{nights} nights" if nights else ""

            # Tour type pills from variants
            for vk in variants:
                vl = {'regular_fit':'Regular','private':'Private','self_drive':'Self Drive'}.get(vk,'')
                if vl and vl not in tour_types_seen: tour_types_seen.append(vl)

            # Variant tabs for card subtitle
            vtypes = ' · '.join({'regular_fit':'Regular FIT','private':'Private','self_drive':'Self Drive'}.get(v,'') for v in variants if v in ('regular_fit','private','self_drive'))

            season_cls = 'season-winter' if winter_only else 'season-allyear'
            season_lbl = '❄️ Winter' if winter_only else '🌍 All Year'
            price_html = f'<div class="card-price">From {curr_sym}{price:,.0f} pp</div>' if price else ''

            card = f"""<div class="brochure-card">
  <div class="card-hero">
    <img src="{img}" alt="{title}" loading="lazy">
    <div class="card-hero-overlay"></div>
    <div class="card-season {season_cls}">{season_lbl}</div>
  </div>
  <div class="card-body">
    <div class="card-title">{title}</div>
    {"<div class='card-duration'>🕐 " + dur + "</div>" if dur else ""}
    {"<div class='card-route'>📍 " + route + "</div>" if route else ""}
    {"<div class='card-desc'>" + desc + "</div>" if desc else ""}
    {price_html}
  </div>
  <div class="card-actions">
    <a href="{brochure_fname}" class="btn-view">View Package</a>
  </div>
</div>"""
            cards.append(card)

            # Map JS for index
            map_id = f"map_{sid.replace('.','_')}"
            js = make_map_js(map_id, cities, coords_cache)
            if js: maps_js_parts.append(js)

        # Write region index
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
