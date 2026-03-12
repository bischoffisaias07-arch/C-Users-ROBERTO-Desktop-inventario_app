from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
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

# 3️⃣ Normalizar código/EAN: quita ceros al inicio.
#    Maneja int, float (ej: 7790060023684.0 → "7790060023684"), str y NaN.
def normalizar_codigo(valor):
    try:
        f = float(valor)
        if f != f:          # NaN → vacío (evita falsos positivos)
            return ''
        return str(int(f)).lstrip('0') or '0'
    except Exception:
        return str(valor).strip().lstrip('0') or '0'

def _ean_str(valor):
    """Convierte un valor EAN a string limpio para mostrar; NaN/vacío → 'N/A'."""
    try:
        f = float(valor)
        if f != f:
            return 'N/A'
        return str(int(f))
    except Exception:
        s = str(valor).strip()
        return 'N/A' if s in ('', 'nan', 'NaN', 'None') else s

# 4️⃣ Cargar Excel base - DOS ARCHIVOS
df_principal = pd.DataFrame(columns=["codigo", "descripcion", "stock"])
df_ean_raw   = pd.DataFrame(columns=["ean", "codigo", "descripcion", "stock"])

if os.path.exists("Inventario.xlsx"):
    try:
        df_principal = pd.read_excel("Inventario.xlsx")
        df_principal.columns = df_principal.columns.str.strip().str.lower()
    except Exception as e:
        print(f"Error cargando Inventario.xlsx: {e}")

if os.path.exists("Inventario_EAN.xlsx"):
    try:
        df_ean_raw = pd.read_excel("Inventario_EAN.xlsx")
        df_ean_raw.columns = df_ean_raw.columns.str.strip().str.lower()
        # Normalizar nombre de columna con tilde → sin tilde
        if 'descripción' in df_ean_raw.columns:
            df_ean_raw = df_ean_raw.rename(columns={'descripción': 'descripcion'})
    except Exception as e:
        print(f"Error cargando Inventario_EAN.xlsx: {e}")

# Construir DataFrame unificado
if not df_ean_raw.empty:
    df = pd.concat([df_principal, df_ean_raw], ignore_index=True)
    df['codigo_normalizado'] = df['codigo'].apply(normalizar_codigo)
    df = df.drop_duplicates(subset=['codigo_normalizado'], keep='first')
else:
    df = df_principal.copy()
    df['codigo_normalizado'] = df['codigo'].apply(normalizar_codigo)

# Consolidar descripción: algunos productos del EAN file pueden estar solo ahí
if 'descripción' in df.columns:
    df['descripcion'] = df['descripcion'].fillna(df['descripción'])

# ── Diccionario de lookup EAN → código_normalizado ──────────────────────────
# Se construye directamente desde el archivo EAN (ANTES del dedup) para no
# perder los EAN de productos que el principal ya tenía (y ganaron el dedup).
_ean_a_codigo: dict[str, str] = {}   # ean_normalizado → codigo_normalizado
if not df_ean_raw.empty and 'ean' in df_ean_raw.columns:
    for _, row in df_ean_raw[df_ean_raw['ean'].notna()].iterrows():
        en = normalizar_codigo(row['ean'])
        cn = normalizar_codigo(row['codigo'])
        if en and cn:
            _ean_a_codigo[en] = cn

# Mantener también ean_normalizado en df (para productos EAN-only que sí quedaron)
if 'ean' in df.columns:
    df['ean_normalizado'] = df['ean'].apply(normalizar_codigo)

# 5️⃣ Lista temporal de productos seleccionados en la sesión
lista_productos: list[dict] = []

class Producto(BaseModel):
    codigo: str | None = None
    descripcion: str | None = None
    ean: str | None = None
    fecha_vencimiento: str

def estado_vencimiento(fecha_str: str) -> str:
    hoy   = datetime.today().date()
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    dias  = (fecha - hoy).days
    if dias < 0:
        return "Vencido"
    if dias == 0:
        return "Se vence hoy"
    if dias <= 7:
        return "Crítico (<7 días)"
    return f"Correcto ({dias} días restantes)"

def _buscar_por_codigo_o_ean(valor: str):
    """Busca una fila en df por código normalizado; si no la encuentra, intenta por EAN."""
    norm = normalizar_codigo(valor)
    fila = df[df['codigo_normalizado'] == norm]
    if fila.empty and norm in _ean_a_codigo:
        fila = df[df['codigo_normalizado'] == _ean_a_codigo[norm]]
    return fila

