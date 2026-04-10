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

    # phonetic normalization (IMPORTANT)
    text = text.replace("aa", "a").replace("ee", "i").replace("oo", "u")
    text = text.replace("kh", "k").replace("gh", "g").replace("sh", "s")

    # fix anjum / anjum variation
    text = text.replace("nj", "nj").replace("nz", "nj")

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

        r["search_blob"] = " ".join(norm_tokens)
        r["phonetic_blob"] = phonetic(r["search_blob"])

    DATABASE = data

load_data()


# -------------------------
# SERVE UI
# -------------------------
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


# -------------------------
# SEARCH API
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    query = (surname + " " + firstname).strip()
    query_ph = phonetic(query)

    if not query:
        return {"results": []}

    results = []

    for r in DATABASE:

        blob = r["search_blob"]
        blob_ph = r["phonetic_blob"]

        score = 0

        # exact
        if query in blob:
            score += 5

        # phonetic match
        if query_ph in blob_ph:
            score += 4

        # fuzzy
        if fuzz.partial_ratio(query, blob) > 85:
            score += 3

        if score > 0:
            results.append((score, r))

    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
