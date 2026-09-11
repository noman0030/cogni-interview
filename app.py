import streamlit as st
import json, random, re, time, uuid
from datetime import datetime

st.set_page_config(page_title="COGNI AI Interview", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")
ADMIN_PASSWORD = "cogni2026"

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{font-family:'Inter',sans-serif}.main{background:#0e1117}
.stApp{background:linear-gradient(135deg,#0e1117,#161b22)}
.ch{background:linear-gradient(90deg,#12395B,#1D9E75);padding:16px 24px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.ch h1{color:white;font-size:24px;margin:0;font-weight:600}.ch span{color:rgba(255,255,255,0.7);font-size:13px}
.ab{background:#1c2333;border-left:3px solid #1D9E75;padding:14px 18px;border-radius:0 12px 12px 12px;margin:10px 0;color:#e6edf3;font-size:15px;line-height:1.6;max-width:85%}
.ub{background:#12395B;border-right:3px solid #58a6ff;padding:14px 18px;border-radius:12px 0 12px 12px;margin:10px 0 10px auto;color:#e6edf3;font-size:15px;line-height:1.6;max-width:85%;text-align:right}
.sb{display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:600;margin:6px 4px}
.sh{background:#1D9E75;color:white}.sm{background:#B8860B;color:white}.sl{background:#e94560;color:white}
.sc{background:#1c2333;border:1px solid #2d333b;border-radius:12px;padding:16px;text-align:center}
.sc h3{color:#1D9E75;font-size:28px;margin:0}.sc p{color:#8b949e;font-size:12px;margin:4px 0 0}
.pb{height:6px;background:#2d333b;border-radius:3px;overflow:hidden}.pf{height:100%;background:linear-gradient(90deg,#1D9E75,#58a6ff);border-radius:3px;transition:width 0.5s}
.fp{background:#1c2333;border:2px dashed #2d333b;border-radius:12px;padding:30px;text-align:center;color:#484f58;font-size:14px}
.tb{display:inline-block;padding:4px 12px;border-radius:12px;background:#2d333b;color:#8b949e;font-size:12px;margin-left:8px}
.ls{background:#1c2333;border:1px solid #2d333b;border-radius:12px;padding:40px;text-align:center;max-width:400px;margin:60px auto}
#MainMenu{visibility:hidden}footer{visibility:hidden}header{visibility:hidden}
</style>""", unsafe_allow_html=True)

@st.cache_data
def load_qb():
    try:
        with open("question_bank.json") as f: return json.load(f)
    except: return [{"question":"Tell me about yourself.","category":"General HR","source":"default"}]
qbank = load_qb()

@st.cache_resource
def get_client():
    try:
        from google import genai
        k = st.secrets.get("GEMINI_KEY","")
        if k: return genai.Client(api_key=k)
    except: pass
    return None
client = get_client()

def ask_ai(prompt, retries=3):
    if not client: return None
    for i in range(retries):
        try:
            r = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            return r.text.strip()
        except Exception as e:
            if ("503" in str(e) or "429" in str(e)) and i < retries-1: time.sleep(2**i); continue
            return None
    return None

def extract_resume(f):
    import pdfplumber
    text = ""
    try:
        with pdfplumber.open(f) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t: text += t + "\n"
    except: pass
    if len(text.strip()) < 50:
        try:
            from pdf2image import convert_from_bytes; import pytesseract
            pages = convert_from_bytes(f.getvalue(), dpi=200)
            text = "".join(pytesseract.image_to_string(p)+"\n" for p in pages)
        except: text = "Could not extract."
    sdb = ["Python","Java","JavaScript","SQL","React","Node.js","HTML","CSS","Database","Machine Learning","Web Development","Testing","API","DevOps","Cloud","Security","Git","Agile","Data Structures"]
    found = [s for s in sdb if s.lower() in text.lower()]
    m = re.search(r'(\d+)\+?\s*years?', text, re.IGNORECASE)
    yr = int(m.group(1)) if m else None
    nm = re.sub(r'^[\\,\s]+','',text.strip().split('\n')[0]).strip() if text.strip() else "Candidate"
    return {"name":nm,"skills":found,"years_experience":yr,"raw_text":text}

def gen_q(skills, profile, prev=None):
    yr = profile.get("years_experience",0); ss = ", ".join(skills[:6])
    if prev:
        q = ask_ai(f"You are a friendly HR interviewer. Candidate said: '{prev}'\nAsk ONE short friendly follow up. Use 'you'. Output ONLY the question.")
        if q and q.endswith('?') and len(q.split())>=5: return q,"Gemini"
        return "Can you tell me more about that?","Bank"
    else:
        sk = random.choice(skills) if skills else "general"
        q = ask_ai(f"You are a friendly HR interviewer. Candidate has {yr} years in: {ss}.\nAsk ONE specific friendly question about {sk}. Output ONLY the question.")
        if q and q.endswith('?') and len(q.split())>=5: return q,"Gemini"
        ms = [q for q in qbank if q["category"].lower()==sk.lower()]
        if ms: return random.choice(ms)["question"],"Bank"
        return f"Tell me about your experience with {sk}.","Default"

def eval_ans(question, answer):
    if len(answer.strip().split())<3: return {"score":0,"verdict":"No answer","feedback":"Please share more details."}
    raw = ask_ai(f"Evaluate interview answer. Be friendly.\nQ: {question}\nA: {answer}\nSCORE: <0 to 10>\nVERDICT: <words>\nFEEDBACK: <one sentence>")
    if raw:
        try:
            sc = int(re.search(r'SCORE:\s*(\d+)',raw).group(1))
            vd = re.search(r'VERDICT:\s*(.+)',raw).group(1).strip()
            fb = re.search(r'FEEDBACK:\s*(.+)',raw).group(1).strip()
            return {"score":min(sc,10),"verdict":vd,"feedback":fb}
        except: pass
    w=len(answer.split()); t=["index","query","cache","api","database","model","test","performance","optimize","algorithm"]
    h=sum(1 for x in t if x in answer.lower()); sc=min(10,(w//12)+(h*2))
    vd="Strong" if sc>=7 else "Adequate" if sc>=4 else "Needs work"
    return {"score":sc,"verdict":vd,"feedback":"Good effort. Add more detail."}

def gen_report(data):
    tr = "\n".join(f"Q: {e['question']}\nA: {e['answer']}\nScore: {e['score']}/10" for e in data["interactions"])
    r = ask_ai(f"Write friendly interview report.\nCANDIDATE: {data['name']}, {data['years']} years\nOVERALL: {data['overall']}/10\nTRANSCRIPT:\n{tr}\nSUMMARY: (2 sentences)\nSTRENGTHS: (2 points)\nAREAS TO IMPROVE: (2 points)\nRECOMMENDATION: (Strong Hire / Hire / Borderline / Do Not Proceed)")
    if r: return r
    rc="Strong Hire" if data["overall"]>=8 else "Hire" if data["overall"]>=6 else "Borderline" if data["overall"]>=4 else "Do Not Proceed"
    return f"SUMMARY: {data['name']} scored {data['overall']}/10.\nRECOMMENDATION: {rc}"

def voice_ui(question, qnum):
    cid=f"v{qnum}_{random.randint(1000,9999)}"
    sq=question.replace("'","\\'").replace('"','\\"').replace('\n',' ').replace('`','')
    return f"""
    <div style="background:#1c2333;border-radius:12px;padding:20px;margin:10px 0;border:1px solid #2d333b;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
            <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#1D9E75,#12395B);display:flex;align-items:center;justify-content:center;font-size:16px;">🤖</div>
            <span style="color:#1D9E75;font-weight:500;">AI Interviewer</span>
            <button onclick="spk_{cid}()" style="margin-left:auto;padding:6px 14px;background:#1D9E75;color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;">🔊 Listen Again</button>
        </div>
        <div style="text-align:center;padding:10px 0;">
            <p id="st_{cid}" style="color:#8b949e;font-size:14px;margin:0 0 12px;">Click mic to speak (Hindi + English supported)</p>
            <button id="mb_{cid}" onclick="tog_{cid}()" style="width:70px;height:70px;border-radius:50%;background:#2d333b;border:2px solid #1D9E75;cursor:pointer;font-size:30px;transition:all 0.3s;">🎤</button>
        </div>
        <div id="trbox_{cid}" style="margin-top:14px;padding:14px;background:#0e1117;border-radius:8px;min-height:60px;color:#e6edf3;font-size:15px;text-align:left;display:none;line-height:1.6;">
        </div>
        <div id="btnrow_{cid}" style="margin-top:10px;text-align:right;display:none;">
            <button onclick="cpy_{cid}()" id="cpybtn_{cid}" style="padding:8px 18px;background:#1D9E75;color:white;border:none;border-radius:6px;cursor:pointer;font-size:14px;font-weight:500;">📋 Copy Answer</button>
            <button onclick="clr_{cid}()" style="padding:8px 18px;background:#2d333b;color:#8b949e;border:none;border-radius:6px;cursor:pointer;font-size:14px;margin-left:6px;">🗑 Clear</button>
        </div>
    </div>
    <script>
    (function(){{
        let rc=null,on=false,ft='';
        window.spk_{cid}=function(){{
            speechSynthesis.cancel();
            const u=new SpeechSynthesisUtterance('{sq}');
            u.rate=0.95;u.lang='en-US';
            speechSynthesis.speak(u);
        }};
        setTimeout(()=>spk_{cid}(),500);

        window.cpy_{cid}=function(){{
            const text=document.getElementById('trbox_{cid}').innerText;
            navigator.clipboard.writeText(text).then(()=>{{
                const btn=document.getElementById('cpybtn_{cid}');
                const orig=btn.innerHTML;
                btn.innerHTML='✅ Copied! Paste in text box below';
                btn.style.background='#12395B';
                setTimeout(()=>{{btn.innerHTML=orig;btn.style.background='#1D9E75';}},2500);
            }});
        }};
        window.clr_{cid}=function(){{
            ft='';
            document.getElementById('trbox_{cid}').innerHTML='';
            document.getElementById('trbox_{cid}').style.display='none';
            document.getElementById('btnrow_{cid}').style.display='none';
        }};

        window.tog_{cid}=function(){{
            if(on){{
                rc.stop();on=false;
                document.getElementById('mb_{cid}').style.background='#2d333b';
                document.getElementById('mb_{cid}').style.borderColor='#1D9E75';
                document.getElementById('st_{cid}').textContent='✅ Done. Copy the text and paste in answer box below.';
                document.getElementById('st_{cid}').style.color='#1D9E75';
                document.getElementById('btnrow_{cid}').style.display='block';
            }}else{{
                ft='';
                try{{
                    rc=new(window.SpeechRecognition||window.webkitSpeechRecognition)();
                    rc.continuous=true;
                    rc.interimResults=true;
                    rc.lang='en-IN';
                    rc.onresult=function(e){{
                        let im='';ft='';
                        for(let i=0;i<e.results.length;i++){{
                            if(e.results[i].isFinal)ft+=e.results[i][0].transcript+' ';
                            else im+=e.results[i][0].transcript;
                        }}
                        const bx=document.getElementById('trbox_{cid}');
                        bx.style.display='block';
                        bx.innerHTML='<span style="color:#e6edf3;">'+ft+'</span><span style="color:#484f58;font-style:italic;">'+im+'</span>';
                    }};
                    rc.onerror=function(e){{
                        document.getElementById('st_{cid}').textContent='Error: '+e.error+' — try again or use text input';
                        document.getElementById('st_{cid}').style.color='#e94560';
                    }};
                    rc.start();on=true;
                    document.getElementById('mb_{cid}').style.background='#e94560';
                    document.getElementById('mb_{cid}').style.borderColor='#e94560';
                    document.getElementById('st_{cid}').textContent='🔴 Listening... speak now, click mic again to stop';
                    document.getElementById('st_{cid}').style.color='#e94560';
                }}catch(err){{
                    document.getElementById('st_{cid}').textContent='Speech not supported. Use Chrome/Edge. Type below instead.';
                    document.getElementById('st_{cid}').style.color='#e94560';
                }}
            }}
        }};
    }})();
    </script>"""

for k,v in {"page":"home","profile":None,"started":False,"q_idx":0,"questions":[],"interactions":[],"sid":None,"total_q":6,"complete":False,"sessions":[],"q_time":None,"hr_auth":False,"dev_auth":False}.items():
    if k not in st.session_state: st.session_state[k]=v

with st.sidebar:
    st.markdown('<div style="text-align:center;padding:10px 0 20px;"><div style="width:50px;height:50px;border-radius:50%;background:linear-gradient(135deg,#12395B,#1D9E75);display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:22px;">🧠</div><h2 style="color:white;margin:0;font-size:20px;">COGNI</h2><p style="color:#8b949e;font-size:12px;margin:2px 0 0;">AI Interview Platform</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🏠  Home",use_container_width=True): st.session_state.page="home";st.rerun()
    if st.button("🎤  Interview Room",use_container_width=True): st.session_state.page="interview";st.rerun()
    if st.button("📊  HR Dashboard  🔒",use_container_width=True): st.session_state.page="hr";st.rerun()
    if st.button("🔧  Dev Dashboard  🔒",use_container_width=True): st.session_state.page="dev";st.rerun()
    st.markdown("---")
    st.markdown(f'<div style="padding:10px;"><p style="color:#8b949e;font-size:12px;margin:0;">Interviews</p><p style="color:#1D9E75;font-size:24px;font-weight:600;margin:0;">{len(st.session_state.sessions)}</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div class="fp">📷 Face Detection<br><span style="font-size:11px;">Phase 2</span></div>', unsafe_allow_html=True)

if st.session_state.page=="home":
    st.markdown('<div class="ch"><div><h1>🏢 COGNI AI Interview Platform</h1><span>Conversational AI Driven Recruitment</span></div></div>', unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    for col,ic,ti,ds in [(c1,"🎤","Interview Room","Voice based AI interview"),(c2,"📊","HR Dashboard","Reports and decisions"),(c3,"🔧","Dev Dashboard","System diagnostics"),(c4,"🧠","Smart Engine","17,000+ questions")]:
        with col: st.markdown(f'<div class="sc"><h3>{ic}</h3><p style="color:#e6edf3;font-size:14px;font-weight:500;">{ti}</p><p>{ds}</p></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    ca,cb=st.columns(2)
    with ca:
        if st.button("🎤  Start Interview",use_container_width=True,type="primary"): st.session_state.page="interview";st.rerun()
    with cb:
        if st.button("📊  Dashboard",use_container_width=True): st.session_state.page="hr";st.rerun()

elif st.session_state.page=="interview":
    st.markdown('<div class="ch"><div><h1>🎤 Interview Room</h1><span>Voice and text based AI interview</span></div></div>', unsafe_allow_html=True)
    if not st.session_state.profile:
        st.markdown("### 📄 Upload your resume to begin")
        up=st.file_uploader("Resume PDF",type=["pdf"],label_visibility="collapsed")
        if up:
            with st.spinner("🔍 Reading resume..."):
                pr=extract_resume(up);st.session_state.profile=pr;st.session_state.sid=str(uuid.uuid4())[:8]
                st.session_state.q_idx=0;st.session_state.interactions=[];st.session_state.complete=False;st.session_state.started=False
                qs=[];us=[s for s in pr["skills"] if any(q["category"].lower()==s.lower() for q in qbank)][:3] or ["Python"]
                for sk in us:
                    q,src=gen_q(pr["skills"],pr);qs.append({"question":q,"source":src,"type":"main","skill":sk})
                    qs.append({"question":"","source":"","type":"followup","skill":sk})
                st.session_state.questions=qs;st.session_state.total_q=len([q for q in qs if q["type"]=="main"]);st.rerun()
    elif not st.session_state.complete:
        pr=st.session_state.profile
        ci,cp=st.columns([1,2])
        with ci: st.markdown(f'<div class="sc"><p style="color:#1D9E75;font-size:11px;">CANDIDATE</p><h3 style="font-size:18px;color:#e6edf3;">{pr["name"]}</h3><p>{pr.get("years_experience","N/A")} years</p></div>', unsafe_allow_html=True)
        with cp:
            ans=len(st.session_state.interactions);tot=st.session_state.total_q*2;pct=int((ans/max(tot,1))*100)
            st.markdown(f'<div style="background:#1c2333;border-radius:8px;padding:12px 16px;margin:10px 0;"><div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="color:#8b949e;font-size:12px;">Progress</span><span style="color:#1D9E75;font-size:12px;">{ans}/{tot}</span></div><div class="pb"><div class="pf" style="width:{pct}%;"></div></div></div>', unsafe_allow_html=True)
        st.markdown("---")
        if not st.session_state.started:
            st.session_state.started=True
            st.markdown(f'<div class="ab">🤖 Welcome {pr["name"]}! I have reviewed your resume. You can answer by speaking or typing. Let us begin!</div>', unsafe_allow_html=True)
        for e in st.session_state.interactions:
            st.markdown(f'<div class="ab">🤖 {e["question"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ub">🗣️ {e["answer"]}</div>', unsafe_allow_html=True)
            s=e["score"];css="sh" if s>=7 else "sm" if s>=4 else "sl"
            st.markdown(f'<div style="text-align:right;"><span class="sb {css}">{s}/10 · {e["verdict"]}</span><span class="tb">⏱️ {e.get("time_taken","N/A")}s</span></div>', unsafe_allow_html=True)
        idx=len(st.session_state.interactions);qs=st.session_state.questions
        if idx<len(qs):
            qd=qs[idx]
            if qd["type"]=="followup" and qd["question"]=="":
                la=st.session_state.interactions[-1]["answer"] if st.session_state.interactions else ""
                fq,fs=gen_q(pr["skills"],pr,prev=la);qd["question"]=fq;qd["source"]=fs;qs[idx]=qd
            cq=qd["question"];ql="Follow up" if qd["type"]=="followup" else f"Question {(idx//2)+1}"
            st.markdown(f'<div class="ab">🤖 <strong>{ql}:</strong> {cq}</div>', unsafe_allow_html=True)
            if st.session_state.q_time is None: st.session_state.q_time=time.time()
            st.components.v1.html(voice_ui(cq,idx),height=260)
            ti=st.text_area("Your Answer",placeholder="✍️ Paste your speech here (from Copy button above) OR type your answer...",height=100,key=f"ti_{idx}",label_visibility="collapsed")
            if st.button("📩 Submit Answer",use_container_width=True,type="primary",key=f"sub_{idx}"):
                a=(ti or "").strip()
                if a:
                    el=round(time.time()-st.session_state.q_time,1) if st.session_state.q_time else 0
                    with st.spinner("🧠 Evaluating..."): ev=eval_ans(cq,a)
                    st.session_state.interactions.append({"question":cq,"answer":a,"score":ev["score"],"verdict":ev["verdict"],"feedback":ev["feedback"],"source":qd["source"],"type":qd["type"],"skill":qd.get("skill",""),"time_taken":el,"timestamp":datetime.now().isoformat()})
                    st.session_state.q_time=None;st.rerun()
                else: st.warning("Please speak or type your answer.")
        else: st.session_state.complete=True;st.rerun()
    else:
        pr=st.session_state.profile;ints=st.session_state.interactions
        ts=sum(e["score"] for e in ints);ov=round(ts/max(len(ints),1),1);at=round(sum(e.get("time_taken",0) for e in ints)/max(len(ints),1),1)
        st.markdown(f'<div class="ab">🤖 Thank you {pr["name"]}! Score: <strong>{ov}/10</strong></div>', unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns(4)
        with c1: st.markdown(f'<div class="sc"><h3>{ov}</h3><p>Score</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="sc"><h3>{len(ints)}</h3><p>Questions</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="sc"><h3>{max(e["score"] for e in ints) if ints else 0}</h3><p>Best</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="sc"><h3>{at}s</h3><p>Avg Time</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        with st.spinner("📄 Generating report..."):
            data={"name":pr["name"],"years":pr.get("years_experience","N/A"),"overall":ov,"interactions":ints};rpt=gen_report(data)
        st.markdown("### 📄 Report")
        st.markdown(f'<div style="background:#1c2333;padding:20px;border-radius:12px;border:1px solid #2d333b;color:#e6edf3;line-height:1.8;white-space:pre-wrap;">{rpt}</div>', unsafe_allow_html=True)
        rec={"session_id":st.session_state.sid,"name":pr["name"],"skills":pr["skills"],"years":pr.get("years_experience"),"overall":ov,"interactions":ints,"report":rpt,"avg_time":at,"timestamp":datetime.now().isoformat()}
        if not any(s["session_id"]==rec["session_id"] for s in st.session_state.sessions): st.session_state.sessions.append(rec)
        if st.button("🔄 New Interview",use_container_width=True,type="primary"):
            for k in ["profile","started","q_idx","questions","interactions","sid","complete","q_time"]: st.session_state[k]=None if k in ["profile","sid","q_time"] else False if k in ["started","complete"] else 0 if k=="q_idx" else []
            st.rerun()

elif st.session_state.page=="hr":
    st.markdown('<div class="ch"><div><h1>📊 HR Dashboard</h1><span>Candidate reports</span></div></div>', unsafe_allow_html=True)
    if not st.session_state.hr_auth:
        st.markdown('<div class="ls"><p style="font-size:36px;margin:0 0 10px;">🔒</p><p style="color:#e6edf3;">HR personnel only.</p></div>', unsafe_allow_html=True)
        pwd=st.text_input("Password",type="password",key="hr_pwd")
        if st.button("Unlock",use_container_width=True,type="primary"):
            if pwd==ADMIN_PASSWORD: st.session_state.hr_auth=True;st.rerun()
            else: st.error("Wrong password.")
    else:
        ss=st.session_state.sessions
        if not ss: st.markdown('<div style="text-align:center;padding:60px;color:#8b949e;"><p style="font-size:48px;">📭</p><p>No interviews yet.</p></div>', unsafe_allow_html=True)
        else:
            avg=round(sum(s["overall"] for s in ss)/len(ss),1);hire=sum(1 for s in ss if s["overall"]>=6);tqs=sum(len(s["interactions"]) for s in ss);avt=round(sum(s.get("avg_time",0) for s in ss)/len(ss),1)
            c1,c2,c3,c4=st.columns(4)
            with c1: st.markdown(f'<div class="sc"><h3>{len(ss)}</h3><p>Interviews</p></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="sc"><h3>{avg}</h3><p>Avg Score</p></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="sc"><h3>{hire}</h3><p>Recommended</p></div>', unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="sc"><h3>{avt}s</h3><p>Avg Time</p></div>', unsafe_allow_html=True)
            st.markdown("---")
            for session in reversed(ss):
                sc=session["overall"]
                with st.expander(f"📋 {session['name']} — {sc}/10 — {session['timestamp'][:10]}"):
                    st.markdown(f"**ID:** {session['session_id']} | **Skills:** {', '.join(session['skills'][:6])} | **Exp:** {session.get('years','N/A')} yrs")
                    for i,e in enumerate(session["interactions"],1):
                        se=e["score"];ce="sh" if se>=7 else "sm" if se>=4 else "sl"
                        st.markdown(f'<div style="background:#1c2333;padding:12px;border-radius:8px;margin:6px 0;border-left:3px solid {"#1D9E75" if e["type"]=="main" else "#58a6ff"};"><strong style="color:#1D9E75;">Q{i}:</strong> <span style="color:#e6edf3;">{e["question"]}</span><br><strong style="color:#58a6ff;">A:</strong> <span style="color:#c9d1d9;">{e["answer"]}</span><br><span class="sb {ce}">{se}/10</span><span class="tb">⏱️ {e.get("time_taken","N/A")}s</span> <span style="color:#8b949e;font-size:12px;">{e.get("feedback","")}</span></div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="background:#1c2333;padding:16px;border-radius:8px;color:#e6edf3;white-space:pre-wrap;margin-top:10px;">{session["report"]}</div>', unsafe_allow_html=True)

elif st.session_state.page=="dev":
    st.markdown('<div class="ch"><div><h1>🔧 Dev Dashboard</h1><span>System diagnostics</span></div></div>', unsafe_allow_html=True)
    if not st.session_state.dev_auth:
        st.markdown('<div class="ls"><p style="font-size:36px;margin:0 0 10px;">🔒</p><p style="color:#e6edf3;">Developer access only.</p></div>', unsafe_allow_html=True)
        pwd=st.text_input("Password",type="password",key="dev_pwd")
        if st.button("Unlock",use_container_width=True,type="primary"):
            if pwd==ADMIN_PASSWORD: st.session_state.dev_auth=True;st.rerun()
            else: st.error("Wrong password.")
    else:
        ss=st.session_state.sessions
        st.markdown("### ⚡ System Status")
        gs="🟢 Connected" if client else "🔴 Offline"
        c1,c2,c3,c4=st.columns(4)
        with c1: st.markdown(f'<div class="sc"><h3 style="font-size:16px;">{gs}</h3><p>Gemini</p></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="sc"><h3>{len(qbank):,}</h3><p>Questions</p></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="sc"><h3>{len(set(q["category"] for q in qbank))}</h3><p>Categories</p></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="sc"><h3>{len(ss)}</h3><p>Sessions</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        if ss:
            ai=[ e for s in ss for e in s["interactions"]];gq=sum(1 for e in ai if e["source"]=="Gemini");bq=sum(1 for e in ai if e["source"]=="Bank");dq=sum(1 for e in ai if e["source"]=="Default");tq=len(ai)
            st.markdown("### 🤖 Question Sources")
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="sc"><h3>{gq}</h3><p>Gemini ({round(gq/max(tq,1)*100,1)}%)</p></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="sc"><h3>{bq}</h3><p>Bank ({round(bq/max(tq,1)*100,1)}%)</p></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="sc"><h3>{dq}</h3><p>Default ({round(dq/max(tq,1)*100,1)}%)</p></div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("### 📊 Scores")
            scores=[e["score"] for e in ai];hi=sum(1 for s in scores if s>=7);mi=sum(1 for s in scores if 4<=s<7);lo=sum(1 for s in scores if s<4)
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="sc"><h3 style="color:#1D9E75;">{hi}</h3><p>Strong (7+)</p></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="sc"><h3 style="color:#B8860B;">{mi}</h3><p>Adequate (4 to 6)</p></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="sc"><h3 style="color:#e94560;">{lo}</h3><p>Weak (0 to 3)</p></div>', unsafe_allow_html=True)
            st.markdown("---")
            times=[e.get("time_taken",0) for e in ai if e.get("time_taken")]
            if times:
                st.markdown("### ⏱️ Response Times")
                c1,c2,c3=st.columns(3)
                with c1: st.markdown(f'<div class="sc"><h3>{round(min(times),1)}s</h3><p>Fastest</p></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="sc"><h3>{round(sum(times)/len(times),1)}s</h3><p>Average</p></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="sc"><h3>{round(max(times),1)}s</h3><p>Slowest</p></div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("### 🎯 Skills Coverage")
            skc={};
            for e in ai: sk=e.get("skill","Unknown");skc[sk]=skc.get(sk,0)+1
            for sk,cnt in sorted(skc.items(),key=lambda x:-x[1]):
                pct=round(cnt/max(tq,1)*100,1)
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0;"><span style="color:#e6edf3;width:140px;font-size:14px;">{sk}</span><div style="flex:1;height:8px;background:#2d333b;border-radius:4px;overflow:hidden;"><div style="width:{pct}%;height:100%;background:#1D9E75;border-radius:4px;"></div></div><span style="color:#8b949e;font-size:12px;width:60px;text-align:right;">{cnt}</span></div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("### 📝 Raw Data")
            st.json(ss)
        else: st.markdown('<div style="text-align:center;padding:60px;color:#8b949e;"><p style="font-size:48px;">📭</p><p>No data yet.</p></div>', unsafe_allow_html=True)
