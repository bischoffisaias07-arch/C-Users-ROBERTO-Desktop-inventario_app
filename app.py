from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pandas as pd
from datetime import datetime
import uuid

# 1️⃣ Crear la aplicación FastAPI
app = FastAPI()

# 2️⃣ Conectar frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 3️⃣ Cargar Excels base - DOS ARCHIVOS
try:
    df_principal = pd.read_excel("Inventario.xlsx")
    df_principal.columns = df_principal.columns.str.strip().str.lower()
except FileNotFoundError:
    df_principal = pd.DataFrame(columns=["codigo", "descripcion", "stock"])

try:
    df_ean = pd.read_excel("Inventario_EAN.xlsx")
    df_ean.columns = df_ean.columns.str.strip().str.lower()
except FileNotFoundError:
    df_ean = pd.DataFrame(columns=["ean", "codigo", "descripcion", "stock"])

# Combinar ambos DataFrames (el principal tiene prioridad en duplicados por código)
df = pd.concat([df_principal, df_ean], ignore_index=True)
# Remove duplicate codes, but keep rows that have no código (EAN-only rows)
_has_code = df["codigo"].notna()
df = pd.concat([
    df[_has_code].drop_duplicates(subset=["codigo"], keep="first"),
    df[~_has_code]
], ignore_index=True)


def normalize_code(code) -> str:
    """Strips leading zeros from a code string for loose comparison (e.g. '0001' == '1').
    Returns empty string for NaN/None so they never match a real code."""
    if pd.isna(code):
        return ""
    stripped = str(code).strip().lstrip("0")
    return stripped if stripped else "0"

# 4️⃣ Lista temporal
lista_productos = []

class Producto(BaseModel):
    codigo: str | None = None
    descripcion: str | None = None
    ean: str | None = None
    fecha_vencimiento: str

def estado_vencimiento(fecha_vencimiento: str) -> str:
    hoy = datetime.today().date()
    fecha = datetime.strptime(fecha_vencimiento, "%Y-%m-%d").date()
    dias = (fecha - hoy).days
    if dias < 0:
        return "Vencido"
    elif dias == 0:
        return "Se vence hoy"
    elif dias <= 7:
        return f"Crítico (<7 días)"
    return f"Correcto ({dias} días restantes)"

# 5️⃣ Endpoints
@app.post("/agregar_producto")
def agregar_producto(prod: Producto):
    if prod.codigo:
        norm_input = normalize_code(prod.codigo)
        # Search by código (ignoring leading zeros)
        producto = df[df["codigo"].astype(str).apply(normalize_code) == norm_input]
        # If not found by código, try matching against EAN column
        if producto.empty and "ean" in df.columns:
            producto = df[df["ean"].astype(str).apply(normalize_code) == norm_input]
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por código")
    elif prod.ean:
        if "ean" in df.columns:
            norm_ean = normalize_code(prod.ean)
            producto = df[df["ean"].astype(str).apply(normalize_code) == norm_ean]
            if producto.empty:
                raise HTTPException(status_code=404, detail="Producto no encontrado por EAN")
        else:
            raise HTTPException(status_code=400, detail="EAN no disponible en la base de datos")
    elif prod.descripcion:
        producto = df[df["descripcion"].str.contains(prod.descripcion.strip(), case=False)]
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por descripción")
    else:
        raise HTTPException(status_code=400, detail="Debe ingresar código, EAN o descripción")

    datos = producto.to_dict(orient="records")[0]

    # Evitar duplicados por código
    for p in lista_productos:
        if p["Codigo"] == datos.get("codigo", ""):
            raise HTTPException(status_code=400, detail="Producto ya agregado")

    lista_productos.append({
        "Codigo": datos.get("codigo", ""),
        "Descripcion": datos.get("descripcion", ""),
        "Stock": datos.get("stock", ""),
        "EAN": datos.get("ean", "N/A"),
        "FechaVencimiento": prod.fecha_vencimiento,
        "Estado": estado_vencimiento(prod.fecha_vencimiento)
    })

    return {"mensaje": "Producto agregado", "lista": lista_productos}

@app.post("/guardar_lista")
def guardar_lista():
    if not lista_productos:
        raise HTTPException(status_code=400, detail="Lista vacía")

    df_final = pd.DataFrame(lista_productos)
    nombre_archivo = f"lista_{uuid.uuid4().hex}.xlsx"
    df_final.to_excel(nombre_archivo, index=False)

    return FileResponse(nombre_archivo, filename="lista_final.xlsx")

@app.delete("/borrar_producto/{codigo}")
def borrar_producto(codigo: str):
    global lista_productos
    # Normalizar comparación para evitar problemas por mayúsculas/espacios/tipos
    def codigo_ok(p):
        try:
            return str(p.get("Codigo", "")).strip().upper()
        except Exception:
            return ""

    codigo_norm = str(codigo).strip().upper()
    lista_productos = [p for p in lista_productos if codigo_ok(p) != codigo_norm]
    return {"mensaje": "Producto eliminado", "lista": lista_productos}

@app.get("/nombres")
def obtener_nombres():
    return {"nombres": df["descripcion"].dropna().unique().tolist()}


@app.get("/api/articulos")
def get_articulos():
    try:
        # Devolver los nombres desde el DataFrame si está disponible
        return df["descripcion"].dropna().unique().tolist()
    except Exception:
        # Fallback de ejemplo
        return ["Producto A", "Producto B", "Producto C"]

@app.get("/lista")
def get_lista():
    return {"lista": lista_productos}


@app.put("/modificar_producto/{codigo}")
def modificar_producto(codigo: str, nueva_fecha: str):
    # Normalizar comparación (ignorar mayúsculas/espacios)
    codigo_norm = str(codigo).strip().upper()
    for p in lista_productos:
        try:
            p_codigo = str(p.get("Codigo", "")).strip().upper()
        except Exception:
            p_codigo = ""
        if p_codigo == codigo_norm:
            p["FechaVencimiento"] = nueva_fecha
            p["Estado"] = estado_vencimiento(nueva_fecha)
            return {"mensaje": "Producto modificado", "lista": lista_productos}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

# 6️⃣ Arranque del servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
