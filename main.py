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

        # -------------------------
        # STRICT MATCHING (AND logic)
        # -------------------------
        def match_token(query):
            for t in tokens:
                if query == t:
                    return 3  # exact
                elif query in t:
                    return 2  # partial
                elif fuzz.ratio(query, t) > 85:
                    return 1  # fuzzy
            return 0

        # surname must match if provided
        if surname:
            s_score = match_token(surname)
            if s_score == 0:
                continue
            score += s_score

        # firstname must match if provided
        if firstname:
            f_score = match_token(firstname)
            if f_score == 0:
                continue
            score += f_score

        # house filter (strict)
        if house_no:
            if record.get("house_no") != house_no:
                continue
            score += 2

        # age filter (strict)
        if age:
            if record.get("age") != age:
                continue
            score += 2

        results.append((score, record))

    # -------------------------
    # SORT: BEST MATCH FIRST
    # -------------------------
    results.sort(key=lambda x: x[0], reverse=True)

    return {"results": [r[1] for r in results]}
