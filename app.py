import json
import re
from flask import Flask, request, jsonify
from rapidfuzz import fuzz, process

app = Flask(__name__)

def load_products():
    with open("data/products.json", "r", encoding="utf-8") as f:
        return json.load(f)

CATEGORIES = sorted({p["category"] for p in load_products()})

def parse_price_clause(q):
    qlow = q.lower()
    max_price = None
    min_price = None
    m = re.search(r'between\s*\$?(\d+(?:\.\d+)?)\s*(?:and|to)\s*\$?(\d+(?:\.\d+)?)', qlow)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        min_price, max_price = min(a, b), max(a, b)
        return {"min_price": min_price, "max_price": max_price}
    m = re.search(r'(?:under|below|less than|<)\s*\$?(\d+(?:\.\d+)?)', qlow)
    if m:
        max_price = float(m.group(1))
        return {"max_price": max_price}
    m = re.search(r'(?:over|above|more than|>)\s*\$?(\d+(?:\.\d+)?)', qlow)
    if m:
        min_price = float(m.group(1))
        return {"min_price": min_price}
    m = re.search(r'\$([\d]+(?:\.\d+)?)', qlow)
    if m:
        val = float(m.group(1))
        return {"max_price": val}
    return {}

def parse_rating_clause(q):
    qlow = q.lower()
    m = re.search(r'(\d(?:\.\d)?)\s*(?:stars|star|rating)', qlow)
    if m:
        return float(m.group(1))
    if "excellent" in qlow or "great" in qlow or "best" in qlow:
        return 4.5
    if "good" in qlow or "very good" in qlow:
        return 4.0
    if "decent" in qlow:
        return 3.5
    if "poor" in qlow or "bad" in qlow:
        return 2.0
    return None

def detect_category(q):
    qlow = q.lower()
    for cat in CATEGORIES:
        if cat.lower() in qlow:
            return cat
    if "shoe" in qlow or "shoes" in qlow or "sneaker" in qlow:
        return "Footwear"
    if "headphone" in qlow or "headphones" in qlow or "audio" in qlow:
        return "Electronics"
    if "book" in qlow or "books" in qlow:
        return "Books"
    if "tent" in qlow or "camp" in qlow or "hiking" in qlow:
        return "Outdoor"
    if "wallet" in qlow or "accessor" in qlow:
        return "Accessories"
    return None

def extract_keywords(q):
    text = re.sub(r'\$[\d]+(?:\.\d+)?', ' ', q)
    text = re.sub(r'\b(under|below|over|above|between|and|to|less than|more than|stars|star|rating)\b', ' ', text, flags=re.I)
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_query(q):
    if not q:
        return {}
    q = q.strip()
    price = parse_price_clause(q)
    min_rating = parse_rating_clause(q)
    category = detect_category(q)
    keywords = extract_keywords(q)

    # detect natural-language mode hints
    qlow = q.lower()
    mode = None
    # user asking explicitly for cheapest / low price
    if any(tok in qlow for tok in ["cheapest", "cheap", "lowest price", "lowest-priced", "lowest"]):
        mode = "cheap"
    # user asking for best rated / highest rated
    if any(tok in qlow for tok in ["best-rated", "best rated", "highest rated", "top rated", "best reviews"]):
        mode = "rating"
    return {
        "raw": q,
        "max_price": price.get("max_price"),
        "min_price": price.get("min_price"),
        "min_rating": min_rating,
        "category": category,
        "keywords": keywords,
        "mode": mode  # may be None, can be overridden by query param 'mode'
    }

