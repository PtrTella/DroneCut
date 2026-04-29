import os
import subprocess
import sys

def build():
    print("🚀 Inizio processo di packaging per macOS...")
    
    # 1. Trova il percorso di customtkinter
    # Basato sul controllo precedente
    ctk_path = ".venv/lib/python3.14/site-packages/customtkinter"
    if not os.path.exists(ctk_path):
        # Fallback per ricerca dinamica se la versione di python cambia
        import glob
        matches = glob.glob(".venv/lib/python3.*/site-packages/customtkinter")
        if matches:
            ctk_path = matches[0]
        else:
            print("❌ Errore: Non riesco a trovare customtkinter nel .venv.")
            return

    # 2. Percorso dei modelli locali e icona
    models_path = "src/models"
    icon_path = "assets/icon.icns"
    
    # 3. Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--windowed",
        "--name=DroneCutPro",
        f"--add-data={models_path}:src/models",
        f"--add-data={ctk_path}:customtkinter",
    ]

    # Aggiunta icona se esiste
    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")
        print(f"🎨 Icona trovata: {icon_path}")
    else:
        print("ℹ️ Nessuna icona trovata in assets/icon.icns, userò quella di default.")

    cmd += [
        "--hidden-import=cv2",
        "--hidden-import=torch",
        "--hidden-import=transformers",
        "--hidden-import=PIL.ImageResampling",
        "--collect-all=transformers",
        "--collect-all=tqdm",
        "--clean",
        "gui.py"
    ]
    
    print(f"🛠 Esecuzione comando: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Build completata con successo!")
        print("📁 Trovi l'applicazione in: dist/DroneCutPro.app")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Errore durante la build: {e}")
    except FileNotFoundError:
        print("\n❌ Errore: PyInstaller non è installato nell'ambiente corrente.")
        print("💡 Prova a installarlo con: pip install pyinstaller")

if __name__ == "__main__":
    build()
