import tkinter as tk
import time

def main():
    root = tk.Tk()
    root.title("Microsoft OneDrive - Iniciar sesión")
    root.geometry("400x300")
    
    label = tk.Label(root, text="Dummy Auth Window\nWaiting for focus...", font=("Arial", 14))
    label.pack(expand=True)
    
    # Bring to back initially
    root.iconify()
    root.update()
    time.sleep(1)
    root.deiconify()
    root.lower() # Push behind other windows
    
    print("Window created and pushed to background.")
    
    # Auto close after 15 seconds
    root.after(15000, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    main()
