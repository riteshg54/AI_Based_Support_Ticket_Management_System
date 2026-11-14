import os, sqlite3, hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

DB=os.getenv("SUPPORTAI_DB","supportai.db"); SECRET=os.getenv("SUPPORTAI_SECRET","change-this-secret-in-production"); ALGO="HS256"
security=HTTPBearer(auto_error=False)
app=FastAPI(title="SupportAI API",version="1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

class AuthRequest(BaseModel): email:EmailStr; password:str
class RegisterRequest(AuthRequest): name:str
class TicketUpdate(BaseModel): status:str; admin_note:str=""

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def hash_password(password,salt=None):
 salt=salt or secrets.token_hex(16)
 digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),120000).hex()
 return salt+"$"+digest
def verify_password(password,stored):
 salt,digest=stored.split("$",1)
 candidate=hash_password(password,salt).split("$",1)[1]
 return hmac.compare_digest(candidate,digest)

def setup():
 c=db()
 c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','admin')));
 CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT,public_id TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL,subject TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',priority TEXT NOT NULL DEFAULT 'MEDIUM',admin_note TEXT DEFAULT '',created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));""")
 if not c.execute("SELECT id FROM users WHERE email=?",("admin@supportai.local",)).fetchone():
  c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",("SupportAI Admin","admin@supportai.local",hash_password("Admin@12345"),"admin"))
 if c.execute("SELECT COUNT(*) n FROM tickets").fetchone()["n"]==0:
  if not c.execute("SELECT id FROM users WHERE email=?",("demo@supportai.local",)).fetchone():
   c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",("Demo Customer","demo@supportai.local",hash_password("User@12345"),"user"))
  uid=c.execute("SELECT id FROM users WHERE email=?",("demo@supportai.local",)).fetchone()["id"]; now=datetime.now(timezone.utc).isoformat()
  for pid,sub,msg,status,priority in [("T-1001","Password reset","I forgot my password and need help resetting it.","RESOLVED","LOW"),("T-1002","API keeps timing out","Our production API has been timing out for two hours.","ESCALATED","HIGH"),("T-1003","Unauthorized payment","I see a payment I did not make.","ESCALATED","CRITICAL")]:
   c.execute("INSERT INTO tickets(public_id,user_id,subject,message,status,priority,created_at) VALUES(?,?,?,?,?,?,?)",(pid,uid,sub,msg,status,priority,now))
 c.commit(); c.close()

@app.on_event("startup")
def startup(): setup()

def current_user(credentials:Optional[HTTPAuthorizationCredentials]=Depends(security)):
 if not credentials: raise HTTPException(401,"Authentication required")
 try:
  payload=jwt.decode(credentials.credentials,SECRET,algorithms=[ALGO]); c=db(); u=c.execute("SELECT id,name,email,role FROM users WHERE id=?",(payload["sub"],)).fetchone(); c.close()
  if not u: raise HTTPException(401,"User not found")
  return dict(u)
 except Exception: raise HTTPException(401,"Invalid or expired token")
def admin_only(user=Depends(current_user)):
 if user["role"]!="admin": raise HTTPException(403,"Admin access required")
 return user

@app.get("/health")
def health(): return {"status":"online","service":"support-ticket-ai"}
@app.post("/api/auth/register")
def register(data:RegisterRequest):
 c=db()
 try:
  c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",(data.name,data.email.lower(),hash_password(data.password),"user")); c.commit(); return {"message":"Account created"}
 except sqlite3.IntegrityError: raise HTTPException(409,"Email already registered")
 finally: c.close()
@app.post("/api/auth/login")
def login(data:AuthRequest):
 c=db(); u=c.execute("SELECT * FROM users WHERE email=?",(data.email.lower(),)).fetchone(); c.close()
 if not u or not verify_password(data.password,u["password_hash"]): raise HTTPException(401,"Invalid email or password")
 token=jwt.encode({"sub":str(u["id"]),"role":u["role"],"exp":datetime.now(timezone.utc)+timedelta(hours=8)},SECRET,algorithm=ALGO)
 return {"access_token":token,"token_type":"bearer","user":{"id":u["id"],"name":u["name"],"email":u["email"],"role":u["role"]}}
@app.get("/api/auth/me")
def me(user=Depends(current_user)): return user
@app.get("/api/tickets")
def tickets(user=Depends(current_user)):
 c=db()
 rows=c.execute("SELECT t.*,u.name customer,u.email FROM tickets t JOIN users u ON u.id=t.user_id ORDER BY t.id DESC").fetchall() if user["role"]=="admin" else c.execute("SELECT * FROM tickets WHERE user_id=? ORDER BY id DESC",(user["id"],)).fetchall()
 c.close(); return {"tickets":[dict(r) for r in rows]}
@app.patch("/api/admin/tickets/{ticket_id}")
def update_ticket(ticket_id:int,data:TicketUpdate,user=Depends(admin_only)):
 if data.status not in {"OPEN","IN_PROGRESS","ESCALATED","RESOLVED","CLOSED"}: raise HTTPException(400,"Invalid ticket status")
 c=db(); cur=c.execute("UPDATE tickets SET status=?,admin_note=? WHERE id=?",(data.status,data.admin_note,ticket_id)); c.commit(); c.close()
 if not cur.rowcount: raise HTTPException(404,"Ticket not found")
 return {"message":"Ticket updated"}
@app.get("/api/admin/stats")
def stats(user=Depends(admin_only)):
 c=db(); total=c.execute("SELECT COUNT(*) n FROM tickets").fetchone()["n"]; escalated=c.execute("SELECT COUNT(*) n FROM tickets WHERE status='ESCALATED'").fetchone()["n"]; open_=c.execute("SELECT COUNT(*) n FROM tickets WHERE status IN ('OPEN','IN_PROGRESS')").fetchone()["n"]; resolved=c.execute("SELECT COUNT(*) n FROM tickets WHERE status IN ('RESOLVED','CLOSED')").fetchone()["n"]; c.close()
 return {"total":total,"escalated":escalated,"open":open_,"resolved":resolved}
