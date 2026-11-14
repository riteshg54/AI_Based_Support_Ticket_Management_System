from dataclasses import dataclass, field
from typing import Literal
Urgency=Literal['low','medium','high','critical']; Action=Literal['REPLY','ESCALATE']
@dataclass
class Ticket: id:str; customer:str; subject:str; message:str
@dataclass
class Classification: category:str; intent:str; urgency:Urgency; sentiment:str; risk_flags:list[str]=field(default_factory=list); confidence:float=0.0
@dataclass
class Judgment: answerable:bool; evidence:list[str]=field(default_factory=list); missing_information:list[str]=field(default_factory=list); confidence:float=0.0
@dataclass
class Decision: action:Action; reason:str
@dataclass
class AgentResult: ticket:Ticket; classification:Classification; judgment:Judgment; decision:Decision; response:str
