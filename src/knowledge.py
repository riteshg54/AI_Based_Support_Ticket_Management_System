from pathlib import Path
class KnowledgeBase:
 def __init__(self,directory:str): self.documents={p.name:p.read_text(encoding='utf-8') for p in Path(directory).glob('*.md')}
 def search(self,query:str,top_k:int=3)->list[str]:
  terms={w.lower() for w in query.split() if len(w)>2}; scored=[]
  for name,text in self.documents.items():
   score=sum(1 for t in terms if t in set(text.lower().split()))
   if score: scored.append((score,f'{name}: {text}'))
  scored.sort(reverse=True,key=lambda x:x[0]); return [x[1] for x in scored[:top_k]]
