"""Findora API scaffold. ALL initial product data is illustrative, not real offers."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .sample_data import PRODUCTS, OFFERS, HISTORY, SIMILAR

app = FastAPI(title="Findora API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "data_mode": "demo"}

@app.get("/products/search")
def search(q: str = ""):
    return {"items": [p for p in PRODUCTS.values() if q.lower() in (p["title"] + " " + p["brand"]).lower()]}

@app.get("/products/{product_id}")
def product(product_id: str):
    if product_id not in PRODUCTS:
        raise HTTPException(404, "Unknown product")
    return PRODUCTS[product_id]

@app.get("/products/{product_id}/offers")
def offers(product_id: str):
    product(product_id)
    return {"product_id": product_id, "offers": OFFERS.get(product_id, [])}

@app.get("/products/{product_id}/history")
def history(product_id: str):
    product(product_id)
    return {"product_id": product_id, "observations": HISTORY.get(product_id, []), "data_status": "demo"}

@app.get("/products/{product_id}/similar")
def similar(product_id: str):
    product(product_id)
    return {"product_id": product_id, "items": SIMILAR.get(product_id, [])}

@app.get("/products/{product_id}/advice")
def advice(product_id: str):
    product(product_id)
    return {"product_id": product_id, "decision": "INSUFFICIENT_DATA", "explanation": "Demo data only; no verified historical observations are connected.", "evidence": [], "data_status": "demo"}
