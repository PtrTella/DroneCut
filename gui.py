import os

# --- Stability Fixes for macOS / Threads ---
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["QT_MAC_WANTS_LAYER"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import multiprocessing
try:
    if multiprocessing.get_start_method(allow_none=True) is None:
        multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import matplotlib
matplotlib.use('Agg')
# -------------------------------------------

from src.ui.app import DroneCutPro

if __name__ == "__main__":
    app = DroneCutPro()
    app.mainloop()
