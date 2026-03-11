import pandas as pd

# Load both Excel files
inventario_df = pd.read_excel('Inventario.xlsx')
inventario_ean_df = pd.read_excel('Inventario_EAN.xlsx')

# Normalize codes and EAN by stripping leading zeros
inventario_df['Código'] = inventario_df['Código'].astype(str).str.lstrip('0')
inventario_ean_df['EAN'] = inventario_ean_df['EAN'].astype(str).str.lstrip('0')

# Add search capability for EAN

def search_by_ean(ean):
    result = inventario_ean_df[inventario_ean_df['EAN'] == ean]
    if not result.empty:
        return result
    else:
        return "EAN not found."

# Example usage:
# search_result = search_by_ean('1234567890123')
# print(search_result)
