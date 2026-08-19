from fastapi import FastAPI, HTTPException , status ,BackgroundTasks , Depends ,Request
from database import SessionLocal, engine , BaseSearch , get_db
from graph import agent
from pydantic import BaseModel
from uuid import uuid4
import uvicorn , os
from sqlalchemy.orm import Session
from taskiq_redis import RedisStreamBroker,RedisAsyncResultBackend
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
admin_key = os.getenv("ADMIN_KEY")

def get_limit(request : Request):
    api_key = request.headers.get("X-API_KEY","")
    if api_key == admin_key :
        return "admin-unlimited"
    return get_remote_address(request)

limiter = Limiter(key_func=get_limit)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    


redis_url = os.getenv("REDIS_URL")
if not os.path.exists("/.dockerenv") and redis_url and "://redis" in redis_url:
    redis_url = redis_url.replace("://redis", "://localhost")

result_backend = RedisAsyncResultBackend(
    redis_url=redis_url,
)

broker = RedisStreamBroker(
    url=redis_url,
)

broker = broker.with_result_backend(result_backend)

@app.on_event("startup")
async def startup():
    await broker.startup()

@app.on_event("shutdown")
async def shutdown():
    await broker.shutdown()

class Input(BaseModel):
    query : str

class Output(BaseModel):
    status : str
    response : str | None = None
    user_id : str

@broker.task
async def agent_response(query_text:str,id:str):
    db = SessionLocal()
    if not query_text:
        raise ValueError("query cannot be empty")
    try :
        search = db.query(BaseSearch).filter(BaseSearch.id == id).first()
        if search : 
            search.status = "running"
            db.commit()
        config = {"configurable": {"thread_id": id}} #for the checkpointer part
        response = await agent(query_text, config=config)
        print(f"RESPONSE TYPE: {type(response)}")
        print(f"RESPONSE VALUE: {repr(response)}")
        if response :
            clean_response = response.replace("\\n", "\n")
            search.response = clean_response
            search.status = "completed"
        else :
            search.status = "failed"
        db.commit()
    except Exception as e:
        db.rollback()
        search = db.query(BaseSearch).filter(BaseSearch.id == id).first()
        if search:
            search.status = "failed"
            db.commit()
        print(f"Error executing agent response for ID {id}: {e}")
        raise e
    finally :
        db.close()
    
@app.get("/")
def read_root():
    return {"message" : "Welcome to the market research agent"}

@app.post("/research")
@limiter.limit("5/minute")
async def research(request: Request,input : Input):
    if not input.query :
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND , detail = "query cannot be empty")
    user_id = str(uuid4())
    db = SessionLocal()
    try :
        new_task = BaseSearch(id = user_id , query = input.query , response =None,status ="queued")
        db.add(new_task)
        db.commit()
        await agent_response.kiq(input.query,user_id)
        return {"message": "task is being processed","user_id": user_id}
    finally:
        db.close()
    

@app.get("/research/{id}")
@limiter.limit("30/minute")
def get_response(request: Request,id: str, db: Session = Depends(get_db)):
    new_search = db.query(BaseSearch).filter(BaseSearch.id == id).first()
    if not new_search :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task ID not found")
    if new_search.status == "completed":
        return Output(status = "task done successfuly" , response = new_search.response ,user_id = new_search.id)
    elif new_search.status == "running":
        return Output(status = "running",response =None , user_id = new_search.id)
    elif new_search.status == "queued":
        return Output(status = "queued",response =None , user_id = new_search.id)
    else :
        return Output(status = "task failed ! Try again",response =None , user_id=new_search.id)
    
    

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)    









    
    




