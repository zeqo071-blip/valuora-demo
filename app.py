"""Valuora AZ — tək fayllı backend. Çalışdır: uvicorn app:app --reload"""
import ipaddress, json, re, socket, urllib.request
from html.parser import HTMLParser
from pathlib import Path
from statistics import median
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
app = FastAPI(title="Valuora AZ")

# Demo bazar müşahidələri (açar söz -> qiymətlər, AZN)
MARKET = {"iphone": [1900, 2100, 2300], "samsung": [900, 1100, 1300],
          "noutbuk": [1200, 1600, 2000], "qulaqlıq": [60, 90, 130]}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # yönləndirmələr bloklanır (SSRF qoruması)


def check_url(url: str):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("Yalnız http/https linkləri qəbul olunur")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or 80)
    except socket.gaierror:
        raise ValueError("Ünvan tapılmadı")
    if any(not ipaddress.ip_address(i[4][0]).is_global for i in infos):
        raise ValueError("Daxili/qadağan olunmuş ünvan")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.ld, self.title = {}, [], ""
        self.in_ld = self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("property") or a.get("name")) and a.get("content"):
            self.meta[(a.get("property") or a.get("name")).lower()] = a["content"]
        elif tag == "script" and a.get("type") == "application/ld+json":
            self.in_ld = True
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_ld = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, d):
        if self.in_ld:
            self.ld.append(d)
        elif self.in_title:
            self.title += d


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def num(v):
    m = re.search(r"\d+(?:[.,]\d+)?", str(v).replace(" ", ""))
    return float(m.group().replace(",", ".")) if m else None


def scrape(url: str) -> dict:
    check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "ValuoraBot/1.0"})
    try:
        raw = urllib.request.build_opener(NoRedirect).open(req, timeout=8).read(1_000_000)
    except Exception as e:
        raise ValueError(f"Səhifə açılmadı: {e}")
    p = Page()
    p.feed(raw.decode("utf-8", "ignore"))
    title, image, price = p.meta.get("og:title") or p.title.strip(), p.meta.get("og:image"), None
    for block in p.ld:
        try:
            for n in walk(json.loads(block)):
                offers = n.get("offers")
                for o in offers if isinstance(offers, list) else [offers]:
                    if isinstance(o, dict):
                        price = price or num(o.get("price") or o.get("lowPrice") or "")
                if n.get("@type") == "Product":
                    title = n.get("name") or title
                    img = n.get("image")
                    image = image or (img[0] if isinstance(img, list) and img else img if isinstance(img, str) else None)
        except ValueError:
            continue
    price = price or num(p.meta.get("product:price:amount") or p.meta.get("og:price:amount") or "")
    if not price:
        raise ValueError("Qiymət tapılmadı (JS ilə render olunan səhifə ola bilər)")
    return {"title": (title or "Adsız məhsul")[:200], "price": price, "image": image}


def judge(title: str, price: float):
    t = title.lower()
    prices = [p for k, ps in MARKET.items() if k in t for p in ps] or [p for ps in MARKET.values() for p in ps]
    m = median(prices)
    return ("ucuz" if price < m * 0.85 else "bahalı" if price > m * 1.15 else "uyğun"), round(m, 2)


class Req(BaseModel):
    url: str


@app.post("/api/analyze")
def analyze(req: Req):
    try:
        data = scrape(req.url.strip())
    except ValueError as e:
        raise HTTPException(400, str(e))
    verdict, market = judge(data["title"], data["price"])
    return {**data, "url": req.url, "verdict": verdict, "market": market}


@app.get("/")
def index():
    return FileResponse(BASE / "index.html")


@app.get("/style.css")
def css():
    return FileResponse(BASE / "style.css", media_type="text/css")


@app.get("/app.js")
def js():
    return FileResponse(BASE / "app.js", media_type="application/javascript")
