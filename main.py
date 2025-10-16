from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
allow_origins=["http://localhost:4200"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Finance Tracker API running"}


@app.get("/transactions")
def get_transactions():
    # Sample data — you can later connect to a DB
    return [
        {"id": 1, "category": "Food", "amount": 200, "type": "expense"},
        {"id": 2, "category": "Salary", "amount": 3000, "type": "income"},
    ]