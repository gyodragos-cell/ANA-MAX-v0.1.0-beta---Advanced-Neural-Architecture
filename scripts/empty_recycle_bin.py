import winshell

try:
    winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
    print("Recycle Bin golit cu succes.")
except Exception as e:
    print(f"Eroare la golirea Recycle Bin-ului: {e}")