"""Download reference photos of Deribasivska Street from Wikimedia Commons (polite, with backoff)."""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

UA = "DeribasivskaRefFetch/1.0 (one-off reference image download)"
OUT = sys.argv[1] if len(sys.argv) > 1 else "refs"
API = "https://commons.wikimedia.org/w/api.php"
os.makedirs(OUT, exist_ok=True)

def get(url, tries=8):
    delay = 20
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After")
            wait = int(ra) if ra and ra.isdigit() else delay
            print("HTTP", e.code, "wait", wait, url[:90], flush=True)
            time.sleep(min(wait, 300)); delay = min(delay * 2, 300)
        except Exception as e:
            print("ERR", e, flush=True); time.sleep(delay)
    return None

def api(**kw):
    kw["format"] = "json"
    b = get(API + "?" + urllib.parse.urlencode(kw))
    try:
        return json.loads(b) if b else {}
    except Exception:
        return {}

titles = []
IDX = os.path.join(OUT, "index.json")
if os.path.exists(IDX):
    titles = [tuple(t) for t in json.load(open(IDX))]
for q in [] if titles else ["Derybasivska Street autumn", "Deribasovskaya street Odessa trees",
          "Дерибасівська вулиця Одеса", "Derybasivska Street Odesa pedestrian",
          "Odessa Passage Derybasivska", "Odesa Transfiguration Cathedral Soborna square",
          "Дерибасовская осень"]:
    d = api(action="query", generator="search", gsrsearch=q + " filetype:bitmap", gsrnamespace=6,
            gsrlimit=20, prop="imageinfo", iiprop="url|size")
    for p in d.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("url") and ii.get("width", 0) >= 1280:
            titles.append((q, p["title"], ii["url"]))
    print(q, "->", len(titles), flush=True)
    time.sleep(5)

json.dump(titles, open(os.path.join(OUT, "index.json"), "w"), ensure_ascii=False, indent=1)
seen = set(); n = 0
for q, title, url in titles:
    if url in seen or n >= 40: continue
    seen.add(url)
    # standard thumbnail path on upload.wikimedia.org
    url = url.split("?")[0]
    name = url.rsplit("/", 1)[1]
    thumb = url.replace("/commons/", "/commons/thumb/") + "/1280px-" + name
    b = get(thumb, tries=5)
    if b and b[:2] == b"\xff\xd8":
        fn = os.path.join(OUT, "ref_%02d.jpg" % n)
        open(fn, "wb").write(b); n += 1
        print("saved", fn, title, flush=True)
    time.sleep(4)
print("done", n)
