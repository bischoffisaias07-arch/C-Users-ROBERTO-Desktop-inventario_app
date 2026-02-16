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

## 📋 Requisitos

- Python 3.7+
- Flask
- pip

## ⚙️ Instalación

1. **Clona o descarga el repositorio**

2. **Instala las dependencias:**
```bash
pip install -r requirements.txt
```

3. **Ejecuta la aplicación:**
```bash
python app.py
```

4. **Abre en tu navegador:**
```
http://localhost:5000
```

## 📁 Estructura del Proyecto

```
inventario_app/
├── app.py                 # Aplicación principal (Flask)
├── requirements.txt       # Dependencias
├── templates/
│   └── index.html        # Página principal
├── products.json         # Base de datos (se crea automáticamente)
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

- Los datos se guardan en `products.json`
- La app funciona sin conexión a internet
- Puedes usar en cualquier navegador moderno

## 📝 Autor

Proyecto de inventario de vencimientos - 2026
