from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# -------------------------
# INIT APP (MUST BE FIRST)
# -------------------------
app = FastAPI()

# -------------------------
# LOAD DATA FROM GOOGLE DRIVE
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

DATABASE = []

try:
    response = requests.get(DATA_URL, timeout=20)

    if response.status_code == 200:
        DATABASE = response.json()
        print(f"✅ Loaded {len(DATABASE)} records")
    else:
        print("❌ Failed to fetch data:", response.status_code)

except Exception as e:
    print("❌ Error loading data:", e)


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

    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    return text.lower().strip()


# -------------------------
# MATCH FUNCTION
# -------------------------
def match_token(query, tokens):
    for t in tokens:
        if query == t:
            return 3   # exact match
        elif query in t:
            return 2   # partial match
        elif fuzz.ratio(query, t) > 85:
            return 1   # fuzzy match
    return 0


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

    for record in DATABASE:
        tokens = record.get("search_tokens", [])
        score = 0

        # -------------------------
        # STRICT AND LOGIC
        # -------------------------

        # Surname must match
        if surname:
            s_score = match_token(surname, tokens)
            if s_score == 0:
                continue
            score += s_score

        # First name must match
        if firstname:
            f_score = match_token(firstname, tokens)
            if f_score == 0:
                continue
            score += f_score

        # House number filter
        if house_no:
            if record.get("house_no") != house_no:
                continue
            score += 2

        # Age filter
        if age:
            if str(record.get("age")) != age:
                continue
            score += 2

        # If no input at all → don't return everything
        if not (surname or firstname or house_no or age):
            continue

        results.append((score, record))

    # -------------------------
    # SORT: BEST FIRST
    # -------------------------
    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
