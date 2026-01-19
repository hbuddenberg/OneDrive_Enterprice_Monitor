"""
Script para investigar columnas específicas de estado de sync
"""
import win32com.client

ONEDRIVE_PATH = r"C:\Users\hansbuddenberg\OneDrive - tipartner"
OUTPUT_FILE = "shell_status_test.txt"

# Columnas que parecen relevantes para estado de sync
RELEVANT_COLS = [7, 8, 148, 149, 305, 306]

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    shell = win32com.client.Dispatch("Shell.Application")
    namespace = shell.Namespace(ONEDRIVE_PATH)
    
    f.write("=== COLUMNAS RELEVANTES PARA ESTADO ===\n\n")
    
    # Mostrar nombres de columnas
    f.write("Nombres de columnas:\n")
    for col in RELEVANT_COLS:
        col_name = namespace.GetDetailsOf(None, col)
        f.write(f"  Col {col}: {col_name}\n")
    
    f.write("\n=== CARPETA RAÍZ ===\n")
    root = namespace.Self
    f.write(f"Nombre: {root.Name}\n")
    for col in RELEVANT_COLS:
        value = namespace.GetDetailsOf(root, col)
        col_name = namespace.GetDetailsOf(None, col)
        f.write(f"  Col {col} [{col_name}]: '{value}'\n")
    
    f.write("\n=== ARCHIVOS (todos) ===\n")
    items = namespace.Items()
    for item in items:
        name = item.Name
        f.write(f"\n{name}:\n")
        for col in RELEVANT_COLS:
            value = namespace.GetDetailsOf(item, col)
            if value:
                col_name = namespace.GetDetailsOf(None, col)
                f.write(f"  Col {col} [{col_name}]: '{value}'\n")
        # Si no hay valores relevantes
        has_values = any(namespace.GetDetailsOf(item, c) for c in RELEVANT_COLS)
        if not has_values:
            f.write("  (sin datos de estado)\n")

print(f"Resultados en: {OUTPUT_FILE}")
