from fastapi import FastAPI
import json
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

app = FastAPI()

# Load data
with open("voter_data.json", "r") as f:
    DATABASE = json.load(f)

# -------------------------
# Normalization (IMPORTANT)
# -------------------------
def normalize(text):
    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass
    return text.lower()

# -------------------------
# Search API
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

        tokens = record["search_tokens"]

        # 🔍 Name matching
        for t in tokens:
            if surname and surname in t:
                score += 2
            elif surname and fuzz.ratio(surname, t) > 85:
                score += 1

            if firstname and firstname in t:
                score += 2
            elif firstname and fuzz.ratio(firstname, t) > 85:
                score += 1

        # 🏠 House filter (exact match)
        if house_no:
            if record["house_no"] != house_no:
                continue

        # 🎂 Age filter
        if age:
            if record["age"] != age:
                continue

        if score > 0 or house_no or age:
            results.append((score, record))

    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results[:20]]}
