from __future__ import annotations
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from pydantic import ConfigDict  # NEW
from fastapi import Response



# ---------- DB setup ----------
DATABASE_URL = "sqlite:///./worklog.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------- Models ----------
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    status = Column(String(30), default="in_progress")  # todo | in_progress | done | paused
    next_action = Column(String(500), default="")       # one-liner you’ll do next
    priority = Column(Integer, default=2)               # 1 high, 2 normal, 3 low
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_touched_at = Column(DateTime, default=datetime.utcnow, index=True)

    project = relationship("Project", back_populates="tasks")
    notes = relationship("Note", back_populates="task", cascade="all, delete-orphan")

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    kind = Column(String(30), default="note")  # note | decision | blocker | snapshot

    task = relationship("Task", back_populates="notes")

Base.metadata.create_all(bind=engine)

# ---------- FastAPI ----------
app = FastAPI(title="Work Memory Helper", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Schemas ----------
class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)

class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # NEW
    id: int
    name: str
    created_at: datetime

class TaskIn(BaseModel):
    title: str
    description: str = ""
    next_action: str = ""
    priority: int = 2
    status: str = "in_progress"
    project_name: Optional[str] = None

class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    next_action: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    project_name: Optional[str] = None

class NoteIn(BaseModel):
    task_id: int
    content: str
    kind: str = "note"

class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # NEW
    id: int
    content: str
    kind: str
    created_at: datetime

class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # NEW
    id: int
    title: str
    description: str
    status: str
    next_action: str
    priority: int
    project: Optional[ProjectOut] = None
    created_at: datetime
    updated_at: datetime
    last_touched_at: datetime

class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # NEW
    task: TaskOut
    latest_notes: List[NoteOut]

# ---------- Helpers ----------
def get_or_create_project(db: Session, name: Optional[str]) -> Optional[Project]:
    if not name:
        return None
    proj = db.query(Project).filter(Project.name == name).first()
    if proj:
        return proj
    proj = Project(name=name)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj

def touch_task(db: Session, task: Task):
    task.last_touched_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)

# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
<!doctype html>
<html lang="en" data-theme="dark">
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Work Memory Helper</title>
<style>
/* Base + Dark / Light */
:root{
  --bg: #0b0f14;
  --fg: #e6edf3;
  --muted:#9aa4af;
  --accent:#7aa2f7;
  --accent-hover:#5b8ef5;
  --card-bg: rgba(255,255,255,0.06);
  --border: rgba(255,255,255,0.12);
  --input-bg: rgba(255,255,255,0.06);
  --shadow: 0 10px 30px rgba(0,0,0,.35);
  --radius: 16px;
}
@media (prefers-color-scheme: light) {
  :root{
    --bg: #eef2f7;
    --fg: #0b1220;
    --muted:#5c6773;
    --accent:#3b82f6;
    --accent-hover:#2563eb;
    --card-bg: rgba(255,255,255,0.6);
    --border: rgba(0,0,0,0.08);
    --input-bg: rgba(255,255,255,0.9);
    --shadow: 0 10px 30px rgba(16,24,40,.15);
  }
}
html[data-theme="light"]{ /* manual override */
  --bg: #eef2f7;
  --fg: #0b1220;
  --muted:#5c6773;
  --accent:#3b82f6;
  --accent-hover:#2563eb;
  --card-bg: rgba(255,255,255,0.6);
  --border: rgba(0,0,0,0.08);
  --input-bg: rgba(255,255,255,0.9);
  --shadow: 0 10px 30px rgba(16,24,40,.15);
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh; color:var(--fg); font: 16px/1.5 system-ui, -apple-system, Segoe UI, Roboto, Inter, Arial, sans-serif;
  /* Frosted gradient background */
  background:
    radial-gradient(1200px 800px at 10% 10%, #1a2940 0%, transparent 55%),
    radial-gradient(1000px 700px at 90% 30%, #422046 0%, transparent 60%),
    radial-gradient(900px 600px at 50% 90%, #183a2e 0%, transparent 60%),
    var(--bg);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Layout */
.container{ max-width: 1000px; margin: 0 auto; padding: 40px 20px; }
.header{
  display:flex; align-items:center; justify-content:space-between; gap: 12px; margin-bottom: 24px;
  backdrop-filter: blur(14px) saturate(120%);
  background: var(--card-bg);
  border:1px solid var(--border);
  border-radius: calc(var(--radius) + 4px);
  padding: 14px 16px; box-shadow: var(--shadow);
}
.title{ display:flex; align-items:center; gap: 12px; }
.title .logo{
  width:38px; height:38px; border-radius:12px;
  background: linear-gradient(135deg, var(--accent), transparent);
  border:1px solid var(--border);
  box-shadow: inset 0 0 20px rgba(255,255,255,.12);
}
.header h1{ font-size: 18px; margin:0; letter-spacing:.2px; }

/* Cards */
.grid{
  display:grid; gap: 20px;
  grid-template-columns: 1.1fr .9fr;
}
@media (max-width: 900px){
  .grid{ grid-template-columns: 1fr; }
}
.card{
  backdrop-filter: blur(18px) saturate(140%);
  background: var(--card-bg);
  border:1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  box-shadow: var(--shadow);
}
.card h2{
  margin: 0 0 10px 0; font-size: 18px;
}
.card p.lead{ color: var(--muted); margin-top: 4px; }

/* Form */
label{ display:block; margin: 10px 0 6px; color: var(--muted); font-size: 13px; }
input, textarea, select{
  width:100%; padding:12px 14px; border-radius: 12px; border:1px solid var(--border);
  background: var(--input-bg); color: var(--fg); outline: none;
}
textarea{ resize: vertical; min-height: 180px; }
.btn-row{ display:flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }
button, .btn{
  appearance:none; border:1px solid transparent; cursor:pointer;
  background: linear-gradient(180deg, var(--accent), var(--accent-hover));
  color: white; padding: 12px 16px; border-radius: 12px; font-weight: 600;
  box-shadow: 0 6px 18px rgba(59,130,246,.28);
}
button.secondary{
  background: transparent; color: var(--fg); border-color: var(--border);
}
button:hover{ filter: brightness(.98); }

/* List */
.task{
  display:flex; flex-direction: column; gap: 6px;
  padding: 12px; border-radius: 12px; border:1px dashed var(--border);
  background: rgba(255,255,255,0.04);
}
.task + .task{ margin-top: 10px; }
.task .meta{
  display:flex; gap:8px; align-items:center; color: var(--muted); font-size: 12px;
}
.badge{
  display:inline-flex; align-items:center; gap:6px; font-size:12px; padding:4px 8px; border-radius:999px;
  background: rgba(122,162,247,.15); color: var(--accent); border:1px solid rgba(122,162,247,.25);
}
.status{ text-transform: capitalize; font-weight:600; }
.next{ color: var(--muted); font-size: 13px; }

/* Toggle */
.toggle{
  display:inline-flex; align-items:center; gap:10px;
  border:1px solid var(--border); border-radius: 999px; padding: 6px 10px;
  background: var(--card-bg);
}
.switch{
  width:42px; height:24px; border-radius: 20px; border:1px solid var(--border);
  background: var(--input-bg); position:relative;
}
.knob{
  position:absolute; top:2px; left:2px; width:20px; height:20px; border-radius:50%;
  background: var(--fg); transition: all .2s ease;
}
.switch.on .knob{ transform: translateX(18px); }

/* Footer */
.footer{ margin-top: 18px; color: var(--muted); font-size: 12px; text-align:center; }
.links{ display:flex; gap:12px; justify-content:center; margin-top:6px; }
</style>

<body>
  <div class="container">
    <div class="header">
      <div class="title">
        <div class="logo"></div>
        <div>
          <h1>Work Memory Helper</h1>
          <div style="color:var(--muted); font-size:12px;">Capture context fast. Return on Friday without friction.</div>
        </div>
      </div>
      <div class="toggle">
        <span style="font-size:12px;color:var(--muted)">Theme</span>
        <div class="switch" id="themeSwitch" role="button" aria-label="Toggle theme">
          <div class="knob"></div>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>Quick Capture</h2>
        <p class="lead">Paste context, set a sharply defined Next Action, and save.</p>
        <form method="post" action="/quick-capture">
          <label>Project (optional)</label>
          <input name="project_name" placeholder="e.g. Identity Platform"/>
          <label>Task title</label>
          <input name="title" placeholder="Short title for this work session" required/>
          <label>Paste your working context</label>
          <textarea name="description" placeholder="Paste text (design notes, problem analysis, etc.)"></textarea>
          <label>Next action (10–15 words, concrete)</label>
          <input name="next_action" placeholder="Implement delegation depth limit in /oauth/token/exchange"/>
          <div class="btn-row">
  <button type="submit">Save Task</button>
  <a class="btn" href="/resume/ui" target="_blank" rel="noopener">Open Resume</a>
  <a class="btn" href="/docs" target="_blank" rel="noopener">API Docs</a>
</div>

        </form>
      </div>

      <div class="card">
        <h2>Recent Focus</h2>
        <p class="lead">Your last touched tasks. Click to open raw JSON.</p>
        <div id="recent"></div>
      </div>
    </div>

    <div class="footer">
      Pro tip: add a quick “decision” note before stopping to float the task for /resume.
      <div class="links">
        <a href="/api/tasks">All Tasks</a>
        <a href="/api/projects">Projects</a>
      </div>
    </div>
  </div>


/* Fetch and paint recent tasks */
<script>
/* Theme toggle with localStorage */
(function(){
  const root = document.documentElement;
  const saved = localStorage.getItem("wmh-theme");
  if(saved){ root.setAttribute("data-theme", saved); }
  const sw = document.getElementById("themeSwitch");
  const apply = () => {
    if(!sw) return;
    sw.classList.toggle("on", root.getAttribute("data-theme")==="light");
  };
  apply();
  if(sw){
    sw.addEventListener("click", () => {
      const mode = root.getAttribute("data-theme")==="dark" ? "light" : "dark";
      root.setAttribute("data-theme", mode);
      localStorage.setItem("wmh-theme", mode);
      apply();
    });
  }
})();

/* Helpers */
function escapeHtml(s){
  return (s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

/* Fetch and paint recent tasks */
async function loadRecent(){
  const el = document.getElementById("recent");
  el.innerHTML = "<div class='task'>Loading…</div>";
  try{
    const res = await fetch("/api/tasks");
    const data = await res.json();
    const items = data.slice(0,5).map(t => {
      const proj = t.project ? t.project.name : "No project";
      const when = new Date(t.last_touched_at).toLocaleString();
      const next = t.next_action ? `<div class="next">Next: ${escapeHtml(t.next_action)}</div>` : "";
      return `
        <div class="task" id="task-${t.id}">
          <div class="meta">
            <span class="badge">${escapeHtml(proj)}</span>
            <span class="status">${escapeHtml(t.status)}</span>
            <span>•</span>
            <span>${when}</span>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
            <div><strong>#${t.id} — ${escapeHtml(t.title)}</strong></div>
<div style="display:flex; gap:8px;">
  <a class="btn" style="padding:6px 10px;font-size:12px" href="/tasks/${t.id}/ui">View</a>
  <a class="btn" style="padding:6px 10px;font-size:12px" href="/api/tasks/${t.id}" target="_blank" rel="noopener">JSON</a>
  <button class="secondary" style="padding:6px 10px;font-size:12px" onclick="deleteTask(${t.id})">Delete</button>
</div>

          </div>
          ${next}
          <div class="meta"><a href="/api/tasks/${t.id}/notes" target="_blank" rel="noopener">Notes</a></div>
        </div>
      `;
    }).join("") || "<div class='task'>No tasks yet. Create one on the left.</div>";
    el.innerHTML = items;
  }catch(e){
    el.innerHTML = "<div class='task'>Could not load tasks.</div>";
  }
}

async function deleteTask(id){
  if(!confirm("Delete task #" + id + " and all its notes?")) return;
  const res = await fetch("/api/tasks/" + id, { method: "DELETE" });
  if(res.ok){
    const el = document.getElementById("task-" + id);
    if(el) el.remove();
  }else{
    alert("Delete failed");
  }
}

loadRecent();
</script>


</body>
</html>
""")


@app.post("/quick-capture", response_class=HTMLResponse)
def quick_capture(
    project_name: Optional[str] = Form(None),
    title: str = Form(...),
    description: str = Form(""),
    next_action: str = Form(""),
    db: Session = Depends(get_db),
):
    proj = get_or_create_project(db, project_name)
    task = Task(title=title, description=description, next_action=next_action, project=proj)
    db.add(task); db.commit(); db.refresh(task)
    
    # first note snapshot (so you keep the raw paste separate from the task meta)
    if description.strip():
        n = Note(task_id=task.id, content=description, kind="snapshot")
        db.add(n); db.commit()
    
    touch_task(db, task)
    
    # after saving:
    return HTMLResponse(f"""
<!doctype html>
<html lang="en" data-theme="dark">
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Saved • Work Memory Helper</title>
<style>
/* paste the same CSS as in home() (or at least the core variables + body + card) */
:root{{ --bg:#0b0f14; --fg:#e6edf3; --muted:#9aa4af; --accent:#7aa2f7; --accent-hover:#5b8ef5;
--card-bg: rgba(255,255,255,0.06); --border: rgba(255,255,255,0.12); --input-bg: rgba(255,255,255,0.06);
--shadow: 0 10px 30px rgba(0,0,0,.35); --radius:16px; }}
html[data-theme="light"]{{ --bg:#eef2f7; --fg:#0b1220; --muted:#5c6773; --accent:#3b82f6; --accent-hover:#2563eb;
--card-bg: rgba(255,255,255,0.6); --border: rgba(0,0,0,0.08); --input-bg: rgba(255,255,255,0.9); --shadow: 0 10px 30px rgba(16,24,40,.15); }}
*{{box-sizing:border-box}}
body{{ margin:0; min-height:100vh; color:var(--fg); font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;
  background:
    radial-gradient(1200px 800px at 10% 10%, #1a2940 0%, transparent 55%),
    radial-gradient(1000px 700px at 90% 30%, #422046 0%, transparent 60%),
    radial-gradient(900px 600px at 50% 90%, #183a2e 0%, transparent 60%),
    var(--bg); }}
.container{{ max-width:720px; margin:0 auto; padding:32px 16px; }}
.card{{ backdrop-filter: blur(18px) saturate(140%); background: var(--card-bg); border:1px solid var(--border);
  border-radius: var(--radius); padding:18px; box-shadow: var(--shadow); }}
.btn{{ display:inline-block; margin-right:8px; background: linear-gradient(180deg, var(--accent), var(--accent-hover)); color:white;
  padding:10px 14px; border-radius:12px; text-decoration:none; }}
.switch{{ width:42px; height:24px; border-radius:20px; border:1px solid var(--border); background: var(--input-bg); position:relative; cursor:pointer }}
.knob{{ position:absolute; top:2px; left:2px; width:20px; height:20px; border-radius:50%; background: var(--fg); transition: all .2s; }}
.switch.on .knob{{ transform: translateX(18px); }}
</style>
<body>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
    <div style="font-weight:700">Saved</div>
    <div class="switch" id="themeSwitch"><div class="knob"></div></div>
  </div>
  <div class="card">
    <p>✅ Task <strong>#{task.id} — {task.title}</strong> saved.</p>
    <div style="margin-top:12px;">
      <a class="btn" href="/resume/ui">Open Resume</a>
      <a class="btn" href="/">Back</a>
      <a class="btn" href="/api/tasks/{task.id}" target="_blank" rel="noopener">Raw JSON</a>
    </div>
  </div>
</div>
<script>
(function(){{const root=document.documentElement;const saved=localStorage.getItem("wmh-theme");if(saved)root.setAttribute("data-theme",saved);
const sw=document.getElementById("themeSwitch");const apply=()=>sw.classList.toggle("on",root.getAttribute("data-theme")==="light");
apply(); sw.addEventListener("click",()=>{{const m=root.getAttribute("data-theme")==="dark"?"light":"dark";root.setAttribute("data-theme",m);
localStorage.setItem("wmh-theme",m);apply();}});
}})();
</script>
</body>
</html>
""")

# ---- Projects ----
@app.post("/api/projects", response_model=ProjectOut)
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    proj = get_or_create_project(db, body.name)
    return proj

@app.get("/api/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()

# ---- Tasks ----
@app.post("/api/tasks", response_model=TaskOut)
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    proj = get_or_create_project(db, body.project_name)
    task = Task(
        title=body.title,
        description=body.description or "",
        next_action=body.next_action or "",
        status=body.status or "in_progress",
        priority=body.priority or 2,
        project=proj
    )
    db.add(task); db.commit(); db.refresh(task)
    touch_task(db, task)
    return task

@app.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).get(task_id)
    if not task: raise HTTPException(404, "Task not found")
    return task

@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks(status: Optional[str] = None, project: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Task)
    if status: q = q.filter(Task.status == status)
    if project: q = q.join(Project, isouter=True).filter(Project.name == project)
    return q.order_by(Task.last_touched_at.desc()).all()

@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskPatch, db: Session = Depends(get_db)):
    task = db.query(Task).get(task_id)
    if not task: raise HTTPException(404, "Task not found")
    if body.title is not None: task.title = body.title
    if body.description is not None: task.description = body.description
    if body.next_action is not None: task.next_action = body.next_action
    if body.priority is not None: task.priority = body.priority
    if body.status is not None: task.status = body.status
    if body.project_name is not None:
        task.project = get_or_create_project(db, body.project_name)
    touch_task(db, task)
    return task

# ---- Notes ----
@app.post("/api/notes", response_model=NoteOut)
def create_note(body: NoteIn, db: Session = Depends(get_db)):
    task = db.query(Task).get(body.task_id)
    if not task: raise HTTPException(404, "Task not found")
    note = Note(task_id=task.id, content=body.content, kind=body.kind or "note")
    db.add(note); db.commit(); db.refresh(note)
    touch_task(db, task)
    return note

@app.get("/api/tasks/{task_id}/notes", response_model=List[NoteOut])
def list_notes(task_id: int, limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(Note).filter(Note.task_id == task_id)
        .order_by(Note.created_at.desc()).limit(limit).all()
    )

# ---- Resume ----
@app.get("/resume", response_model=ResumeOut)
def resume(db: Session = Depends(get_db)):
    task = (
        db.query(Task)
        .filter(Task.status.in_(["in_progress", "todo", "paused"]))
        .order_by(Task.last_touched_at.desc())
        .first()
    )
    if not task:
        raise HTTPException(404, "No active tasks yet. Create one at / or POST /api/tasks.")
    notes = (
        db.query(Note).filter(Note.task_id == task.id)
        .order_by(Note.created_at.desc()).limit(5).all()
    )
    return ResumeOut(task=task, latest_notes=notes)

@app.get("/resume.json", response_model=ResumeOut)
def resume_json(db: Session = Depends(get_db)):
    task = (
        db.query(Task)
        .filter(Task.status.in_(["in_progress", "todo", "paused"]))
        .order_by(Task.last_touched_at.desc())
        .first()
    )
    if not task:
        raise HTTPException(404, "No active tasks yet. Create one at / or POST /api/tasks.")
    notes = (
        db.query(Note).filter(Note.task_id == task.id)
        .order_by(Note.created_at.desc()).limit(5).all()
    )
    # Either return directly (with model_config fix)…
    return ResumeOut(task=task, latest_notes=notes)
    # …or: return ResumeOut.model_validate({"task": task, "latest_notes": notes})

@app.get("/resume/ui", response_class=HTMLResponse)
def resume_ui():
    return HTMLResponse("""
<!doctype html>
<html lang="en" data-theme="dark">
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Resume • Work Memory Helper</title>
<style>
/* reuse the same CSS from your home() page */
/* You can literally paste the exact <style> block from home() here */
:root{
  --bg: #0b0f14; --fg:#e6edf3; --muted:#9aa4af; --accent:#7aa2f7; --accent-hover:#5b8ef5;
  --card-bg: rgba(255,255,255,0.06); --border: rgba(255,255,255,0.12);
  --input-bg: rgba(255,255,255,0.06); --shadow: 0 10px 30px rgba(0,0,0,.35); --radius:16px;
}
html[data-theme="light"]{ --bg:#eef2f7; --fg:#0b1220; --muted:#5c6773; --accent:#3b82f6; --accent-hover:#2563eb;
  --card-bg: rgba(255,255,255,0.6); --border: rgba(0,0,0,0.08); --input-bg: rgba(255,255,255,0.9); --shadow: 0 10px 30px rgba(16,24,40,.15);
}
*{box-sizing:border-box}
body{
  margin:0; min-height:100vh; color:var(--fg);
  font: 16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;
  background:
    radial-gradient(1200px 800px at 10% 10%, #1a2940 0%, transparent 55%),
    radial-gradient(1000px 700px at 90% 30%, #422046 0%, transparent 60%),
    radial-gradient(900px 600px at 50% 90%, #183a2e 0%, transparent 60%),
    var(--bg);
}
.container{ max-width: 900px; margin: 0 auto; padding: 32px 16px; }
.header{
  display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px;
  backdrop-filter: blur(14px) saturate(120%); background: var(--card-bg); border:1px solid var(--border);
  border-radius: calc(var(--radius) + 4px); padding: 12px 14px; box-shadow: var(--shadow);
}
h1{ font-size:18px; margin:0; }
.card{
  backdrop-filter: blur(18px) saturate(140%); background: var(--card-bg); border:1px solid var(--border);
  border-radius: var(--radius); padding:18px; box-shadow: var(--shadow);
}
.badge{ display:inline-flex; gap:6px; align-items:center; font-size:12px; padding:4px 8px; border-radius:999px;
  background: rgba(122,162,247,.15); color: var(--accent); border:1px solid rgba(122,162,247,.25);
}
.meta{ color: var(--muted); font-size:12px; }
.note{ border:1px dashed var(--border); border-radius:12px; padding:10px; background: rgba(255,255,255,0.04); }
.note + .note{ margin-top:10px; }
.toggle{
  display:inline-flex; align-items:center; gap:10px; border:1px solid var(--border);
  border-radius:999px; padding:6px 10px; background: var(--card-bg);
}
.switch{ width:42px; height:24px; border-radius:20px; border:1px solid var(--border); background: var(--input-bg); position:relative; }
.knob{ position:absolute; top:2px; left:2px; width:20px; height:20px; border-radius:50%; background: var(--fg); transition: all .2s; }
.switch.on .knob{ transform: translateX(18px); }
a{ color:var(--accent); text-decoration:none } a:hover{text-decoration:underline}
</style>
<body>
<div class="container">
  <div class="header">
    <h1>Resume</h1>
    <div class="toggle">
      <span style="font-size:12px;color:var(--muted)">Theme</span>
      <div class="switch" id="themeSwitch"><div class="knob"></div></div>
    </div>
  </div>

  <div class="card" id="content">Loading…</div>
  <div style="margin-top:12px;"><a href="/">← Back</a></div>
</div>

<script>
function esc(s){return (s??"").replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));}

async function loadResume(){
  const el = document.getElementById("content");
  try{
    const res = await fetch("/resume.json");
    if(!res.ok){ el.innerHTML = "No active tasks yet. Create one on the home page."; return; }
    const { task, latest_notes } = await res.json();
    const proj = task.project ? task.project.name : "No project";
    const when = new Date(task.last_touched_at).toLocaleString();
    const notes = latest_notes.map(n => `
      <div class="note" id="note-${n.id}">
        <div class="meta">${new Date(n.created_at).toLocaleString()} • ${esc(n.kind)}</div>
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div>${esc(n.content)}</div>
          <button class="secondary" style="padding:6px 10px;font-size:12px" onclick="deleteNote(${n.id})">Delete</button>
        </div>
      </div>
    `).join("") || "<div class='note'>No recent notes.</div>";
    el.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
        <span class="badge">${esc(proj)}</span>
        <span class="meta">${when}</span>
      </div>
      <div style="font-weight:700; font-size:18px; margin-bottom:6px;">#${task.id} — ${esc(task.title)}</div>
      <div class="meta" style="margin-bottom:10px;">Status: ${esc(task.status)} · Priority: ${task.priority}</div>
      ${task.next_action ? `<div style="margin:10px 0;"><strong>Next action:</strong> ${esc(task.next_action)}</div>` : ""}
      <div style="display:flex; gap:8px; margin: 8px 0 16px;">
        <a class="btn" href="/api/tasks/${task.id}" target="_blank" rel="noopener" style="padding:8px 12px; font-size:12px">Raw JSON</a>
        <button class="secondary" style="padding:8px 12px; font-size:12px" onclick="deleteCurrentTask(${task.id})">Delete Task</button>
      </div>
      <div style="margin-top:12px;"><strong>Latest notes</strong></div>
      <div style="margin-top:8px;">${notes}</div>
    `;
  }catch(err){
    el.innerHTML = "Could not load resume.";
  }
}

async function deleteCurrentTask(id){
  if(!confirm("Delete task #" + id + " and all its notes?")) return;
  const res = await fetch("/api/tasks/" + id, { method: "DELETE" });
  if(res.ok){
    // After deletion, reload to show next most recent task (if any)
    loadResume();
  }else{
    alert("Delete failed");
  }
}

async function deleteNote(id){
  if(!confirm("Delete note #" + id + "?")) return;
  const res = await fetch("/api/notes/" + id, { method: "DELETE" });
  if(res.ok){
    const el = document.getElementById("note-" + id);
    if(el) el.remove();
  }else{
    alert("Delete failed");
  }
}
loadResume();
</script>

</body>
</html>
""")
@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task)  # cascades delete notes
    db.commit()
    return Response(status_code=204)

@app.delete("/api/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()
    return Response(status_code=204)

from fastapi import Path
from fastapi.responses import HTMLResponse

@app.get("/tasks/{task_id}/ui", response_class=HTMLResponse)
def task_ui(task_id: int = Path(...)):
    return HTMLResponse(f"""
<!doctype html>
<html lang="en" data-theme="dark">
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Task {task_id} • Work Memory Helper</title>
<style>
:root{{
  --bg:#0b0f14; --fg:#e6edf3; --muted:#9aa4af; --accent:#7aa2f7; --accent-hover:#5b8ef5;
  --card-bg:rgba(255,255,255,0.06); --border:rgba(255,255,255,0.12); --input-bg:rgba(255,255,255,0.06);
  --shadow:0 10px 30px rgba(0,0,0,.35); --radius:16px;
}}
html[data-theme="light"]{{ --bg:#eef2f7; --fg:#0b1220; --muted:#5c6773; --accent:#3b82f6; --accent-hover:#2563eb;
  --card-bg:rgba(255,255,255,0.6); --border:rgba(0,0,0,0.08); --input-bg:rgba(255,255,255,0.9); --shadow:0 10px 30px rgba(16,24,40,.15); }}
*{{box-sizing:border-box}}
body{{ margin:0; min-height:100vh; color:var(--fg); font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;
  background:
    radial-gradient(1200px 800px at 10% 10%, #1a2940 0%, transparent 55%),
    radial-gradient(1000px 700px at 90% 30%, #422046 0%, transparent 60%),
    radial-gradient(900px 600px at 50% 90%, #183a2e 0%, transparent 60%),
    var(--bg);
}}
.container{{ max-width:900px; margin:0 auto; padding:32px 16px; }}
.header{{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px;
  backdrop-filter: blur(14px) saturate(120%); background: var(--card-bg); border:1px solid var(--border);
  border-radius: calc(var(--radius) + 4px); padding:12px 14px; box-shadow: var(--shadow); }}
h1{{ font-size:18px; margin:0; }}
.card{{ backdrop-filter: blur(18px) saturate(140%); background: var(--card-bg); border:1px solid var(--border);
  border-radius: var(--radius); padding:18px; box-shadow: var(--shadow); }}
.meta{{ color:var(--muted); font-size:12px; }}
.badge{{ display:inline-flex; gap:6px; align-items:center; font-size:12px; padding:4px 8px; border-radius:999px;
  background: rgba(122,162,247,.15); color: var(--accent); border:1px solid rgba(122,162,247,.25); }}
.toolbar{{ display:flex; gap:8px; flex-wrap:wrap; }}
button,.btn{{ appearance:none; border:1px solid transparent; cursor:pointer;
  background:linear-gradient(180deg, var(--accent), var(--accent-hover)); color:white; padding:8px 12px; border-radius:12px; font-weight:600; }}
button.secondary{{ background:transparent; color:var(--fg); border-color:var(--border); }}
.note{{ border:1px dashed var(--border); border-radius:12px; padding:10px; background: rgba(255,255,255,0.04); }}
.note + .note{{ margin-top:10px; }}
.markdown p{{ margin: .6em 0; }}
.markdown pre{{ overflow:auto; padding:12px; border:1px solid var(--border); border-radius:12px; background:rgba(0,0,0,.35); }}
.markdown code{{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
.switch{{ width:42px; height:24px; border-radius:20px; border:1px solid var(--border); background: var(--input-bg); position:relative; cursor:pointer }}
.knob{{ position:absolute; top:2px; left:2px; width:20px; height:20px; border-radius:50%; background: var(--fg); transition: all .2s; }}
.switch.on .knob{{ transform: translateX(18px); }}
a{{ color:var(--accent); text-decoration:none; }} a:hover{{ text-decoration:underline; }}
label{{ display:block; margin: 10px 0 6px; color: var(--muted); font-size: 13px; }}
textarea{{ width:100%; padding:12px 14px; border-radius: 12px; border:1px solid var(--border); background: var(--input-bg); color: var(--fg); resize: vertical; min-height: 120px; }}
select{{ width:100%; padding:12px 14px; border-radius: 12px; border:1px solid var(--border); background: var(--input-bg); color: var(--fg); }}
</style>

<body>
<div class="container">
  <div class="header">
    <h1>Task {task_id}</h1>
    <div class="switch" id="themeSwitch"><div class="knob"></div></div>
  </div>

  <div class="card" id="task">Loading…</div>

  <div style="height:12px"></div>

  <div class="card">
    <div style="font-weight:700;margin-bottom:8px;">Add Note</div>
    <form id="noteForm" onsubmit="return addNote(event)">
      <label>Kind</label>
      <select id="noteKind">
        <option value="note">note</option>
        <option value="decision">decision</option>
        <option value="blocker">blocker</option>
        <option value="snapshot">snapshot</option>
      </select>
      <label>Content (Markdown supported)</label>
      <textarea id="noteContent" placeholder="Write a quick note…"></textarea>
      <div class="toolbar" style="margin-top:8px;">
        <button type="submit">Save Note</button>
      </div>
    </form>
  </div>

  <div style="margin-top:12px;"><a href="/">← Back</a></div>
</div>

<script>
// Debug: Log the task ID
console.log("Task ID:", {task_id});

function esc(s){{
  return (s ?? "").replace(/[&<>"']/g, function(c) {{
    switch(c) {{
      case '&': return '&amp;';
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '"': return '&quot;';
      case "'": return '&#039;';
      default: return c;
    }}
  }});
}}

// simple markdown-ish renderer
function md(src){{
  src = src.replace(/```([\\s\\S]*?)```/g, function(_, code) {{
    return "<pre><code>" + esc(code) + "</code></pre>";
  }});
  src = src.replace(/`([^`]+)`/g, function(_, code) {{
    return "<code>" + esc(code) + "</code>";
  }});
  src = src.replace(/^######\\s?(.*)$/gm,'<h6>$1</h6>')
           .replace(/^#####\\s?(.*)$/gm,'<h5>$1</h5>')
           .replace(/^####\\s?(.*)$/gm,'<h4>$1</h4>')
           .replace(/^###\\s?(.*)$/gm,'<h3>$1</h3>')
           .replace(/^##\\s?(.*)$/gm,'<h2>$1</h2>')
           .replace(/^#\\s?(.*)$/gm,'<h1>$1</h1>');
  src = src.replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>');
  src = src.replace(/\\*([^*]+)\\*/g,'<em>$1</em>');
  src = src.replace(/\\[([^\\]]+)\\]\\((https?:[^)]+)\\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  src = src.replace(/^(?:- |\\* )(.*)$/gm,'<li>$1</li>');
  src = src.replace(/(<li>[^<]+<\\/li>\\n?)+/g, function(m) {{ return '<ul>' + m + '</ul>'; }});
  src = src.split(/\\n\\n+/).map(function(p) {{
    return /<(h\\d|ul|pre)/.test(p) ? p : '<p>' + p.replace(/\\n/g,'<br/>') + '</p>';
  }}).join('');
  return '<div class="markdown">' + src + '</div>';
}}

const TASK_ID = {task_id};

async function fetchTask(){{
  console.log("Fetching task:", TASK_ID);
  const url = "/api/tasks/" + TASK_ID;
  console.log("Fetch URL:", url);
  
  try {{
    const res = await fetch(url);
    console.log("Response status:", res.status);
    
    if(!res.ok) {{
      const errorText = await res.text();
      console.error("Error response:", errorText);
      throw new Error("Task not found: " + res.status);
    }}
    
    const data = await res.json();
    console.log("Task data:", data);
    return data;
  }} catch(err) {{
    console.error("Fetch error:", err);
    throw err;
  }}
}}

async function fetchNotes(){{
  console.log("Fetching notes for task:", TASK_ID);
  const url = "/api/tasks/" + TASK_ID + "/notes?limit=50";
  console.log("Notes URL:", url);
  
  try {{
    const res = await fetch(url);
    console.log("Notes response status:", res.status);
    
    if(!res.ok) {{
      console.warn("Notes fetch failed:", res.status);
      return [];
    }}
    
    const data = await res.json();
    console.log("Notes data:", data);
    return data;
  }} catch(err) {{
    console.error("Notes fetch error:", err);
    return [];
  }}
}}

function render(task, notes){{
  console.log("Rendering task:", task);
  const el = document.getElementById("task");
  const proj = task.project ? task.project.name : "No project";
  const when = new Date(task.last_touched_at).toLocaleString();
  const na = task.next_action ? ('<div style="margin:10px 0;"><strong>Next:</strong> ' + esc(task.next_action) + '</div>') : "";
  
  const notesHtml = notes.length ? notes.map(function(n) {{
    return '<div class="note" id="note-' + n.id + '">' +
      '<div class="meta">' + new Date(n.created_at).toLocaleString() + ' • ' + esc(n.kind) + '</div>' +
      '<div>' + md(esc(n.content)) + '</div>' +
      '<div style="display:flex;gap:8px;margin-top:8px;">' +
        '<button class="secondary" style="padding:6px 10px;font-size:12px" onclick="deleteNote(' + n.id + ')">Delete</button>' +
      '</div>' +
    '</div>';
  }}).join("") : "<div class='note'>No notes yet.</div>";

  el.innerHTML = 
    '<div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:8px;">' +
      '<div style="display:flex; align-items:center; gap:8px;">' +
        '<span class="badge">' + esc(proj) + '</span>' +
        '<span class="meta">' + when + '</span>' +
      '</div>' +
      '<div class="toolbar">' +
        '<a class="btn" href="/api/tasks/' + task.id + '" target="_blank" rel="noopener" title="View raw JSON">JSON</a>' +
        '<button class="secondary" onclick="toggleStatus()">Toggle Done</button>' +
        '<button class="secondary" onclick="deleteTask()">Delete</button>' +
      '</div>' +
    '</div>' +
    '<div style="font-weight:700; font-size:20px; margin-bottom:6px;">#' + task.id + ' — ' + esc(task.title) + '</div>' +
    '<div class="meta" style="margin-bottom:10px;">Status: ' + esc(task.status) + ' · Priority: ' + task.priority + '</div>' +
    na +
    '<div style="margin:14px 0 6px;"><strong>Description</strong></div>' +
    (task.description ? md(esc(task.description)) : '<div class="meta">No description.</div>') +
    '<div style="margin:14px 0 6px;"><strong>Notes</strong></div>' +
    '<div>' + notesHtml + '</div>';
}}

async function hydrate(){{
  console.log("Starting hydrate...");
  try {{
    const taskPromise = fetchTask();
    const notesPromise = fetchNotes();
    const task = await taskPromise;
    const notes = await notesPromise;
    
    window.__task = task;
    render(task, notes);
    console.log("Hydrate completed successfully");
  }} catch(err) {{
    console.error("Error in hydrate:", err);
    document.getElementById("task").innerHTML = "Could not load task: " + err.message + " (Check console for details)";
  }}
}}

async function toggleStatus(){{
  const t = window.__task;
  const next = t.status === "done" ? "in_progress" : "done";
  const res = await fetch("/api/tasks/" + t.id, {{
    method: "PATCH",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{ status: next }})
  }});
  if(res.ok) hydrate(); else alert("Update failed");
}}

async function deleteTask(){{
  const t = window.__task;
  if(!confirm("Delete task #" + t.id + " and all its notes?")) return;
  const res = await fetch("/api/tasks/" + t.id, {{ method: "DELETE" }});
  if(res.ok) location.href = "/"; else alert("Delete failed");
}}

async function deleteNote(id){{
  if(!confirm("Delete note #" + id + "?")) return;
  const res = await fetch("/api/notes/" + id, {{ method: "DELETE" }});
  if(res.ok) {{
    const el = document.getElementById("note-" + id);
    if(el) el.remove();
  }} else {{
    alert("Delete failed");
  }}
}}

async function addNote(e){{
  e.preventDefault();
  const content = document.getElementById("noteContent").value.trim();
  const kind = document.getElementById("noteKind").value;
  if(!content) return false;
  const res = await fetch("/api/notes", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{ task_id: TASK_ID, content: content, kind: kind }})
  }});
  if(res.ok){{
    document.getElementById("noteContent").value = "";
    hydrate();
  }} else {{
    alert("Save failed");
  }}
  return false;
}}

// Theme toggle
(function(){{
  const root = document.documentElement;
  const saved = localStorage.getItem("wmh-theme");
  if(saved) root.setAttribute("data-theme", saved);
  const sw = document.getElementById("themeSwitch");
  const apply = function() {{
    sw.classList.toggle("on", root.getAttribute("data-theme") === "light");
  }};
  apply();
  sw.addEventListener("click", function() {{
    const m = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", m); 
    localStorage.setItem("wmh-theme", m); 
    apply();
  }});
}})();

console.log("About to call hydrate...");
hydrate();
</script>

</body>
</html>
""")
