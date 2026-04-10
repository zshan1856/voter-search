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

    text = text.replace("aa", "a").replace("ee", "i").replace("oo", "u")

    return text


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
        r["normalized_tokens"] = [normalize(t) for t in tokens]

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
# MATCH FUNCTION (SMART)
# -------------------------
def score_token(query, token):
    if query == token:
        return 5
    if token.startswith(query):
        return 4
    if fuzz.ratio(query, token) > 90:
        return 3
    if fuzz.ratio(query, token) > 80:
        return 2
    if query in token:
        return 1
    return 0


# -------------------------
# SEARCH API
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    if not surname and not firstname:
        return {"results": []}

    results = []

    for r in DATABASE:

        tokens = r.get("normalized_tokens", [])

        if not tokens:
            continue

        s_score = 0
        f_score = 0

        # surname = first token
        if surname:
            s_score = score_token(surname, tokens[0])

        # firstname = rest tokens
        if firstname:
            for t in tokens[1:]:
                f_score = max(f_score, score_token(firstname, t))

        # filtering logic
        if surname and not firstname:
            if s_score == 0:
                continue
        elif firstname and not surname:
            if f_score == 0:
                continue
        else:
            if s_score == 0 and f_score == 0:
                continue

        score = s_score + f_score

        if s_score > 0 and f_score > 0:
            score += 5  # boost

        results.append((score, r))

    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
