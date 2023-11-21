import uvicorn as uvicorn
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from web.router import ur_route

app = FastAPI(docs_url="/urent/docs")
add_pagination(app)

app.include_router(ur_route.router, prefix="/urent")

if __name__ == '__main__':
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)

