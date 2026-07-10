from fastapi import FastAPI, HTTPException , status ,BackgroundTasks , Depends
from database import SessionLocal, engine , BaseSearch , get_db
from graph import agent
from pydantic import BaseModel
from uuid import uuid4
import uvicorn
from sqlalchemy.orm import Session

app = FastAPI()

class Input(BaseModel):
    query : str

class Output(BaseModel):
    status : str
    response : str | None = None
    user_id : str

def agent_response(query_text:str,id:str):
    db = SessionLocal()
    if not query_text:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND , detail = "query cannot be empty")
    try :
        search = db.query(BaseSearch).filter(BaseSearch.id == id).first()
        if search : 
            search.status = "running"
            db.commit()
        response = agent(query_text)
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
def research(input : Input,background_tasks: BackgroundTasks):
    if not input.query :
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND , detail = "query cannot be empty")
    user_id = str(uuid4())
    db = SessionLocal()
    try :
        new_task = BaseSearch(id = user_id , query = input.query , response =None,status ="queued")
        db.add(new_task)
        db.commit()
        background_tasks.add_task(agent_response,input.query,user_id)
        return {"message": "task is being processed","user_id": user_id}
    finally:
        db.close()
    

@app.get("/research/{id}")
def get_response(id: str, db: Session = Depends(get_db)):
    new_search = db.query(BaseSearch).filter(BaseSearch.id == id).first()
    if not new_search :
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task ID not found")
    if new_search.status == "completed":
        return Output(status = "task done successfuly" , response = new_search.response ,user_id = new_search.id)
    elif new_search.status == "running":
        return Output(status = "running",response =None , user_id = new_search.id)
    else :
        return Output(status = "task failed ! Try again",response =None , user_id=new_search.id)

    

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)    









    
    




