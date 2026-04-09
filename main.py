from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from rapidfuzz import fuzz

app = FastAPI()

# Load data
import requests

DATA_URL = "https://drive.google.com/uc?id=1tfYsu-wHTUANOIT9pc_NYlQQiytlE01U"

response = requests.get(DATA_URL)
DATABASE = response.json()

# Serve HTML
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html") as f:
        return f.read()

# Search logic
def search(query, database):
    query = query.lower()
    results = []

    for record in database:
        score = 0

        for token in record["search_tokens"]:
            if query in token:
                score += 2
            elif fuzz.ratio(query, token) > 85:
                score += 1

        if score > 0:
            results.append((score, record))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:20]]

@app.get("/search")
def search_api(q: str):
    return {"results": search(q, DATABASE)}