from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pandas as pd
from datetime import datetime
import uuid
import os

# 1️⃣ Crear la aplicación FastAPI
app = FastAPI()

# 2️⃣ Conectar frontend
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 3️⃣ Función para normalizar código/EAN (quita ceros al inicio)
def normalizar_codigo(valor):
    try:
        return str(valor).strip().lstrip('0') or '0'
    except Exception:
        return str(valor)

# 4️⃣ Cargar Excel base - DOS ARCHIVOS
df_principal = pd.DataFrame(columns=["codigo", "descripcion", "stock"])
df_ean = pd.DataFrame(columns=["ean", "codigo", "descripcion", "stock"])

if os.path.exists("Inventario.xlsx"):
    try:
        df_principal = pd.read_excel("Inventario.xlsx")
        df_principal.columns = df_principal.columns.str.strip().str.lower()
    except Exception as e:
        print(f"Error cargando Inventario.xlsx: {e}")

if os.path.exists("Inventario_EAN.xlsx"):
    try:
        df_ean = pd.read_excel("Inventario_EAN.xlsx")
        df_ean.columns = df_ean.columns.str.strip().str.lower()
    except Exception as e:
        print(f"Error cargando Inventario_EAN.xlsx: {e}")

if not df_ean.empty:
    df = pd.concat([df_principal, df_ean], ignore_index=True)
    df['codigo_normalizado'] = df['codigo'].apply(normalizar_codigo)
    df = df.drop_duplicates(subset=['codigo_normalizado'], keep='first')
else:
    df = df_principal.copy()
    df['codigo_normalizado'] = df['codigo'].apply(normalizar_codigo)

if 'ean' in df.columns:
    df['ean_normalizado'] = df['ean'].apply(normalizar_codigo)

# 5️⃣ Lista temporal
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

# 6️⃣ Endpoints
@app.post("/agregar_producto")
def agregar_producto(prod: Producto):
    if prod.codigo:
        codigo_norm = normalizar_codigo(prod.codigo)
        producto = df[df['codigo_normalizado'] == codigo_norm]
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por código")
    elif prod.ean and 'ean_normalizado' in df.columns:
        ean_norm = normalizar_codigo(prod.ean)
        producto = df[df['ean_normalizado'] == ean_norm]
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por EAN")
    elif prod.descripcion:
        producto = df[df["descripcion"].str.contains(prod.descripcion.strip(), case=False, na=False)]
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por descripción")
    else:
        raise HTTPException(status_code=400, detail="Debe ingresar código, EAN o descripción")

    datos = producto.iloc[0].to_dict()

    # Evitar duplicados por código
    codigo_original = str(datos.get("codigo", "")).strip()
    for p in lista_productos:
        if p["Codigo"] == codigo_original:
            raise HTTPException(status_code=400, detail="Producto ya agregado")

    lista_productos.append({
        "Codigo": codigo_original,
        "Descripcion": str(datos.get("descripcion", "")),
        "Stock": datos.get("stock", ""),
        "EAN": str(datos.get("ean", "N/A")),
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

# 7️⃣ Arranque del servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
