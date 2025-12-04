from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from Resume_parser.routes.route import router as api_router

app = FastAPI()
app.mount('/static', StaticFiles(directory='/home/lelo/projects/AI_Agent_task/Resume_parser/ui'), name='static')

@app.get('/', response_class=HTMLResponse)
async def index():
    with open('/home/lelo/projects/AI_Agent_task/Resume_parser/ui/index.html', 'r', encoding='utf-8') as f:
        return f.read()

app.include_router(api_router)