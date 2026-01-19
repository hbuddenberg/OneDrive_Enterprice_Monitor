# Script para investigar los valores de estado de OneDrive via Shell.Application
# Ejecutar con: powershell -ExecutionPolicy Bypass -File test_shell_status.ps1

$OneDrivePath = "C:\Users\hansbuddenberg\OneDrive - tipartner"

Write-Host "============================================"
Write-Host "Investigacion de estado OneDrive via Shell"
Write-Host "Carpeta: $OneDrivePath"
Write-Host "============================================"
Write-Host ""

# Verificar que la carpeta existe
if (-not (Test-Path $OneDrivePath)) {
    Write-Host "ERROR: La carpeta no existe!"
    exit 1
}

# Crear objeto Shell
$shell = New-Object -ComObject Shell.Application
$namespace = $shell.Namespace($OneDrivePath)

if (-not $namespace) {
    Write-Host "ERROR: No se pudo obtener el namespace de la carpeta!"
    exit 1
}

# Obtener el item raiz
$rootItem = $namespace.Self

Write-Host "=== COLUMNAS RELEVANTES ==="

# Columnas conocidas para OneDrive
$columns = @{
    303 = "Availability status"
    217 = "Sync progress"
    0 = "Name"
    1 = "Size"
    2 = "Type"
    3 = "Date modified"
    4 = "Date created"
}

foreach ($col in $columns.Keys | Sort-Object) {
    $value = $namespace.GetDetailsOf($rootItem, $col)
    if ($value) {
        Write-Host "Columna $col ($($columns[$col])): $value"
    }
}

Write-Host ""
Write-Host "=== EXPLORANDO COLUMNAS 0-350 ==="

# Explorar columnas que tienen valor
for ($i = 0; $i -le 350; $i++) {
    $value = $namespace.GetDetailsOf($rootItem, $i)
    if ($value -and $value.Trim() -ne "") {
        $colName = $namespace.GetDetailsOf($null, $i)
        Write-Host "Col $i [$colName]: $value"
    }
}

Write-Host ""
Write-Host "=== ESTADO DE ARCHIVOS (primeros 5) ==="

# Revisar algunos archivos dentro de la carpeta
$files = $namespace.Items() | Select-Object -First 5
foreach ($file in $files) {
    $name = $file.Name
    $status303 = $namespace.GetDetailsOf($file, 303)
    $status217 = $namespace.GetDetailsOf($file, 217)
    Write-Host "  $name -> Col303: $status303 | Col217: $status217"
}

Write-Host ""
Write-Host "============================================"
Write-Host "FIN DE INVESTIGACION"
Write-Host "============================================"
