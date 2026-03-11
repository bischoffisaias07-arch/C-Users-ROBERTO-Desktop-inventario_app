import pandas as pd
import os

# Function to read Excel file with error handling
def read_excel_with_error_handling(file_path):
    try:
        return pd.read_excel(file_path)
    except Exception as e:
        print(f'Error reading {file_path}: {e}')
        return None

# Function to update DataFrame column names
def update_column_names(df):
    if df is not None:
        df.columns = ['código', 'descripción', 'ean']
    return df

# Main function to process Excel files
def process_excel_files(file1, file2):
    # Read the first Excel file
    df1 = read_excel_with_error_handling(file1)
    # Update column names
    df1 = update_column_names(df1)

    # Read the second Excel file
    df2 = read_excel_with_error_handling(file2)
    # Update column names
    df2 = update_column_names(df2)

    # Process the data as needed
    # (Add your processing logic here)

# Example usage
file1 = 'path/to/first/excel/file.xlsx'
file2 = 'path/to/second/excel/file.xlsx'
process_excel_files(file1, file2)