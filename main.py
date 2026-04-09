from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -------------------------
# INIT APP
# -------------------------
app = FastAPI()

# -------------------------
# LOAD DATA
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
            print("❌ Failed to fetch data")

    except Exception as e:
        print("❌ Error loading data:", e)

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

    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    return text.lower()

# -------------------------
# NORMALIZE TOKENS (IMPORTANT FIX)
# -------------------------
def normalize_tokens(tokens):
    normalized = []
    for t in tokens:
        try:
            t = transliterate(t, sanscript.DEVANAGARI, sanscript.ITRANS)
        except:
            pass
        normalized.append(t.lower())
    return normalized

# -------------------------
# MATCH FUNCTION
# -------------------------
def get_match_score(query, tokens):
    best = 0

    for t in tokens:
        if query == t:
            return 3
        elif query in t:
            best = max(best, 2)
        elif fuzz.ratio(query, t) > 85:
            best = max(best, 1)

    return best

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

    # Prevent empty search
    if not (surname or firstname or house_no or age):
        return {"results": []}

    for record in DATABASE:

        raw_tokens = record.get("search_tokens", [])
        tokens = normalize_tokens(raw_tokens)

        score = 0

        # -------------------------
        # SURNAME
        # -------------------------
        if surname:
            s_score = get_match_score(surname, tokens)
            if s_score == 0:
                continue
            score += s_score

        # -------------------------
        # FIRST NAME
        # -------------------------
        if firstname:
            f_score = get_match_score(firstname, tokens)
            if f_score == 0:
                continue
            score += f_score

        # -------------------------
        # HOUSE
        # -------------------------
        if house_no:
            if record.get("house_no") != house_no:
                continue
            score += 2

        # -------------------------
        # AGE
        # -------------------------
        if age:
            if str(record.get("age")) != age:
                continue
            score += 2

        results.append((score, record))

    # Sort best first
    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
