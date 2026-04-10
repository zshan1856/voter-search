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

    return text


def remove_vowels(text):
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

        norm = [normalize(t) for t in tokens]
        nv = [remove_vowels(t) for t in norm]

        r["tokens"] = norm
        r["tokens_nv"] = nv

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
# MATCH FUNCTION (STRICT)
# -------------------------
def match_token(query, query_nv, token, token_nv):
    
    # exact
    if query == token:
        return 3

    # startswith
    if token.startswith(query):
        return 2

    # vowel-less match (important for anjum)
    if query_nv == token_nv:
        return 2

    # strong fuzzy only
    if fuzz.ratio(query, token) > 92:
        return 1

    return 0


# -------------------------
# SEARCH API
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    surname_nv = remove_vowels(surname)
    firstname_nv = remove_vowels(firstname)

    if not surname and not firstname:
        return {"results": []}

    strong = []
    medium = []

    for r in DATABASE:

        tokens = r["tokens"]
        tokens_nv = r["tokens_nv"]

        if not tokens:
            continue

        s_score = 0
        f_score = 0

        # -------------------------
        # SURNAME (ONLY TOKEN[0])
        # -------------------------
        if surname:
            s_score = match_token(
                surname,
                surname_nv,
                tokens[0],
                tokens_nv[0]
            )

        # -------------------------
        # FIRSTNAME (TOKEN[1:])
        # -------------------------
        if firstname:
            for i in range(1, len(tokens)):
                score = match_token(
                    firstname,
                    firstname_nv,
                    tokens[i],
                    tokens_nv[i]
                )
                f_score = max(f_score, score)

        # -------------------------
        # DECISION LOGIC
        # -------------------------
        if surname and not firstname:
            if s_score > 0:
                strong.append((s_score, r))

        elif firstname and not surname:
            if f_score > 0:
                strong.append((f_score, r))

        else:
            if s_score > 0 and f_score > 0:
                strong.append((s_score + f_score + 2, r))  # boost
            elif s_score > 0 or f_score > 0:
                medium.append((s_score + f_score, r))

    # sort properly
    strong.sort(key=lambda x: x[0], reverse=True)
    medium.sort(key=lambda x: x[0], reverse=True)

    results = [r[1] for r in strong + medium]

    return {"results": results[:200]}
