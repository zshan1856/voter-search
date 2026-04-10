from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

app = FastAPI()

# -------------------------
# NORMALIZE
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


def close_match(q, t):
    return (
        t == q or
        t.startswith(q) or
        q.startswith(t)
    )


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
# SEARCH
# -------------------------
@app.get("/search")
def search_api(surname: str = "", firstname: str = ""):

    surname = normalize(surname)
    firstname = normalize(firstname)

    if not surname and not firstname:
        return {"results": []}

    strong = []
    partial = []

    for r in DATABASE:

        tokens = r["tokens"]

        s_match = False
        f_match = False

        # SURNAME
        if surname and tokens:
            if close_match(surname, tokens[0]):
                s_match = True

        # FIRST NAME
        if firstname:
            for t in tokens[1:]:
                if close_match(firstname, t):
                    f_match = True
                    break

        # -------------------------
        # LOGIC
        # -------------------------
        if surname and not firstname:
            if s_match:
                strong.append(r)

        elif firstname and not surname:
            if f_match:
                strong.append(r)

        else:
            if s_match and f_match:
                strong.append(r)   # best
            elif s_match or f_match:
                partial.append(r)  # fallback

    return {"results": strong + partial}
