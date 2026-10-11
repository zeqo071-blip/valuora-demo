import sqlite3
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, scraper, security, services


@asynccontextmanager
async def lifespan(_):
    db.init()
    yield


app = FastAPI(title="Valuora AZ", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=config.BASE / "static"), name="static")
templates = Jinja2Templates(directory=config.BASE / "templates")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "same-origin"
    return r


def current_user(request: Request):
    uid = security.read_token(request.cookies.get("session"))
    if not uid:
        return None
    with db.connect() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def render(request, name, **ctx):
    return templates.TemplateResponse(request, name, {"user": current_user(request), **ctx})


def login_redirect(uid: int):
    r = RedirectResponse("/dashboard", 303)
    r.set_cookie("session", security.make_token(uid), httponly=True, samesite="lax",
                 secure=config.COOKIE_SECURE, max_age=7 * 86400)
    return r


@app.get("/")
def index(request: Request):
    return render(request, "index.html")


@app.get("/register")
def register_page(request: Request):
    return render(request, "auth.html", mode="register", error=None)


@app.post("/register")
def register(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    if "@" not in email or len(password) < 8:
        return render(request, "auth.html", mode="register", error="E-poçt düzgün və şifrə ən azı 8 simvol olmalıdır")
    try:
        with db.connect() as c:
            cur = c.execute("INSERT INTO users(email,pw,is_admin) VALUES(?,?,?)",
                            (email, security.hash_password(password), int(email in config.ADMIN_EMAILS)))
    except sqlite3.IntegrityError:
        return render(request, "auth.html", mode="register", error="Bu e-poçt artıq qeydiyyatdadır")
    return login_redirect(cur.lastrowid)


@app.get("/login")
def login_page(request: Request):
    return render(request, "auth.html", mode="login", error=None)


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    if security.too_many(f"{request.client.host}:{email}"):
        return render(request, "auth.html", mode="login", error="Çox cəhd. Bir az sonra yenidən yoxla")
    with db.connect() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u or not security.verify_password(password, u["pw"]):
        return render(request, "auth.html", mode="login", error="E-poçt və ya şifrə yanlışdır")
    return login_redirect(u["id"])


@app.get("/logout")
def logout():
    r = RedirectResponse("/", 303)
    r.delete_cookie("session")
    return r


@app.get("/dashboard")
def dashboard(request: Request):
    u = current_user(request)
    if not u:
        return RedirectResponse("/login", 303)
    return render(request, "dashboard.html", items=services.history(u["id"]))


@app.post("/analyze")
def analyze(request: Request, url: str = Form(...)):
    u = current_user(request)
    if not u:
        return JSONResponse({"error": "Əvvəlcə daxil ol"}, 401)
    try:
        return services.analyze(u["id"], url.strip())
    except scraper.ScrapeError as e:
        return JSONResponse({"error": str(e)}, 400)


@app.get("/api/history")
def api_history(request: Request):
    u = current_user(request)
    if not u:
        return JSONResponse({"error": "Əvvəlcə daxil ol"}, 401)
    return services.history(u["id"])
