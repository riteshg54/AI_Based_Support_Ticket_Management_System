import os, sqlite3, hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

DB=os.getenv("SUPPORTAI_DB","supportai.db")
SECRET=os.getenv("SUPPORTAI_SECRET","change-this-secret-in-production")
ALGO="HS256"
security=HTTPBearer(auto_error=False)
app=FastAPI(title="SupportAI API",version="2.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

class AuthRequest(BaseModel): email:EmailStr; password:str
class RegisterRequest(AuthRequest): name:str
class TicketCreate(BaseModel): subject:str; message:str; priority:str="MEDIUM"
class TicketUpdate(BaseModel):
    status:Optional[str]=None; priority:Optional[str]=None; admin_note:str=""; assigned_to:Optional[int]=None
class ReplyCreate(BaseModel): message:str
class ChatRequest(BaseModel): message:str

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def hash_password(password,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+"$"+hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),120000).hex()

def verify_password(password,stored):
    salt,digest=stored.split("$",1)
    return hmac.compare_digest(hash_password(password,salt).split("$",1)[1],digest)

def setup():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('user','junior','admin')));
    CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT,public_id TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL,subject TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',priority TEXT NOT NULL DEFAULT 'MEDIUM',admin_note TEXT DEFAULT '',assigned_to INTEGER,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id),FOREIGN KEY(assigned_to) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS replies(id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id INTEGER NOT NULL,user_id INTEGER NOT NULL,message TEXT NOT NULL,internal INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,FOREIGN KEY(ticket_id) REFERENCES tickets(id),FOREIGN KEY(user_id) REFERENCES users(id));
    """)
    seeds=[("SupportAI Admin","admin@supportai.local","Admin@12345","admin"),("Junior Support","junior@supportai.local","Junior@12345","junior"),("Demo Customer","demo@supportai.local","User@12345","user")]
    for name,email,pw,role in seeds:
        if not c.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():
            c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",(name,email,hash_password(pw),role))
    c.commit(); c.close()

@app.on_event("startup")
def startup(): setup()

def current_user(credentials:Optional[HTTPAuthorizationCredentials]=Depends(security)):
    if not credentials: raise HTTPException(401,"Authentication required")
    try:
        payload=jwt.decode(credentials.credentials,SECRET,algorithms=[ALGO])
        c=db(); u=c.execute("SELECT id,name,email,role FROM users WHERE id=?",(int(payload["sub"]),)).fetchone(); c.close()
        if not u: raise HTTPException(401,"User not found")
        return dict(u)
    except HTTPException: raise
    except Exception: raise HTTPException(401,"Invalid or expired token")

def admin_only(user=Depends(current_user)):
    if user["role"]!="admin": raise HTTPException(403,"Admin access required")
    return user

@app.get("/health")
def health(): return {"status":"online","service":"support-ticket-ai","version":"2.0"}

@app.post("/api/auth/register")
def register(data:RegisterRequest):
    c=db()
    try:
        c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",(data.name,data.email.lower(),hash_password(data.password),"user")); c.commit()
        return {"message":"Account created"}
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
    if user["role"]=="user":
        rows=c.execute("SELECT t.*,u.name customer,a.name assigned_name FROM tickets t JOIN users u ON u.id=t.user_id LEFT JOIN users a ON a.id=t.assigned_to WHERE t.user_id=? ORDER BY t.id DESC",(user["id"],)).fetchall()
    else:
        rows=c.execute("SELECT t.*,u.name customer,u.email,a.name assigned_name FROM tickets t JOIN users u ON u.id=t.user_id LEFT JOIN users a ON a.id=t.assigned_to ORDER BY t.id DESC").fetchall()
    c.close(); return {"tickets":[dict(r) for r in rows]}

@app.post("/api/tickets")
def create_ticket(data:TicketCreate,user=Depends(current_user)):
    if user["role"]!="user": raise HTTPException(403,"Only customers can raise tickets")
    if data.priority not in {"LOW","MEDIUM","HIGH","CRITICAL"}: raise HTTPException(400,"Invalid priority")
    c=db(); now=datetime.now(timezone.utc).isoformat(); n=c.execute("SELECT COUNT(*) n FROM tickets").fetchone()["n"]+1001; pid=f"T-{n}"
    c.execute("INSERT INTO tickets(public_id,user_id,subject,message,priority,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(pid,user["id"],data.subject,data.message,data.priority,now,now)); c.commit(); c.close()
    return {"message":"Ticket created","ticket_id":pid}

@app.get("/api/tickets/{ticket_id}/replies")
def get_replies(ticket_id:int,user=Depends(current_user)):
    c=db(); t=c.execute("SELECT * FROM tickets WHERE id=?",(ticket_id,)).fetchone()
    if not t: c.close(); raise HTTPException(404,"Ticket not found")
    if user["role"]=="user" and t["user_id"]!=user["id"]: c.close(); raise HTTPException(403,"Forbidden")
    rows=c.execute("SELECT r.*,u.name,u.role FROM replies r JOIN users u ON u.id=r.user_id WHERE r.ticket_id=? ORDER BY r.id",(ticket_id,)).fetchall(); c.close()
    return {"replies":[dict(r) for r in rows]}

@app.post("/api/tickets/{ticket_id}/replies")
def reply(ticket_id:int,data:ReplyCreate,user=Depends(current_user)):
    c=db(); t=c.execute("SELECT * FROM tickets WHERE id=?",(ticket_id,)).fetchone()
    if not t: c.close(); raise HTTPException(404,"Ticket not found")
    if user["role"]=="user" and t["user_id"]!=user["id"]: c.close(); raise HTTPException(403,"Forbidden")
    now=datetime.now(timezone.utc).isoformat()
    c.execute("INSERT INTO replies(ticket_id,user_id,message,created_at) VALUES(?,?,?,?)",(ticket_id,user["id"],data.message,now))
    c.execute("UPDATE tickets SET updated_at=? WHERE id=?",(now,ticket_id)); c.commit(); c.close()
    return {"message":"Reply added"}

@app.patch("/api/admin/tickets/{ticket_id}")
def update_ticket(ticket_id:int,data:TicketUpdate,user=Depends(admin_only)):
    if data.status and data.status not in {"OPEN","IN_PROGRESS","ESCALATED","RESOLVED","CLOSED"}: raise HTTPException(400,"Invalid status")
    if data.priority and data.priority not in {"LOW","MEDIUM","HIGH","CRITICAL"}: raise HTTPException(400,"Invalid priority")
    c=db(); t=c.execute("SELECT id FROM tickets WHERE id=?",(ticket_id,)).fetchone()
    if not t: c.close(); raise HTTPException(404,"Ticket not found")
    if data.assigned_to is not None:
        a=c.execute("SELECT id,role FROM users WHERE id=?",(data.assigned_to,)).fetchone()
        if not a or a["role"]!="junior": c.close(); raise HTTPException(400,"Ticket can only be transferred to a junior")
    fields=[]; vals=[]
    for col,val in [("status",data.status),("priority",data.priority),("admin_note",data.admin_note if data.admin_note else None),("assigned_to",data.assigned_to)]:
        if val is not None: fields.append(col+"=?"); vals.append(val)
    fields.append("updated_at=?"); vals.append(datetime.now(timezone.utc).isoformat()); vals.append(ticket_id)
    c.execute("UPDATE tickets SET "+",".join(fields)+" WHERE id=?",vals); c.commit(); c.close()
    return {"message":"Ticket updated"}

@app.get("/api/admin/juniors")
def juniors(user=Depends(admin_only)):
    c=db(); rows=c.execute("SELECT id,name,email FROM users WHERE role='junior' ORDER BY name").fetchall(); c.close(); return {"juniors":[dict(r) for r in rows]}

@app.post("/api/admin/juniors")
def create_junior(data:RegisterRequest,user=Depends(admin_only)):
    c=db()
    try:
        c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'junior')",(data.name,data.email.lower(),hash_password(data.password))); c.commit(); return {"message":"Junior account created"}
    except sqlite3.IntegrityError: raise HTTPException(409,"Email already registered")
    finally: c.close()

@app.get("/api/admin/stats")
def stats(user=Depends(admin_only)):
    c=db(); out={}
    for k,q in {"total":"SELECT COUNT(*) n FROM tickets","escalated":"SELECT COUNT(*) n FROM tickets WHERE status='ESCALATED'","open":"SELECT COUNT(*) n FROM tickets WHERE status IN ('OPEN','IN_PROGRESS')","resolved":"SELECT COUNT(*) n FROM tickets WHERE status IN ('RESOLVED','CLOSED')","unassigned":"SELECT COUNT(*) n FROM tickets WHERE assigned_to IS NULL AND status NOT IN ('RESOLVED','CLOSED')"}.items(): out[k]=c.execute(q).fetchone()["n"]
    c.close(); return out

@app.post("/api/chat")
def chatbot(data:ChatRequest,user=Depends(current_user)):
    msg=data.message.lower()
    if any(x in msg for x in ["password","login","forgot"]): answer="You can reset your password from Settings → Security → Reset password. A reset email is sent to your verified email."
    elif any(x in msg for x in ["refund","billing","charged"]): answer="For billing issues, include the transaction date and reference number. You can also raise a support ticket."
    elif any(x in msg for x in ["api","timeout","error"]): answer="API incidents may require investigation. Raise a ticket with the endpoint, timestamp and error message."
    elif "ticket" in msg or "support" in msg: answer="I can help you understand your ticket or guide you to raise a new support request."
    else: answer="I’m not confident enough to answer that safely. Please raise a ticket and our support team will review it."
    return {"reply":answer,"escalate":answer.startswith("I’m not confident")}

if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=8000)
