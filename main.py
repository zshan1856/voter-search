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
# PHONETIC KEY (CORE)
# -------------------------
def phonetic_key(word):
    if not word:
        return ""

    w = word.lower()

    # remove vowels (except first)
    first = w[0]
    rest = "".join([c for c in w[1:] if c not in "aeiou"])

    # normalize common variations
    rest = rest.replace("ph", "f")
    rest = rest.replace("kh", "k")
    rest = rest.replace("gh", "g")
    rest = rest.replace("sh", "s")
    rest = rest.replace("z", "j")

    return first + rest


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

        normalized = [normalize(t) for t in tokens]
        phonetics = [phonetic_key(t) for t in normalized]

        r["normalized_tokens"] = normalized
        r["phonetic_tokens"] = phonetics

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
# MATCH FUNCTION (ADVANCED)
# -------------------------
def score_token(query, tokens, phonetic_tokens):
    best = 0
    q_ph = phonetic_key(query)

    for i, t in enumerate(tokens):

        # exact
        if query == t:
            return 6

        # prefix
        if t.startswith(query):
            best = max(best, 5)

        # phonetic
        if q_ph == phonetic_tokens[i]:
            best = max(best, 4)

        # fuzzy
        if fuzz.ratio(query, t) > 85:
            best = max(best, 3)

        # substring
        if query in t:
            best = max(best, 2)

    return best


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

        tokens = r["normalized_tokens"]
        phonetics = r["phonetic_tokens"]

        s_score = 0
        f_score = 0

        # surname = first token
        if surname:
            s_score = score_token(surname, [tokens[0]], [phonetics[0]])

        # firstname = rest
        if firstname:
            f_score = score_token(firstname, tokens[1:], phonetics[1:])

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

        # boost if both match
        if s_score > 0 and f_score > 0:
            score += 5

        results.append((score, r))

    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
