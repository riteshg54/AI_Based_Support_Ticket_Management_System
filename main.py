import json,sys
from src.llm import MockLLM
from src.knowledge import KnowledgeBase
from src.models import Ticket
from src.pipeline import SupportPipeline
p=sys.argv[1] if len(sys.argv)>1 else 'tickets/ticket_001.json'
with open(p,encoding='utf-8') as f:t=Ticket(**json.load(f))
r=SupportPipeline(MockLLM(),KnowledgeBase('help_centre')).run(t)
print(json.dumps({'ticket_id':t.id,'classification':r.classification.__dict__,'judgment':r.judgment.__dict__,'decision':r.decision.__dict__,'response':r.response},indent=2))
