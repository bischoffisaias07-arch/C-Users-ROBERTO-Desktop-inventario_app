from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import io
import os
from datetime import datetime, date
from typing import Optional

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Load Excel inventory files at startup
try:
    inventario_df = pd.read_excel(os.path.join(BASE_DIR, 'Inventario.xlsx'))
except Exception as e:
    print("Error loading Inventario.xlsx: {}".format(e))
    inventario_df = pd.DataFrame(columns=['Codigo', 'Descripcion'])

try:
    ean_df = pd.read_excel(os.path.join(BASE_DIR, 'Inventario_EAN.xlsx'))
except Exception as e:
    print("Error loading Inventario_EAN.xlsx: {}".format(e))
    ean_df = pd.DataFrame(columns=['Codigo', 'Descripción', 'EAN'])

# In-memory list for the current working session
lista_productos = []
_contador = 0


def _calcular_estado(fecha_venc: str) -> str:
    try:
        fv = datetime.strptime(fecha_venc, "%Y-%m-%d").date()
        hoy = date.today()
        delta = (fv - hoy).days
        if delta < 0:
            return "VENCIDO"
        elif delta <= 30:
            return "PRÓXIMO A VENCER"
        else:
            return "VIGENTE"
    except Exception:
        return "DESCONOCIDO"


def _buscar_descripcion_por_codigo(codigo: str) -> Optional[str]:
    cod_norm = str(codigo).lstrip('0')
    mask = inventario_df['Codigo'].astype(str).str.lstrip('0') == cod_norm
    rows = inventario_df[mask]
    if not rows.empty:
        return str(rows.iloc[0]['Descripcion'])
    return None


def _buscar_codigo_por_descripcion(descripcion: str) -> Optional[str]:
    mask = inventario_df['Descripcion'].str.strip().str.lower() == descripcion.strip().lower()
    rows = inventario_df[mask]
    if not rows.empty:
        return str(rows.iloc[0]['Codigo'])
    return None


# ---------- Models ----------

class ProductoEntrada(BaseModel):
    codigo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_vencimiento: str


# ---------- Routes ----------

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/articulos")
async def get_articulos():
    nombres = inventario_df['Descripcion'].dropna().astype(str).tolist()
    return nombres


@app.get("/nombres")
async def get_nombres():
    nombres = inventario_df['Descripcion'].dropna().astype(str).tolist()
    return {"nombres": nombres}


@app.get("/lista")
async def get_lista():
    return {"lista": lista_productos}


@app.post("/agregar_producto")
async def agregar_producto(producto: ProductoEntrada):
    global _contador
    codigo = (producto.codigo or "").strip()
    descripcion = (producto.descripcion or "").strip()

    if codigo and descripcion:
        raise HTTPException(status_code=400, detail="Ingresa SOLO código O nombre, no ambos")
    if not codigo and not descripcion:
        raise HTTPException(status_code=400, detail="Ingresa código o nombre")
    if not producto.fecha_vencimiento:
        raise HTTPException(status_code=400, detail="Ingresa fecha de vencimiento")

    if codigo:
        desc_encontrada = _buscar_descripcion_por_codigo(codigo)
        if desc_encontrada is None:
            raise HTTPException(status_code=404, detail="Código no encontrado en el inventario")
        descripcion = desc_encontrada
    else:
        cod_encontrado = _buscar_codigo_por_descripcion(descripcion)
        if cod_encontrado is not None:
            codigo = cod_encontrado
        else:
            _contador += 1
            codigo = "NOM{}".format(_contador)

    estado = _calcular_estado(producto.fecha_vencimiento)
    item = {
        "Codigo": codigo,
        "Descripcion": descripcion,
        "FechaVencimiento": producto.fecha_vencimiento,
        "Estado": estado,
    }
    lista_productos.append(item)
    return {"lista": lista_productos}


@app.delete("/borrar_producto/{codigo}")
async def borrar_producto(codigo: str):
    idx = next((i for i, p in enumerate(lista_productos) if str(p["Codigo"]) == str(codigo)), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    lista_productos.pop(idx)
    return {"lista": lista_productos, "mensaje": "Producto eliminado"}


@app.put("/modificar_producto/{codigo}")
async def modificar_producto(codigo: str, nueva_fecha: str):
    try:
        datetime.strptime(nueva_fecha, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")
    idx = next((i for i, p in enumerate(lista_productos) if str(p["Codigo"]) == str(codigo)), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    lista_productos[idx]["FechaVencimiento"] = nueva_fecha
    lista_productos[idx]["Estado"] = _calcular_estado(nueva_fecha)
    return {"lista": lista_productos, "mensaje": "Producto modificado"}


@app.post("/guardar_lista")
async def guardar_lista():
    if not lista_productos:
        raise HTTPException(status_code=400, detail="La lista está vacía")
    df_out = pd.DataFrame(lista_productos)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_out.to_excel(writer, index=False, sheet_name='Vencimientos')
    output.seek(0)
    headers = {
        "Content-Disposition": "attachment; filename=lista_final.xlsx"
    }
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
