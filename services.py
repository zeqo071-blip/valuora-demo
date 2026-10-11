from statistics import median
from . import db, scraper


def verdict(title: str, price: float) -> tuple[str, float | None]:
    with db.connect() as c:
        rows = c.execute("SELECT keyword, price FROM observations").fetchall()
    t = title.lower()
    prices = [r["price"] for r in rows if r["keyword"] in t] or [r["price"] for r in rows]
    m = median(prices)
    if price < m * 0.85:
        return "ucuz", m
    if price > m * 1.15:
        return "bahalı", m
    return "uyğun", m


def analyze(user_id: int, url: str) -> dict:
    data = scraper.fetch(url)
    v, m = verdict(data["title"], data["price"])
    with db.connect() as c:
        cur = c.execute(
            "INSERT INTO analyses(user_id,url,title,price,image,verdict) VALUES(?,?,?,?,?,?)",
            (user_id, url, data["title"], data["price"], data["image"], v))
    return {"id": cur.lastrowid, "url": url, **data, "verdict": v, "market": round(m, 2)}


def history(user_id: int, limit: int = 50) -> list[dict]:
    with db.connect() as c:
        rows = c.execute("SELECT * FROM analyses WHERE user_id=? ORDER BY id DESC LIMIT ?",
                         (user_id, limit)).fetchall()
    return [dict(r) for r in rows]
