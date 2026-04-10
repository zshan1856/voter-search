from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

app = FastAPI()

# -------------------------
# NORMALIZATION
# -------------------------
def normalize(text):
    if not text:
        return ""

    text = text.strip().lower()

    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    # normalize patterns
    text = text.replace("aa", "a").replace("ee", "i").replace("oo", "u")
    text = text.replace("kh", "k").replace("gh", "g").replace("sh", "s")

    return text


def phonetic(text):
    text = normalize(text)
    return "".join([c for c in text if c not in "aeiou"])


# -------------------------
# LOAD DATA
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

DATABASE = []

def load_data():
    global DATABASE

    res = requests.get(DATA_URL)
    data = res.json()

    for r in data:
        tokens = r.get("search_tokens", [])

        norm_tokens = [normalize(t) for t in tokens]

        r["blob"] = " ".join(norm_tokens)
        r["phonetic_blob"] = phonetic(r["blob"])

    DATABASE = data

load_data()


# -------------------------
# UI
# -------------------------
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


# -------------------------
# SEARCH
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    query = (surname + " " + firstname).strip()
    query_ph = phonetic(query)

    if not query:
        return {"results": []}

    tier1 = []
    tier2 = []
    tier3 = []

    for r in DATABASE:

        blob = r["blob"]
        blob_ph = r["phonetic_blob"]

        # -------------------------
        # TIER 1 (STRONG)
        # -------------------------
        if query == blob or query in blob.split():
            tier1.append(r)
            continue

        if query_ph == blob_ph or query_ph in blob_ph:
            tier1.append(r)
            continue

        # -------------------------
        # TIER 2 (MEDIUM)
        # -------------------------
        if blob.startswith(query):
            tier2.append(r)
            continue

        if fuzz.partial_ratio(query, blob) > 90:
            tier2.append(r)
            continue

        # -------------------------
        # TIER 3 (WEAK)
        # -------------------------
        if fuzz.partial_ratio(query, blob) > 80:
            tier3.append(r)

    # Combine results (priority order)
    results = tier1 + tier2 + tier3

    return {"results": results[:200]}  # cap to avoid overload
