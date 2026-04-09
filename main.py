from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -------------------------
# INIT APP (FIRST)
# -------------------------
app = FastAPI()

# -------------------------
# LOAD DATA (SAFE)
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

DATABASE = []

def load_data():
    global DATABASE
    try:
        res = requests.get(DATA_URL, timeout=20)
        if res.status_code == 200:
            DATABASE = res.json()
            print(f"✅ Loaded {len(DATABASE)} records")
        else:
            print("❌ Failed to fetch data:", res.status_code)
    except Exception as e:
        print("❌ Error loading data:", e)

# load once at startup
load_data()


# -------------------------
# SERVE FRONTEND
# -------------------------
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


# -------------------------
# NORMALIZATION
# -------------------------
def normalize(text):
    if not text:
        return ""

    text = text.strip()

    # Marathi → English (phonetic)
    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    return text.lower()


def normalize_tokens(tokens):
    out = []
    for t in tokens:
        try:
            t = transliterate(t, sanscript.DEVANAGARI, sanscript.ITRANS)
        except:
            pass
        out.append(t.lower())
    return out


# -------------------------
# MATCH SCORING
# -------------------------
def get_match_score(query, tokens):
    best = 0

    for t in tokens:
        # exact
        if query == t:
            return 3

        # partial
        if query in t:
            best = max(best, 2)

        # fuzzy
        elif fuzz.ratio(query, t) > 85:
            best = max(best, 1)

    return best


# -------------------------
# SEARCH API (2-STAGE)
# -------------------------
@app.get("/search")
def search_api(
    surname: str = "",
    firstname: str = "",
    house_no: str = "",
    age: str = ""
):
    results = []

    surname = normalize(surname)
    firstname = normalize(firstname)
    house_no = house_no.strip()
    age = age.strip()

    # ❗ Stage 0: no search input → return nothing
    if not (surname or firstname):
        return {"results": []}

    for record in DATABASE:

        tokens = normalize_tokens(record.get("search_tokens", []))

        surname_score = 0
        firstname_score = 0

        # -------------------------
        # STAGE 1: SEARCH (NAME)
        # -------------------------
        if surname:
            surname_score = get_match_score(surname, tokens)

        if firstname:
            firstname_score = get_match_score(firstname, tokens)

        # matching logic
        if surname and firstname:
            if surname_score == 0 and firstname_score == 0:
                continue
        elif surname:
            if surname_score == 0:
                continue
        elif firstname:
            if firstname_score == 0:
                continue

        # -------------------------
        # SCORING
        # -------------------------
        score = surname_score + firstname_score

        # boost if BOTH match
        if surname_score > 0 and firstname_score > 0:
            score += 5

        # -------------------------
        # STAGE 2: FILTER
        # -------------------------
        if house_no:
            if record.get("house_no") != house_no:
                continue

        if age:
            if str(record.get("age")) != age:
                continue

        results.append((score, record))

    # -------------------------
    # SORT
    # -------------------------
    results.sort(key=lambda x: x[0], reverse=True)

    # include relative_name in response (already present in record)
    return {"results": [r[1] for r in results]}
