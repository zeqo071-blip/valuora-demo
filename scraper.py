import ipaddress, json, re, socket, urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse


class ScrapeError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # yönləndirmələr bloklanır


def _check_url(url: str):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ScrapeError("Yalnız http/https linkləri qəbul olunur")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or 80)
    except socket.gaierror:
        raise ScrapeError("Ünvan tapılmadı")
    for i in infos:
        if not ipaddress.ip_address(i[4][0]).is_global:
            raise ScrapeError("Daxili/qadağan olunmuş ünvan")


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.ld, self._ld, self._t, self.title = {}, [], False, False, ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = a.get("property") or a.get("name")
            if k and a.get("content"):
                self.meta[k.lower()] = a["content"]
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld = True
        elif tag == "title":
            self._t = True

    def handle_endtag(self, tag):
        self._ld = self._t = False if tag in ("script", "title") else self._ld

    def handle_data(self, d):
        if self._ld:
            self.ld.append(d)
        elif self._t:
            self.title += d


def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def _num(v):
    m = re.search(r"\d+(?:[.,]\d+)?", str(v).replace(" ", ""))
    return float(m.group().replace(",", ".")) if m else None


def fetch(url: str) -> dict:
    _check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "ValuoraBot/1.0"})
    try:
        raw = urllib.request.build_opener(_NoRedirect).open(req, timeout=8).read(1_000_000)
    except Exception as e:
        raise ScrapeError(f"Səhifə açılmadı: {e}")
    p = _P()
    p.feed(raw.decode("utf-8", "ignore"))
    title, price, image = p.meta.get("og:title") or p.title.strip(), None, p.meta.get("og:image")
    for block in p.ld:
        try:
            for n in _walk(json.loads(block)):
                if "offers" in n or "price" in n:
                    offers = n.get("offers", n)
                    for o in offers if isinstance(offers, list) else [offers]:
                        price = price or (_num(o.get("price") or o.get("lowPrice")) if isinstance(o, dict) else None)
                if n.get("@type") == "Product":
                    title = n.get("name") or title
                    img = n.get("image")
                    image = image or (img[0] if isinstance(img, list) and img else img if isinstance(img, str) else None)
        except ValueError:
            continue
    price = price or _num(p.meta.get("product:price:amount") or p.meta.get("og:price:amount") or "")
    if not price:
        raise ScrapeError("Qiymət tapılmadı (JS ilə render olunan səhifə ola bilər)")
    return {"title": (title or "Adsız məhsul")[:200], "price": price, "image": image}
