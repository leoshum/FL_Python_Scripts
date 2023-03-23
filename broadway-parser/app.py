from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from broadway_parser import parse_event_seats


app = FastAPI()
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
@app.get("/seats")
def root(pid, pyr, pmo, pda):
    return parse_event_seats(pid, pyr, pmo, pda)