import PyInstaller.__main__
import os
import customtkinter

# Get path to customtkinter
ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    'gui.py',
    '--name=DroneCut',
    '--windowed',
    '--noconsole',
    f'--add-data={ctk_path}:customtkinter',
    '--hidden-import=customtkinter',
    '--clean',
    '--onefile', # Optional: bundle into a single file
])