def filter_and_score_products(products, parsed, top_n=5):
    # Apply hard filters first (price, rating, category)
    candidates = []
    for p in products:
        if parsed.get("max_price") is not None and p["price"] > parsed["max_price"]:
            continue
        if parsed.get("min_price") is not None and p["price"] < parsed["min_price"]:
            continue
        if parsed.get("min_rating") is not None and p["rating"] < parsed["min_rating"]:
            continue
        if parsed.get("category") is not None and p["category"] != parsed["category"]:
            continue
        candidates.append(p)

    # decide weights based on 'mode'
    # default: balanced (text relevance strong)
    mode = parsed.get("mode", None)
    # possible modes: 'balanced' (default), 'rating', 'cheap'
    if mode is None:
        # caller may override via request param; default keep old weights
        fuzz_w, rating_w, price_w = 0.7, 0.2, 0.1
    elif mode == "rating":
        # emphasize rating more
        fuzz_w, rating_w, price_w = 0.5, 0.4, 0.1
    elif mode == "cheap":
        # emphasize price proximity / cheaper products
        fuzz_w, rating_w, price_w = 0.5, 0.1, 0.4
    elif mode == "text":
        # pure text relevance
        fuzz_w, rating_w, price_w = 0.85, 0.1, 0.05
    else:
        fuzz_w, rating_w, price_w = 0.7, 0.2, 0.1

    def combined_text(prod):
        return f'{prod["name"]} {prod["description"]} {prod["category"]}'

    results = []
    if parsed.get("keywords"):
        for p in candidates:
            text = combined_text(p)
            fuzzy_score = fuzz.token_sort_ratio(parsed["keywords"], text)  # 0..100
            # price proximity score
            price_score = 1.0
            if parsed.get("max_price") is not None:
                price_score = min(1.0, p["price"] / (parsed["max_price"] if parsed["max_price"] > 0 else p["price"]))
            else:
                # if no max_price but mode == 'cheap', prefer lower absolute prices:
                if mode == "cheap":
                    # map price to score in 0..1 using a simple heuristic
                    # Choose a ceiling for normalization — use max product price among candidates
                    max_price = max([c["price"] for c in candidates]) if candidates else p["price"]
                    # invert so cheaper => higher score
                    price_score = 1.0 - (p["price"] / max_price) * 0.9  # keep some spread
                    price_score = max(0.0, min(1.0, price_score))
            rating_score = p.get("rating", 0) / 5.0
            # combined weighted score
            score = (fuzz_w * (fuzzy_score / 100.0)) + (rating_w * rating_score) + (price_w * price_score)
            results.append({
                "product": p,
                "fuzzy_score": fuzzy_score,
                "rating_score": round(rating_score, 4),
                "price_score": round(price_score, 4),
                "score": round(score, 4)
            })
    else:
        # No keywords: rank by rating and price proximity, influenced by mode
        for p in candidates:
            rating_score = p.get("rating", 0) / 5.0
            price_score = 1.0
            if parsed.get("max_price") is not None:
                price_score = min(1.0, p["price"] / (parsed["max_price"] if parsed["max_price"] > 0 else p["price"]))
            else:
                if mode == "cheap":
                    max_price = max([c["price"] for c in candidates]) if candidates else p["price"]
                    price_score = 1.0 - (p["price"] / max_price) * 0.9
                    price_score = max(0.0, min(1.0, price_score))
            # use the same weight logic, with fuzzy_score=0
            score = (fuzz_w * 0.0) + (rating_w * rating_score) + (price_w * price_score)
            results.append({
                "product": p,
                "fuzzy_score": 0,
                "rating_score": round(rating_score, 4),
                "price_score": round(price_score, 4),
                "score": round(score, 4)
            })

    # final sort: by score desc, but if mode == 'cheap' and user likely wants the absolute cheapest,
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

@app.route("/categories")
def categories():
    return jsonify({"categories": CATEGORIES})

@app.route("/search")
def search():
    q = request.args.get("q", "")
    top_n = int(request.args.get("n",5))
    parsed = parse_query(q)
    # allow request param to override mode: ?mode=rating or ?mode=cheap or ?mode=balanced
    mode_param = request.args.get("mode")
    if mode_param:
        parsed["mode"] = mode_param.lower()
    products = load_products()
    results = filter_and_score_products(products, parsed, top_n=top_n)
    resp = {
        "query": q,
        "parsed": parsed,
        "total_candidates": len(results),
        "results": [
            {
                "id": r["product"]["id"],
                "name": r["product"]["name"],
                "price": r["product"]["price"],
                "category": r["product"]["category"],
                "rating": r["product"]["rating"],
                "description": r["product"]["description"],
                "fuzzy_score": r["fuzzy_score"],
                "rating_score": r["rating_score"],
                "price_score": r["price_score"],
                "score": r["score"]
            }
            for r in results
        ]
    }
    return jsonify(resp)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
