from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

app = FastAPI()

# -------------------------
# NORMALIZE (ONLY THIS)
# -------------------------
def normalize(text):
    if not text:
        return ""

    text = text.strip().lower()

    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    # light normalization only
    text = text.replace("aa", "a").replace("ee", "i").replace("oo", "u")

    return text


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

        # normalize tokens once
        r["tokens"] = [normalize(t) for t in tokens]

    DATABASE = data

load_data()


# -------------------------
# UI
# -------------------------
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()


# -------------------------
# SEARCH (STRICT)
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    if not surname and not firstname:
        return {"results": []}

    results = []

    for r in DATABASE:

        tokens = r["tokens"]

        s_match = False
        f_match = False

        # -------------------------
        # SURNAME (first token)
        # -------------------------
        if surname:
            if tokens and (
                tokens[0] == surname or
                tokens[0].startswith(surname)
            ):
                s_match = True

        # -------------------------
        # FIRST NAME (rest tokens)
        # -------------------------
        if firstname:
            for t in tokens[1:]:
                if t == firstname or t.startswith(firstname):
                    f_match = True
                    break

        # -------------------------
        # FINAL LOGIC
        # -------------------------
        if surname and not firstname:
            if s_match:
                results.append(r)

        elif firstname and not surname:
            if f_match:
                results.append(r)

        else:
            if s_match and f_match:
                results.append(r)

    return {"results": results}
