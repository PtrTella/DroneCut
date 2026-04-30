import os
import sys
import multiprocessing
import logging

# --- Stability Fixes for macOS / AI Libraries ---
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if __name__ == "__main__":
    try:
        if multiprocessing.get_start_method(allow_none=True) is None:
            multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

# Configure root logging to INFO to see technical details
logging.basicConfig(
    level=logging.INFO, 
    format='%(message)s' 
)

# Allow technical details from libraries to flow into the UI console
logging.getLogger("transformers").setLevel(logging.INFO)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
# -----------------------------------------------

from src.ui.app import DroneCutPro

def main():
    """Main Entry Point for DroneCut Pro GUI."""
    app = DroneCutPro()
    app.mainloop()

if __name__ == "__main__":
    main()
