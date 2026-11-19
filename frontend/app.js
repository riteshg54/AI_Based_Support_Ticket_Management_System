const API="http://localhost:8000";
let token=localStorage.getItem("supportai_token"),me=JSON.parse(localStorage.getItem("supportai_user")||"null");
const app=document.getElementById("app");
const esc=s=>String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
async function api(path,opt={}){
  opt.headers={...(opt.headers||{}),"Content-Type":"application/json",...(token?{Authorization:"Bearer "+token}:{})};
  const r=await fetch(API+path,opt),d=await r.json().catch(()=>({}));
  if(!r.ok) throw Error(d.detail||"Request failed");
  return d;
}
function loginView(){
 app.innerHTML='<div class="auth"><div class="auth-card"><div class="brand">Support<span>AI</span></div><h1>Welcome back</h1><p>Sign in to your support workspace.</p><input id="email" type="email" placeholder="Email" autocomplete="email"><input id="password" type="password" placeholder="Password" autocomplete="current-password"><button onclick="login()">Sign in</button><p id="err" class="error"></p><button class="ghost" onclick="registerView()">Create customer account</button></div></div>';
}
function registerView(){
 app.innerHTML='<div class="auth"><div class="auth-card"><div class="brand">Support<span>AI</span></div><h1>Create account</h1><p>Start managing your support requests.</p><input id="name" placeholder="Full name" autocomplete="name"><input id="email" type="email" placeholder="Email" autocomplete="email"><input id="password" type="password" placeholder="Password" autocomplete="new-password"><button onclick="register()">Create account</button><p id="err" class="error"></p><button class="ghost" onclick="loginView()">Back to login</button></div></div>';
}
async function login(){
 try{
  const d=await api("/api/auth/login",{method:"POST",body:JSON.stringify({email:email.value.trim(),password:password.value})});
  token=d.access_token;me=d.user;
  localStorage.setItem("supportai_token",token);localStorage.setItem("supportai_user",JSON.stringify(me));
  render();
 }catch(e){err.textContent=e.message}
}
async function register(){
 try{
  await api("/api/auth/register",{method:"POST",body:JSON.stringify({name:name.value.trim(),email:email.value.trim(),password:password.value})});
  loginView(); document.getElementById("err").textContent="Account created. Please sign in.";
 }catch(e){err.textContent=e.message}
}
function logout(){localStorage.clear();token=null;me=null;loginView()}
async function render(){
 if(!token)return loginView();
 try{me=await api("/api/auth/me");localStorage.setItem("supportai_user",JSON.stringify(me))}
 catch(e){return logout()}
 app.innerHTML='<div class="layout"><aside><div class="brand">Support<span>AI</span></div><div class="profile"><b>'+esc(me.name)+'</b><small>'+esc(me.role.toUpperCase())+'</small></div><nav><button onclick="loadDashboard()">Dashboard</button><button onclick="loadTickets()">Tickets</button>'+(me.role==="user"?'<button onclick="newTicket()">+ Raise Ticket</button>':'')+(me.role==="admin"?'<button onclick="loadTeam()">Support Team</button>':'')+'</nav><button class="logout" onclick="logout()">Logout</button></aside><main><header><div><h1 id="title">Dashboard</h1><p id="subtitle">AI-powered customer support workspace</p></div><div class="avatar">'+esc((me.name||"?")[0].toUpperCase())+'</div></header><section id="content"></section></main></div>'+(me.role!=="admin"?'<button class="chat" onclick="toggleChat()">AI</button><div id="chatbox" class="chatbox hidden"></div>':'');
 loadDashboard();
}
async function loadDashboard(){
 document.getElementById("title").textContent=me.role==="admin"?"Admin Overview":me.role==="junior"?"Agent Workspace":"Customer Portal";
 document.getElementById("subtitle").textContent=me.role==="admin"?"Real-time support operations and performance":"Manage your support requests in one place";
 const d=await api("/api/tickets"),t=d.tickets;
 if(me.role==="admin"){const s=await api("/api/admin/stats");document.getElementById("content").innerHTML=adminDashboard(s,t)}
 else document.getElementById("content").innerHTML='<div class="welcome"><h2>Need help?</h2><p>Raise a ticket and our support team will take care of it.</p>'+(me.role==="user"?'<button onclick="newTicket()">Raise a ticket</button>':'')+'</div>'+ticketTable(t);
}
function adminDashboard(s,t){
 const bar=(label,val,total)=>'<div class="barrow"><span>'+esc(label)+'</span><div class="bar"><i style="width:'+Math.min(100,total?val/total*100:0)+'%"></i></div><b>'+val+'</b></div>';
 const recent=(s.recent||[]).slice().reverse().map(x=>'<div class="mini-day"><span>'+esc(x.day)+'</span><b>'+x.count+'</b></div>').join("");
 return '<div class="stats six"><div><b>'+s.total+'</b><small>Total Tickets</small></div><div><b>'+s.open+'</b><small>Open</small></div><div><b>'+s.in_progress+'</b><small>In Progress</small></div><div><b>'+s.resolved+'</b><small>Resolved</small></div><div><b>'+s.critical+'</b><small>Critical</small></div><div><b>'+s.resolution_rate+'%</b><small>Resolution Rate</small></div></div>'+
 '<div class="analytics-grid"><div class="panel"><div class="panelhead"><h2>Ticket health</h2><span class="muted">'+s.total+' total</span></div>'+bar("Open",s.open,s.total)+bar("In Progress",s.in_progress,s.total)+bar("Resolved",s.resolved,s.total)+bar("Escalated",s.escalated,s.total)+'</div>'+
 '<div class="panel"><div class="panelhead"><h2>Priority mix</h2></div>'+["CRITICAL","HIGH","MEDIUM","LOW"].map(p=>bar(p,(s.by_priority||{})[p]||0,s.total)).join("")+'</div></div>'+
 '<div class="analytics-grid"><div class="panel"><div class="panelhead"><h2>Tickets created</h2><span class="muted">Last 14 days</span></div><div class="mini-chart">'+recent+'</div></div>'+
 '<div class="panel"><div class="panelhead"><h2>Agent performance</h2></div><div class="agent-list">'+(s.by_agent||[]).map(a=>'<div class="agent"><div><b>'+esc(a.agent)+'</b><small>'+a.total+' handled</small></div><strong>'+a.resolved+' resolved</strong></div>').join("")+'</div></div></div>'+
 '<div class="panel"><div class="panelhead"><h2>Critical queue</h2><button onclick="loadTickets()">View all</button></div>'+ticketTable(t.filter(x=>x.priority==="CRITICAL").slice(0,5),true)+'</div>';
}
function ticketTable(t,compact=false){
 return '<div class="tickets">'+(t.length?t.map(x=>'<div class="ticket" onclick="openTicket('+x.id+')"><div><b>'+esc(x.public_id)+' · '+esc(x.subject)+'</b><p>'+esc(x.message).slice(0,110)+'</p></div><div><span class="status '+x.status+'">'+x.status+'</span><small>'+esc(x.assigned_name||"Unassigned")+'</small></div></div>').join(""):'<p class="muted">No tickets found.</p>')+'</div>';
}
async function loadTickets(){
 document.getElementById("title").textContent="Tickets";document.getElementById("subtitle").textContent="Search and manage support requests";
 const d=await api("/api/tickets");
 document.getElementById("content").innerHTML='<div class="panel"><div class="panelhead"><h2>'+(me.role==="user"?"My tickets":"Ticket queue")+'</h2><button onclick="loadTickets()">Refresh</button></div>'+ticketTable(d.tickets)+'</div>';
}
function newTicket(){
 document.getElementById("title").textContent="Raise a Ticket";
 document.getElementById("subtitle").textContent="Tell us what you need help with";
 document.getElementById("content").innerHTML='<div class="panel form"><h2>What can we help with?</h2><input id="tsub" placeholder="Subject"><select id="tprio"><option>MEDIUM</option><option>LOW</option><option>HIGH</option><option>CRITICAL</option></select><textarea id="tmsg" placeholder="Describe your issue clearly"></textarea><button onclick="createTicket()">Submit ticket</button><p id="formerr" class="error"></p></div>';
}
async function createTicket(){
 try{const d=await api("/api/tickets",{method:"POST",body:JSON.stringify({subject:tsub.value.trim(),message:tmsg.value.trim(),priority:tprio.value})});await openTicketByPublic(d.ticket_id)}
 catch(e){formerr.textContent=e.message}
}
async function openTicket(id){const d=await api("/api/tickets"),t=d.tickets.find(x=>x.id===id);if(t)showTicket(t)}
async function openTicketByPublic(pid){const d=await api("/api/tickets"),t=d.tickets.find(x=>x.public_id===pid);if(t)showTicket(t)}
async function showTicket(t){
 document.getElementById("title").textContent=t.public_id;document.getElementById("subtitle").textContent="Ticket details and activity";
 const rr=await api("/api/tickets/"+t.id+"/replies"),juniors=me.role==="admin"?(await api("/api/admin/juniors")).juniors:[];
 document.getElementById("content").innerHTML='<div class="panel"><div class="tickettop"><div><h2>'+esc(t.subject)+'</h2><p>'+esc(t.message)+'</p></div><span class="status '+t.status+'">'+t.status+'</span></div><div class="meta">Priority: <b>'+t.priority+'</b> · Customer: <b>'+esc(t.customer||me.name)+'</b> · Assigned: <b>'+esc(t.assigned_name||"Unassigned")+'</b></div>'+(me.role==="admin"?'<div class="admin-controls"><select id="st"><option>OPEN</option><option>IN_PROGRESS</option><option>ESCALATED</option><option>RESOLVED</option><option>CLOSED</option></select><select id="ass"><option value="">Unassigned</option>'+juniors.map(j=>'<option value="'+j.id+'">'+esc(j.name)+'</option>').join("")+'</select><input id="note" placeholder="Internal admin note" value="'+esc(t.admin_note||"")+'"><button onclick="updateTicket('+t.id+')">Save / Transfer</button></div>':'')+'<div class="replies">'+rr.replies.map(r=>'<div class="reply"><b>'+esc(r.name)+' · '+esc(r.role)+'</b><p>'+esc(r.message)+'</p></div>').join("")+'</div><div class="replybox"><textarea id="replymsg" placeholder="Write a reply..."></textarea><button onclick="sendReply('+t.id+')">Send reply</button></div></div>';
 if(me.role==="admin"){st.value=t.status;if(t.assigned_to)ass.value=t.assigned_to}
}
async function updateTicket(id){await api("/api/admin/tickets/"+id,{method:"PATCH",body:JSON.stringify({status:st.value,assigned_to:ass.value?Number(ass.value):null,admin_note:note.value})});openTicket(id)}
async function sendReply(id){if(!replymsg.value.trim())return;await api("/api/tickets/"+id+"/replies",{method:"POST",body:JSON.stringify({message:replymsg.value})});openTicket(id)}
async function loadTeam(){
 document.getElementById("title").textContent="Support Team";document.getElementById("subtitle").textContent="Manage junior support agents";
 const d=await api("/api/admin/juniors");
 document.getElementById("content").innerHTML='<div class="panel"><h2>Junior agents</h2>'+(d.juniors.length?d.juniors.map(j=>'<div class="team"><div><b>'+esc(j.name)+'</b><small>'+esc(j.email)+'</small></div><span>Support Agent</span></div>').join(""):"<p class='muted'>No junior agents yet.</p>")+'</div>';
}
function toggleChat(){const b=document.getElementById("chatbox");b.classList.toggle("hidden");if(!b.innerHTML)b.innerHTML='<div class="chathead">SupportAI Assistant</div><div id="msgs" class="msgs"><p class="bot">Hi! I can help with common support questions before you raise a ticket.</p></div><div class="chatinput"><input id="chatmsg" placeholder="Ask anything..." onkeydown="if(event.key===\'Enter\')chat()"><button onclick="chat()">Send</button></div>'}
async function chat(){if(!chatmsg.value.trim())return;const m=chatmsg.value;msgs.innerHTML+='<p class="userchat">'+esc(m)+'</p>';chatmsg.value="";const d=await api("/api/chat",{method:"POST",body:JSON.stringify({message:m})});msgs.innerHTML+='<p class="bot">'+esc(d.reply)+'</p>';msgs.scrollTop=msgs.scrollHeight}
if(token)render();else loginView();