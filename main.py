from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -------------------------
# INIT APP (ALWAYS FIRST)
# -------------------------
app = FastAPI()

# -------------------------
# LOAD DATA (ONCE ONLY)
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

# Load once at startup
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
# NORMALIZE QUERY ONLY
# -------------------------
def normalize(text):
    if not text:
        return ""

    text = text.strip().lower()

    # Marathi → English
    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    # Basic phonetic cleanup
    text = text.replace("aa", "a")
    text = text.replace("ee", "i")
    text = text.replace("oo", "u")

    return text


# -------------------------
# MATCHING FUNCTION
# -------------------------
def get_match_score(query, tokens):
    best = 0

    for t in tokens:
        t = t.lower()

        # exact
        if query == t:
            return 3

        # partial
        if query in t:
            best = max(best, 2)

        # fuzzy
        elif fuzz.ratio(query, t) > 80:
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

    # ❗ No name input → no results
    if not (surname or firstname):
        return {"results": []}

    for record in DATABASE:

        tokens = record.get("search_tokens", [])  # DO NOT normalize again

        surname_score = 0
        firstname_score = 0

        # -------------------------
        # STAGE 1: SEARCH
        # -------------------------
        if surname:
            surname_score = get_match_score(surname, tokens)

        if firstname:
            firstname_score = get_match_score(firstname, tokens)

        # Matching logic
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

        # boost if both match
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
    # SORT RESULTS
    # -------------------------
    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
