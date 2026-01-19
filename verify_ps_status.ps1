$targetPath = "C:\Users\hansbuddenberg\OneDrive - tipartner"
$parentPath = Split-Path -Parent $targetPath
$folderName = Split-Path -Leaf $targetPath

$shell = New-Object -ComObject Shell.Application
$parent = $shell.Namespace($parentPath)
if (!$parent) { "Parent Not Found" | Out-File "ps_status_root.txt"; exit }

$item = $parent.ParseName($folderName)
if (!$item) { "Item Not Found in Parent" | Out-File "ps_status_root.txt"; exit }

# Scan Root Folder Item Columns
foreach ($i in 0..400) {
    $val = $parent.GetDetailsOf($item, $i)
    if ($val) {
        $name = $parent.GetDetailsOf($null, $i)
        "ID: $i | Name: '$name' | Value: '$val'" | Out-File "ps_scan_root.txt" -Append -Encoding UTF8
    }
}
