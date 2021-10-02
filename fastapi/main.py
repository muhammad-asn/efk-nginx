from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import uuid

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/healtcheck")
async def healtcheck():
    return {"status": "HEALTHY"}

@app.get("/article/{id}")
async def get_post_by_id(id: int):
    try :
        if id == 1:
            return HTMLResponse(content=f"<h2> This is article {id}</h2>", status_code=200)
        else:
            return HTMLResponse(content=f"<h2> This is article {uuid.uuid4()}</h2>", status_code=200)
    except Exception as e:
        return "<a style=\"color:red\" There's something wrong, please check again>"