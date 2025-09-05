from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import csv

from agents.price_suggestor import PriceSuggestorAgent, ProductInput
from agents.chat_moderator import ChatModerationAgent, ModerateInput
from utils.llm import get_llm_client

app = FastAPI(title="Marketplace Agents API")

# ---- CORS Setup ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Initialize Agents ----
llm_client = get_llm_client()
price_agent = PriceSuggestorAgent(llm_client=llm_client)
moderator = ChatModerationAgent(llm_client=llm_client)


# ---- Routes ----
@app.post("/negotiate")
def negotiate(payload: ProductInput):
    """
    Suggest a fair price range for a product.
    Falls back to heuristic if no LLM is available.
    """
    try:
        return price_agent.suggest(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Negotiation failed: {str(e)}")


@app.post("/moderate")
def moderate(payload: ModerateInput):
    """
    Moderate a chat message for safety/toxicity.
    """
    try:
        result = moderator.moderate(payload.message)
        return {"moderated": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Moderation failed: {str(e)}")


@app.get("/load_sample/{row_id}")
def load_sample(row_id: int):
    """
    Load a sample product from data/products.csv and run price suggestion.
    """
    path = os.path.join("data", "products.csv")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="data/products.csv not found")

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if int(r["id"]) == row_id:
                    inp = ProductInput(
                        id=int(r["id"]),
                        title=r["title"],
                        category=r["category"],
                        brand=r.get("brand"),
                        condition=r["condition"],
                        age_months=int(r["age_months"]),
                        asking_price=float(r["asking_price"]) if r.get("asking_price") else None,
                        location=r.get("location"),
                    )
                    return price_agent.suggest(inp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sample: {str(e)}")

    raise HTTPException(status_code=404, detail="Row not found")
