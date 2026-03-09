# C-Users-ROBERTO-Desktop-inventario_app
# 📦 Inventario de Vencimientos

App web para gestionar y controlar las fechas de vencimiento de productos.

## 🚀 Características

- ✅ Agregar productos con fecha de vencimiento
- 📊 Gestión visual con tarjetas de estado
- 🎯 Filtros: todos, vencidos, próximos a vencer, vigentes
- 📈 Estadísticas en tiempo real
- 🎨 Diseño responsive y moderno
- 💾 Almacenamiento en base de datos

## 🌐 Ver la app en línea (Render – gratis)

1. Crea una cuenta en [render.com](https://render.com) (gratis).
2. Clic en **New → Web Service** y conecta este repositorio de GitHub.
3. Render detecta automáticamente el archivo `render.yaml` y configura todo.
4. Hacé clic en **Deploy** y en unos minutos recibirás una URL pública como:
   ```
   https://inventario-app.onrender.com
   ```

## 📋 Requisitos (local)

- Python 3.9+
- pip

## ⚙️ Instalación local

1. **Clona o descarga el repositorio**

2. **Instala las dependencias:**
```bash
pip install -r requirements.txt
```

3. **Ejecuta la aplicación:**
```bash
uvicorn app:app --reload
```

4. **Abre en tu navegador:**
```
http://localhost:8000
```

## 📁 Estructura del Proyecto

```
inventario_app/
├── app.py                 # Aplicación principal (FastAPI)
├── requirements.txt       # Dependencias
├── Inventario.xlsx        # Base de datos de productos
├── templates/
│   └── index.html        # Página principal
└── README.md            # Este archivo
```

## 🎨 Estados de Productos

- **🟢 Vigente**: Más de 7 días para vencer
- **🟡 Próximo a vencer**: Entre 1 y 7 días
- **🔴 Vencido**: Ya pasó la fecha

## 🔧 Uso

1. **Agrega un producto** completando el formulario
2. **Filtra** por estado (vencidos, próximos, etc)
3. **Visualiza** estadísticas en tiempo real
4. **Elimina** productos cuando sea necesario

## 💡 Notas

- Los datos de productos se leen de `Inventario.xlsx`
- La lista generada se descarga como archivo Excel
- La app funciona en cualquier navegador moderno

## 📝 Autor

Proyecto de inventario de vencimientos - 2026
