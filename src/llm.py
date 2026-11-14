from .models import Classification,Judgment
class MockLLM:
 def classify(self,ticket):
  text=f'{ticket.subject} {ticket.message}'.lower()
  if any(x in text for x in ['unauthorized','fraud','did not make','accessed my account']): return Classification('security','unauthorized payment/account compromise','critical','concerned',['security_incident'],.99)
  if 'password' in text or 'login' in text:return Classification('account','password/login help','low','neutral',[],.97)
  if 'api' in text or 'timeout' in text:return Classification('technical','api failure','high','frustrated',['possible_bug'],.93)
  return Classification('other','unknown','medium','neutral',[],.55)
 def judge(self,ticket,evidence,classification):
  if classification.risk_flags or classification.confidence<.80:return Judgment(False,evidence,['safe resolution not established'],.95)
  if not evidence:return Judgment(False,[],['relevant Help Centre evidence'],.95)
  return Judgment(True,evidence,[],.95)
 def respond(self,ticket,evidence,classification,judgment):
  if classification.category=='account':return 'You can reset your password from Settings → Security → Reset password. A reset email will be sent to your verified account email address.'
  return 'Thanks for contacting support. We have reviewed your request and will follow up with the next steps.'