# 6️⃣ Endpoints
@app.post("/agregar_producto")
def agregar_producto(prod: Producto):
    if prod.codigo:
        producto = _buscar_por_codigo_o_ean(prod.codigo)
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por código")
    elif prod.ean:
        producto = _buscar_por_codigo_o_ean(prod.ean)
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por EAN")
    elif prod.descripcion:
        producto = df[df["descripcion"].str.contains(
            prod.descripcion.strip(), case=False, na=False, regex=False)]
        if producto.empty:
            raise HTTPException(status_code=404, detail="Producto no encontrado por descripción")
    else:
        raise HTTPException(status_code=400, detail="Debe ingresar código, EAN o descripción")

    datos = producto.iloc[0].to_dict()

    # Evitar duplicados en la lista de trabajo
    codigo_original = str(datos.get("codigo", "")).strip()
    for p in lista_productos:
        if p["Codigo"] == codigo_original:
            raise HTTPException(status_code=400, detail="Producto ya agregado")

    lista_productos.append({
        "Codigo":           codigo_original,
        "Descripcion":      str(datos.get("descripcion", "") or "").strip(),
        "Stock":            datos.get("stock", ""),
        "EAN":              _ean_str(datos.get("ean", "")),
        "FechaVencimiento": prod.fecha_vencimiento,
        "Estado":           estado_vencimiento(prod.fecha_vencimiento),
    })
    return {"mensaje": "Producto agregado", "lista": lista_productos}

@app.post("/guardar_lista")
def guardar_lista(background_tasks: BackgroundTasks):
    if not lista_productos:
        raise HTTPException(status_code=400, detail="Lista vacía")
    df_final = pd.DataFrame(lista_productos)
    nombre_archivo = f"lista_{uuid.uuid4().hex}.xlsx"
    df_final.to_excel(nombre_archivo, index=False)
    background_tasks.add_task(os.remove, nombre_archivo)
    return FileResponse(nombre_archivo, filename="lista_final.xlsx")

@app.delete("/borrar_producto/{codigo}")
def borrar_producto(codigo: str):
    global lista_productos
    codigo_norm = str(codigo).strip().upper()
    lista_productos = [
        p for p in lista_productos
        if str(p.get("Codigo", "")).strip().upper() != codigo_norm
    ]
    return {"mensaje": "Producto eliminado", "lista": lista_productos}

@app.get("/nombres")
def obtener_nombres():
    return {"nombres": df["descripcion"].dropna().unique().tolist()}

@app.get("/api/articulos")
def get_articulos():
    try:
        return df["descripcion"].dropna().unique().tolist()
    except Exception:
        return []

@app.get("/buscar_articulos")
def buscar_articulos(q: str = ""):
    """Busca artículos por nombre parcial (≥2 chars, hasta 30 resultados)."""
    q = q.strip()
    if len(q) < 2:
        return []
    try:
        mask = df["descripcion"].str.contains(q, case=False, na=False, regex=False)
        return df[mask]["descripcion"].dropna().unique().tolist()[:30]
    except Exception:
        return []

@app.get("/buscar_codigo_ean")
def buscar_codigo_ean(q: str = ""):
    """Busca producto por código o EAN parcial/completo (≥2 chars).
    Devuelve lista de {codigo, descripcion} para autocompletado."""
    q = q.strip()
    if len(q) < 2:
        return []
    try:
        q_norm = normalizar_codigo(q)
        vistos: set[str] = set()
        resultados: list[dict] = []

        def _agregar_fila(row):
            cod  = str(row.get('codigo',     '') or '').strip()
            desc = str(row.get('descripcion','') or '').strip()
            if desc and cod not in vistos:
                vistos.add(cod)
                resultados.append({"codigo": cod, "descripcion": desc})

        # 1. Por código
        for _, row in df[df['codigo_normalizado'].str.startswith(q_norm, na=False)].head(10).iterrows():
            _agregar_fila(row)

        # 2. Por EAN (usando el dict completo del archivo EAN)
        if len(resultados) < 20:
            for ean_n, cod_n in _ean_a_codigo.items():
                if ean_n.startswith(q_norm):
                    fila = df[df['codigo_normalizado'] == cod_n]
                    if not fila.empty:
                        _agregar_fila(fila.iloc[0])
                    if len(resultados) >= 20:
                        break

        return resultados
    except Exception:
        return []

@app.get("/lista")
def get_lista():
    return {"lista": lista_productos}

@app.put("/modificar_producto/{codigo}")
def modificar_producto(codigo: str, nueva_fecha: str):
    codigo_norm = str(codigo).strip().upper()
    for p in lista_productos:
        if str(p.get("Codigo", "")).strip().upper() == codigo_norm:
            p["FechaVencimiento"] = nueva_fecha
            p["Estado"]           = estado_vencimiento(nueva_fecha)
            return {"mensaje": "Producto modificado", "lista": lista_productos}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

# 7️⃣ Arranque del servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
