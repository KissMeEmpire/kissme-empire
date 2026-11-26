import os,json,hmac,hashlib,sqlite3,time
from pathlib import Path
from urllib.parse import parse_qsl
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse

ROOT=Path(__file__).parent
DB=os.getenv("DB_PATH",str(ROOT/"game.db"))
TOKEN=os.getenv("BOT_TOKEN","")
app=FastAPI(title="KissMe Empire 2.0")

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

with connect() as c:
    c.execute('''CREATE TABLE IF NOT EXISTS players(
    uid TEXT PRIMARY KEY, username TEXT DEFAULT '', language TEXT DEFAULT 'ru',
    balance INTEGER DEFAULT 1000, energy INTEGER DEFAULT 1000, max_energy INTEGER DEFAULT 1000,
    level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0, last_energy INTEGER DEFAULT 0,
    businesses TEXT DEFAULT '{}', upgrades TEXT DEFAULT '{}', unlocked TEXT DEFAULT '["city"]')''')
    c.execute('CREATE TABLE IF NOT EXISTS daily(uid TEXT PRIMARY KEY, claimed INTEGER)')

def user_from(init):
    if not TOKEN: return {"id":"preview","username":"Preview"}
    try:
        d=dict(parse_qsl(init,keep_blank_values=True)); h=d.pop("hash")
        check="\n".join(f"{k}={v}" for k,v in sorted(d.items()))
        secret=hmac.new(b"WebAppData",TOKEN.encode(),hashlib.sha256).digest()
        if not hmac.compare_digest(h,hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()): return None
        u=json.loads(d["user"]); return u if u.get("id") else None
    except Exception: return None

def state(u):
    uid=str(u["id"]); now=int(time.time())
    with connect() as c:
        r=c.execute("SELECT * FROM players WHERE uid=?",(uid,)).fetchone()
        if not r:
            c.execute("INSERT INTO players(uid,username,last_energy) VALUES(?,?,?)",(uid,u.get("username",u.get("first_name","")),now))
            r=c.execute("SELECT * FROM players WHERE uid=?",(uid,)).fetchone()
        p=dict(r); e=min(p["max_energy"],p["energy"]+max(0,now-p["last_energy"])//3)
        if e!=p["energy"]:
            c.execute("UPDATE players SET energy=?,last_energy=? WHERE uid=?",(e,now,uid)); p["energy"]=e
        for k in ("businesses","upgrades","unlocked"): p[k]=json.loads(p[k] or "{}")
        p["user_id"]=p.pop("uid")
        return p

def save(uid,**v):
    if not v:return
    with connect() as c:
        c.execute("UPDATE players SET "+",".join(k+"=?" for k in v)+" WHERE uid=?",(*v.values(),str(uid)))

@app.get("/")
def home(): return FileResponse(ROOT/"web"/"index.html") 
@app.get("/C538937A-AB6E-46DF-B722-24CF1EE1D74A.png")
def flame_image():
    return FileResponse(ROOT/"web"/"C538937A-AB6E-46DF-B722-24CF1EE1D74A.png")
@app.get("/health")
def health(): return {"ok":True,"game":"KissMe Empire 2.0"}
@app.post("/api/state")
async def get_state(req:Request):
    d=await req.json(); u=user_from(d.get("initData",""))
    if not u: raise HTTPException(401,"Telegram verification failed")
    return state(u)
@app.post("/api/action")
async def action(req:Request):
    d=await req.json(); u=user_from(d.get("initData",""))
    if not u: raise HTTPException(401,"Telegram verification failed")
    p=state(u); uid=p["user_id"]; a=d.get("action"); key=d.get("key","")
    bal,energy,xp=p["balance"],p["energy"],p["xp"]
    b,up,un=p["businesses"],p["upgrades"],p["unlocked"]; now=int(time.time())
    if a=="tap":
        if energy<1: raise HTTPException(400,"Недостаточно энергии")
        bal+=1+up.get("tap",0); energy-=1; xp+=1
    elif a=="buy":
        catalog={"cafe":(500,"city",2),"shop":(1800,"city",7),"tower":(7000,"city",25),"villa":(25000,"island",80),"yacht":(80000,"island",220),"palace":(250000,"palace",700)}
        if key not in catalog: raise HTTPException(400,"Неизвестный бизнес")
        base,region,_=catalog[key]
        if region not in un: raise HTTPException(400,"Сначала откройте регион")
        price=int(base*1.65**b.get(key,0))
        if bal<price: raise HTTPException(400,"Недостаточно KME")
        bal-=price; b[key]=b.get(key,0)+1; xp+=25
    elif a=="upgrade":
        costs={"tap":1000,"energy":2500,"income":5000}
        if key not in costs: raise HTTPException(400,"Неизвестное улучшение")
        price=int(costs[key]*1.8**up.get(key,0))
        if bal<price: raise HTTPException(400,"Недостаточно KME")
        bal-=price; up[key]=up.get(key,0)+1
        if key=="energy": p["max_energy"]+=250; energy=p["max_energy"]
    elif a=="unlock":
        gates={"island":(30000,5),"palace":(200000,12)}
        if key not in gates: raise HTTPException(400,"Неизвестный регион")
        price,lvl=gates[key]
        if p["level"]<lvl: raise HTTPException(400,f"Нужен уровень {lvl}")
        if key in un: raise HTTPException(400,"Уже открыто")
        if bal<price: raise HTTPException(400,"Недостаточно KME")
        bal-=price; un.append(key); xp+=100
    elif a=="daily":
        with connect() as c:
            r=c.execute("SELECT claimed FROM daily WHERE uid=?",(uid,)).fetchone()
            if r and now-r["claimed"]<86400: raise HTTPException(400,"Награда уже получена сегодня")
            c.execute("INSERT OR REPLACE INTO daily VALUES(?,?)",(uid,now))
        bal+=1500; xp+=50
    elif a=="language":
        save(uid,language="en" if key=="en" else "ru")
        return state(u)
    else: raise HTTPException(400,"Неизвестное действие")
    rates={"cafe":2,"shop":7,"tower":25,"villa":80,"yacht":220,"palace":700}
    passive=sum(b.get(k,0)*v for k,v in rates.items())
    bal+=int(passive*(1+up.get("income",0)*.25))
    level=p["level"]
    while xp>=level*250: xp-=level*250; level+=1
    save(uid,balance=bal,energy=energy,max_energy=p["max_energy"],xp=xp,level=level,
         businesses=json.dumps(b),upgrades=json.dumps(up),unlocked=json.dumps(un),last_energy=now)
    return state(u)
