from .models import AgentResult,Decision
class SupportPipeline:
 def __init__(self,llm,kb):self.llm=llm;self.kb=kb
 def run(self,t):
  c=self.llm.classify(t);j=self.llm.judge(t,self.kb.search(f'{t.subject} {t.message}'),c)
  if c.risk_flags:d=Decision('ESCALATE','High-risk or security-related ticket')
  elif c.confidence<.80:d=Decision('ESCALATE','Classification confidence is below threshold')
  elif not j.answerable:d=Decision('ESCALATE','Ticket cannot be safely answered from verified knowledge')
  else:d=Decision('REPLY','Ticket is supported by verified Help Centre evidence')
  response=f'Escalation required: {d.reason}. Customer issue: {t.subject}.' if d.action=='ESCALATE' else self.llm.respond(t,j.evidence,c,j)
  return AgentResult(t,c,j,d,response)
