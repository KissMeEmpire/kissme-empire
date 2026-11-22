import os, json, time, hmac, hashlib, sqlite3
from urllib.parse import parse_qsl
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "kissme_empire.sqlite3")
WEB_DIR = Path(__file__).parent / "web"
app = FastAPI(title="KissMe Empire API")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

BUSINESSES = [
    {"cost": 500, "profit": 3}, {"cost": 2500, "profit": 12},
    {"cost": 12000, "profit": 65}, {"cost": 65000, "profit": 350},
]
ENERGY_MAX = 500

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS players(
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            coins REAL NOT NULL DEFAULT 1000, energy REAL NOT NULL DEFAULT 500,
            tap_power INTEGER NOT NULL DEFAULT 1, owned TEXT NOT NULL DEFAULT '[0,0,0,0]',
            updated REAL NOT NULL DEFAULT 0)""")

def verify_init_data(init_data: str):
    if not BOT_TOKEN:
        raise HTTPException(503, "BOT_TOKEN is not configured. Set it in the server environment.")
    if not init_data:
        raise HTTPException(401, "Open the game from its Telegram bot.")
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash")
        auth_date = int(pairs.get("auth_date", "0"))
    except Exception:
        raise HTTPException(401, "Invalid Telegram initData")
    if time.time() - auth_date > 86400:
        raise HTTPException(401, "Telegram session expired. Reopen the Mini App.")
    data_check = "\n".join(f"{k}={v}" for k,v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(401, "Telegram signature check failed")
    try:
        user = json.loads(pairs["user"])
        return user
    except Exception:
        raise HTTPException(401, "Telegram user data missing")

def get_player(user):
    uid = int(user["id"])
    now = time.time()
    with db() as c:
        row = c.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
        if row is None:
            c.execute("INSERT INTO players(user_id,username,first_name,updated) VALUES(?,?,?,?)",
                      (uid, user.get("username",""), user.get("first_name","Player"), now))
            row = c.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
        elapsed = max(0, min(3600, now - row["updated"]))
        owned = json.loads(row["owned"])
        income = sum(owned[i] * BUSINESSES[i]["profit"] for i in range(4))
        coins = row["coins"] + income * elapsed
        energy = min(ENERGY_MAX, row["energy"] + elapsed * 2)
        c.execute("UPDATE players SET coins=?,energy=?,updated=? WHERE user_id=?", (coins, energy, now, uid))
        row = c.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
    return row

def response(row):
    owned = json.loads(row["owned"])
    income = sum(owned[i] * BUSINESSES[i]["profit"] for i in range(4))
    return {"coins": int(row["coins"]), "energy": int(row["energy"]), "tap_power": row["tap_power"],
            "owned": owned, "income": income, "level": 1 + int(max(0,row["coins"]-1000)//10000)}

class Payload(BaseModel):
    initData: str = ""
    business: int | None = None

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")

@app.post("/api/state")
def state(p: Payload):
    user = verify_init_data(p.initData)
    return response(get_player(user))

@app.post("/api/tap")
def tap(p: Payload):
    user = verify_init_data(p.initData)
    row = get_player(user)
    if row["energy"] < 1:
        raise HTTPException(400, "Not enough energy")
    with db() as c:
        c.execute("UPDATE players SET coins=coins+tap_power, energy=energy-1, updated=? WHERE user_id=?",
                  (time.time(), int(user["id"])))
        row = c.execute("SELECT * FROM players WHERE user_id=?", (int(user["id"]),)).fetchone()
    return response(row)

@app.post("/api/buy")
def buy(p: Payload):
    user = verify_init_data(p.initData)
    if p.business is None or p.business not in range(4):
        raise HTTPException(400, "Unknown business")
    row = get_player(user)
    b = BUSINESSES[p.business]
    if row["coins"] < b["cost"]:
        raise HTTPException(400, "Not enough KME")
    owned = json.loads(row["owned"])
    owned[p.business] += 1
    with db() as c:
        c.execute("UPDATE players SET coins=coins-?, owned=?, updated=? WHERE user_id=?",
                  (b["cost"], json.dumps(owned), time.time(), int(user["id"])))
        row = c.execute("SELECT * FROM players WHERE user_id=?", (int(user["id"]),)).fetchone()
    return response(row)

@app.get("/health")
def health():
    return {"ok": True, "app": "KissMe Empire"}
