from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -------------------------
# INIT APP (FIRST ALWAYS)
# -------------------------
app = FastAPI()

# -------------------------
# LOAD DATA (SAFE + STABLE)
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

DATABASE = []

def load_data():
    global DATABASE
    try:
        response = requests.get(DATA_URL, timeout=20)

        if response.status_code == 200:
            DATABASE = response.json()
            print(f"✅ Loaded {len(DATABASE)} records")
        else:
            print("❌ Failed to fetch data:", response.status_code)

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
# NORMALIZATION (CRITICAL)
# -------------------------
def normalize(text):
    if not text:
        return ""

    text = text.strip()

    # Try Marathi → English
    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    return text.lower()


# -------------------------
# MATCH SCORING (SAFE)
# -------------------------
def get_match_score(query, tokens):
    best_score = 0

    for t in tokens:
        t = t.lower()

        # Exact match
        if query == t:
            return 3

        # Partial match
        if query in t:
            best_score = max(best_score, 2)

        # Fuzzy match
        elif fuzz.ratio(query, t) > 85:
            best_score = max(best_score, 1)

    return best_score


# -------------------------
# SEARCH API
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

    # ❗ Prevent empty search returning everything
    if not (surname or firstname or house_no or age):
        return {"results": []}

    for record in DATABASE:
        tokens = record.get("search_tokens", [])
        score = 0

        # -------------------------
        # NAME MATCHING (SMART)
        # -------------------------
        if surname:
            s_score = get_match_score(surname, tokens)
            if s_score == 0:
                continue
            score += s_score

        if firstname:
            f_score = get_match_score(firstname, tokens)
            if f_score == 0:
                continue
            score += f_score

        # -------------------------
        # STRICT FILTERS
        # -------------------------
        if house_no:
            if record.get("house_no") != house_no:
                continue
            score += 2

        if age:
            if str(record.get("age")) != age:
                continue
            score += 2

        results.append((score, record))

    # -------------------------
    # SORT BEST FIRST
    # -------------------------
    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
