"""Debug script to list all system tray icons legacy properties."""

from pywinauto import Desktop
from pathlib import Path

def list_tray_icons():
    """List all icons in the system tray with legacy accessible properties."""
    desktop = Desktop(backend="uia")
    output_lines = []
    
    output_lines.append("=" * 60)
    output_lines.append("SYSTEM TRAY ICON EXPLORER (LEGACY)")
    output_lines.append("=" * 60)
    
    try:
        taskbar = desktop.window(class_name="Shell_TrayWnd")
        
        output_lines.append("\n=== All OneDrive elements in taskbar ===")
        for ctrl in taskbar.descendants():
            try:
                text = ctrl.window_text()
                if text and "onedrive" in text.lower():
                    output_lines.append(f"FOUND ELEMENT: {text}")
                    
                    # Try LegacyIAccessiblePattern
                    try:
                        legacy = ctrl.iface_value.GetCurrentPattern(10018) # LegacyIAccessiblePatternId
                        output_lines.append(f"  - Legacy Name: '{legacy.CurrentName}'")
                        output_lines.append(f"  - Legacy Help: '{legacy.CurrentHelp}'")
                        output_lines.append(f"  - Legacy Description: '{legacy.CurrentDescription}'")
                        output_lines.append(f"  - Legacy Value: '{legacy.CurrentValue}'")
                    except Exception as e:
                        output_lines.append(f"  - Legacy Pattern not supported: {e}")

            except Exception:
                pass
            
    except Exception as e:
        output_lines.append(f"Error: {e}")
    
    output_lines.append("\n" + "=" * 60)
    
    # Write to file
    output_path = Path("tray_debug_output.txt")
    output_path.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Output written to {output_path.absolute()}")

if __name__ == "__main__":
    list_tray_icons()
