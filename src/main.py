from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from socketio_handlers import sio_app


app = FastAPI()
app.mount("/", app=sio_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)