from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

app = FastAPI()

# Load the Excel files
try:
    inventario_df = pd.read_excel('Inventario.xlsx')
    ean_df = pd.read_excel('Inventario_EAN.xlsx')
except Exception as e:
    raise HTTPException(status_code=500, detail="Error loading Excel files: {}".format(e))

# Normalize EAN codes by stripping leading zeros

# Assuming the code column in the dataframes are named 'code' and 'ean_code'
inventario_df['normalized_code'] = inventario_df['code'].astype(str).str.lstrip('0')
ean_df['normalized_ean'] = ean_df['ean_code'].astype(str).str.lstrip('0')

class Item(BaseModel):
    code: str

@app.get("/items/{item_code}")
async def get_item(item_code: str):
    normalized_code = item_code.lstrip('0')
    item = inventario_df[inventario_df['normalized_code'] == normalized_code]
    if item.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.to_dict(orient='records')

@app.get("/ean/{ean_code}")
async def get_ean(ean_code: str):
    normalized_ean = ean_code.lstrip('0')
    ean_item = ean_df[ean_df['normalized_ean'] == normalized_ean]
    if ean_item.empty:
        raise HTTPException(status_code=404, detail="EAN not found")
    return ean_item.to_dict(orient='records')

@app.get("/items/")
async def list_items():
    return inventario_df.to_dict(orient='records')

@app.get("/ean/")
async def list_eans():
    return ean_df.to_dict(orient='records')
