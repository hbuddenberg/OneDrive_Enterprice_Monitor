# Test script to see what OneDrive windows are visible
Write-Host "=== OneDrive Processes ==="
$procs = Get-Process -Name OneDrive -ErrorAction SilentlyContinue
foreach ($proc in $procs) {
    Write-Host "PID: $($proc.Id) | Title: '$($proc.MainWindowTitle)'"
}

Write-Host "`n=== All Windows with 'OneDrive' in title ==="
Get-Process | Where-Object { $_.MainWindowTitle -like '*OneDrive*' } | ForEach-Object {
    Write-Host "Process: $($_.ProcessName) | Title: '$($_.MainWindowTitle)'"
}

Write-Host "`n=== Windows with auth keywords ==="
Get-Process | Where-Object { 
    $_.MainWindowTitle -match 'Sign in|Iniciar ses|Contrase|Password|credential|credencial|vuelve'
} | ForEach-Object {
    Write-Host "Process: $($_.ProcessName) | Title: '$($_.MainWindowTitle)'"
}
