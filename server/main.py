from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create a FastAPI app instance
app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI backend service!"}


@app.get("/api/greet")
def greet_user(name: str = "World"):
    """
    A simple API endpoint that takes a name and returns a greeting.
    :param name: The name to greet, passed as a query parameter (e.g., /api/greet?name=Gemini)
    """
    if not name:
        name = "World"
    return {"message": f"Hello, {name}! This is a message from FastAPI."}


if __name__ == "__main__":
    print("Starting FastAPI server, please visit http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)