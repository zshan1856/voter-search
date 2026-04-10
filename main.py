from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from rapidfuzz import fuzz
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

app = FastAPI()

# -------------------------
# NORMALIZATION
# -------------------------
def normalize(text):
    if not text:
        return ""

    text = text.strip().lower()

    try:
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except:
        pass

    text = text.replace("aa", "a").replace("ee", "i").replace("oo", "u")

    return text


def remove_vowels(text):
    return "".join([c for c in text if c not in "aeiou"])


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

        norm_tokens = [normalize(t) for t in tokens]

        r["tokens"] = norm_tokens
        r["tokens_nv"] = [remove_vowels(t) for t in norm_tokens]

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
# SEARCH
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    surname_nv = remove_vowels(surname)
    firstname_nv = remove_vowels(firstname)

    if not surname and not firstname:
        return {"results": []}

    strong = []
    medium = []

    for r in DATABASE:

        tokens = r["tokens"]
        tokens_nv = r["tokens_nv"]

        s_match = False
        f_match = False

        # -------------------------
        # SURNAME (STRICT)
        # -------------------------
        if surname:
            if surname == tokens[0]:
                s_match = True
            elif surname_nv == tokens_nv[0]:
                s_match = True
            elif fuzz.ratio(surname, tokens[0]) > 90:
                s_match = True

        # -------------------------
        # FIRST NAME (STRICT)
        # -------------------------
        if firstname:
            for i in range(1, len(tokens)):
                if firstname == tokens[i]:
                    f_match = True
                elif firstname_nv == tokens_nv[i]:
                    f_match = True
                elif fuzz.ratio(firstname, tokens[i]) > 90:
                    f_match = True

        # -------------------------
        # FILTER LOGIC
        # -------------------------
        if surname and not firstname:
            if not s_match:
                continue
            strong.append(r)

        elif firstname and not surname:
            if not f_match:
                continue
            strong.append(r)

        else:
            if s_match and f_match:
                strong.append(r)
            elif s_match or f_match:
                medium.append(r)

    return {"results": strong + medium}
