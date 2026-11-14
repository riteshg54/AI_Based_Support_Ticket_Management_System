from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI(title='SupportAI API')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
@app.get('/health')
def health():return {'status':'online','service':'support-ticket-ai'}
@app.get('/api/tickets')
def tickets():return {'tickets':[{'id':'T-001','status':'REPLY'},{'id':'T-002','status':'ESCALATE'},{'id':'T-003','status':'ESCALATE'}]}
