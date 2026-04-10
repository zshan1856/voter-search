from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -------------------------
# INIT
# -------------------------
app = FastAPI()

# -------------------------
# LOAD DATA
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

DATABASE = []

def normalize(text):
    if not text:
        return ""

    text = text.strip().lower()

    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    # phonetic normalization
    text = text.replace("aa", "a").replace("ee", "i").replace("oo", "u")

    return text


def prepare_database():
    global DATABASE

    try:
        res = requests.get(DATA_URL, timeout=20)
        data = res.json()

        print(f"✅ Raw records: {len(data)}")

        # 🔥 Normalize tokens ONCE
        for r in data:
            tokens = r.get("search_tokens", [])

            normalized_tokens = []
            for t in tokens:
                normalized_tokens.append(normalize(t))

            r["normalized_tokens"] = normalized_tokens

        DATABASE = data

        print("✅ Tokens normalized")

    except Exception as e:
        print("❌ ERROR:", e)


prepare_database()


# -------------------------
# FRONTEND
# -------------------------
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


# -------------------------
# MATCH FUNCTION
# -------------------------
def match_score(query, tokens):
    best = 0

    for t in tokens:

        if query == t:
            return 3

        if query in t:
            best = max(best, 2)

        elif fuzz.ratio(query, t) > 80:
            best = max(best, 1)

    return best


# -------------------------
# SEARCH API (STRICT DESIGN)
# -------------------------
@app.get("/search")
def search_api(
    surname: str = "",
    firstname: str = "",
    house_no: str = "",
    age: str = ""
):
    surname = normalize(surname)
    firstname = normalize(firstname)

    # ❗ No input → no results
    if not surname and not firstname:
        return {"results": []}

    matched = []

    # -------------------------
    # STAGE 1: SEARCH
    # -------------------------
    for r in DATABASE:
        tokens = r["normalized_tokens"]

        s_score = match_score(surname, tokens) if surname else 0
        f_score = match_score(firstname, tokens) if firstname else 0

        # RULES
        if surname and not firstname:
            if s_score == 0:
                continue

        elif firstname and not surname:
            if f_score == 0:
                continue

        elif surname and firstname:
            if s_score == 0 and f_score == 0:
                continue

        score = s_score + f_score

        # boost if both match
        if s_score > 0 and f_score > 0:
            score += 5

        matched.append((score, r))

    # -------------------------
    # SORT AFTER SEARCH
    # -------------------------
    matched.sort(key=lambda x: x[0], reverse=True)

    results = [m[1] for m in matched]

    # -------------------------
    # STAGE 2: FILTER (OPTIONAL)
    # -------------------------
    if house_no:
        results = [r for r in results if r.get("house_no") == house_no]

    if age:
        results = [r for r in results if str(r.get("age")) == age]

    return {"results": results}
