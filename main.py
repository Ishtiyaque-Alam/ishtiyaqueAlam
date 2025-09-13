from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.pipeline.analyzer import CodeAnalyzer
from src.qa_agent.conv_bot import ConversationalBot
from src.qa_agent.manage_chunks import TopicSwitchingRetriever
from src.qa_agent.debugger_agent import LLMClient, DebuggerAgent, Planner, DebugMain
from src.vector_db.chroma_manager import ChromaManager

app = FastAPI()

# Mount static and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Initialize components (shared for now)
llm = LLMClient()
planner = Planner(llm)
chroma_manager=ChromaManager()
topic_retriever = TopicSwitchingRetriever(chroma_manager)
analyzer = DebugMain(llm)
debugger_agent = DebuggerAgent(planner, topic_retriever, analyzer)
bot = ConversationalBot(topic_retriever, debugger_agent, llm)

# ---------------- UI Routes ----------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/github", response_class=HTMLResponse)
async def github_tab(request: Request):
    return templates.TemplateResponse("github.html", {"request": request})

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_tab(request: Request):
    return templates.TemplateResponse("analyze.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_tab(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

# ---------------- API Endpoints ----------------
@app.post("/analyze", response_class=HTMLResponse)
async def analyze_repo(repo_url: str = Form(...)):
    code_analyzer = CodeAnalyzer(output_dir="./analysis_output")
    summary = code_analyzer.analyze(repo_url)

    return f"""
    <div class="bg-white border rounded-xl shadow p-4">
      <h3 class="text-lg font-semibold mb-2">Analysis</h3>
      <p class="text-gray-800">{summary}</p>
      <div class="border-t my-3"></div>
      <h3 class="text-lg font-semibold mb-2">Fix</h3>
      <p class="text-gray-800">Fix suggestions will appear here.</p>
    </div>
    """

@app.post("/chat", response_class=HTMLResponse)
async def chat(message: str = Form(...)):
    response = bot.handle_query(message)
    return response  # HTMX script in chat.html will wrap it in a bubble

@app.post("/github", response_class=HTMLResponse)
async def analyze_github(owner: str = Form(...), repo: str = Form(...)):
    from src.github_analyser.github_analyzer import download_github_repo
    download_github_repo(owner, repo, dest_folder="./downloaded_repo")

    code_analyzer = CodeAnalyzer(output_dir="./analysis_output")
    summary = code_analyzer.analyze("./downloaded_repo")

    return f"""
    <div class="bg-white border rounded-xl shadow p-4">
      <h3 class="text-lg font-semibold mb-2">GitHub Repo Analysis</h3>
      <p class="text-gray-800">{summary}</p>
    </div>
    """

# ---------------- Run ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000, reload=True)