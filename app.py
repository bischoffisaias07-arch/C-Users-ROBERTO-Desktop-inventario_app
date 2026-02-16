from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# Archivo para guardar datos
DATA_FILE = 'products.json'

def load_products():
    """Cargar productos del archivo JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_products(products):
    """Guardar productos en archivo JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def get_product_status(expiry_date_str):
    """Determinar estado del producto"""
    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
    today = datetime.now().date()
    days_remaining = (expiry_date - today).days
    
    if days_remaining < 0:
        return 'expired', 'Vencido'
    elif days_remaining <= 7:
        return 'expiring', 'Próximo a vencer'
    else:
        return 'valid', 'Vigente'

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    """Obtener todos los productos"""
    products = load_products()
    
    # Agregar información de estado
    for product in products:
        status, label = get_product_status(product['expiryDate'])
        product['status'] = status
        product['statusLabel'] = label
        
        # Calcular días restantes
        expiry_date = datetime.strptime(product['expiryDate'], '%Y-%m-%d').date()
        today = datetime.now().date()
        product['daysRemaining'] = (expiry_date - today).days
    
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    """Agregar nuevo producto"""
    data = request.json
    
    products = load_products()
    new_product = {
        'id': int(datetime.now().timestamp() * 1000),
        'name': data.get('name'),
        'expiryDate': data.get('expiryDate'),
        'quantity': int(data.get('quantity', 1)),
        'category': data.get('category'),
        'dateAdded': datetime.now().isoformat()
    }
    
    products.append(new_product)
    save_products(products)
    
    return jsonify(new_product), 201

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Eliminar producto"""
    products = load_products()
    products = [p for p in products if p['id'] != product_id]
    save_products(products)
    
    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas"""
    products = load_products()
    
    total = len(products)
    expired = sum(1 for p in products if get_product_status(p['expiryDate'])[0] == 'expired')
    expiring = sum(1 for p in products if get_product_status(p['expiryDate'])[0] == 'expiring')
    valid = sum(1 for p in products if get_product_status(p['expiryDate'])[0] == 'valid')
    
    return jsonify({
        'total': total,
        'expired': expired,
        'expiring': expiring,
        'valid': valid
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
