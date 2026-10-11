import sqlite3
from . import config

# Demo bazar müşahidələri: (açar söz, qiymət AZN)
DEMO = [("iphone", 1900), ("iphone", 2100), ("iphone", 2300), ("samsung", 900),
        ("samsung", 1100), ("samsung", 1300), ("noutbuk", 1200), ("noutbuk", 1600),
        ("noutbuk", 2000), ("qulaqlıq", 60), ("qulaqlıq", 90), ("qulaqlıq", 130)]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
  pw TEXT NOT NULL, is_admin INTEGER DEFAULT 0, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
  url TEXT, title TEXT, price REAL, image TEXT, verdict TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, keyword TEXT, price REAL);
"""


def connect():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with connect() as c:
        c.executescript(SCHEMA)
        if not c.execute("SELECT 1 FROM observations").fetchone():
            c.executemany("INSERT INTO observations(keyword,price) VALUES(?,?)", DEMO)
