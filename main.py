from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# ✅ MUST BE FIRST
app = FastAPI()

# -------------------------
# LOAD DATA
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

try:
    response = requests.get(DATA_URL, timeout=15)
    DATABASE = response.json()
    print(f"Loaded {len(DATABASE)} records")
except Exception as e:
    print("Error loading data:", e)
    DATABASE = []

# -------------------------
# SERVE HTML
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

    for record in DATABASE:
        tokens = record.get("search_tokens", [])
        score = 0

        def match_token(query):
            for t in tokens:
                if query == t:
                    return 3
                elif query in t:
                    return 2
                elif fuzz.ratio(query, t) > 85:
                    return 1
            return 0

        if surname:
            s = match_token(surname)
            if s == 0:
                continue
            score += s

        if firstname:
            f = match_token(firstname)
            if f == 0:
                continue
            score += f

        if house_no:
            if record.get("house_no") != house_no:
                continue
            score += 2

        if age:
            if record.get("age") != age:
                continue
            score += 2

        results.append((score, record))

    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
