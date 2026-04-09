from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

app = FastAPI()

# -------------------------
# LOAD DATA FROM GOOGLE DRIVE
# -------------------------
DATA_URL = "https://drive.google.com/uc?export=download&id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

try:
    response = requests.get(DATA_URL, timeout=15)

    if response.status_code != 200:
        raise Exception("Failed to fetch data")

    DATABASE = response.json()

    print(f"✅ Loaded {len(DATABASE)} records")

except Exception as e:
    print("❌ ERROR LOADING DATA:", e)
    DATABASE = []


# -------------------------
# SERVE FRONTEND
# -------------------------
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


# -------------------------
# NORMALIZATION (Marathi + English)
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
        score = 0
        tokens = record.get("search_tokens", [])

        # 🔍 Name matching
        for t in tokens:
            if surname:
                if surname in t:
                    score += 2
                elif fuzz.ratio(surname, t) > 85:
                    score += 1

            if firstname:
                if firstname in t:
                    score += 2
                elif fuzz.ratio(firstname, t) > 85:
                    score += 1

        # 🏠 House filter
        if house_no:
            if record.get("house_no") != house_no:
                continue

        # 🎂 Age filter
        if age:
            if record.get("age") != age:
                continue

        # Add result if relevant
        if score > 0 or house_no or age:
            results.append((score, record))

    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results[:20]]}
