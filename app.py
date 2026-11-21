# Einstiegspunkt für Hugging Face Spaces (Gradio-SDK, kostenlos).
# Gradio selbst wird nicht benutzt: Hier startet direkt der Tolk-Live-Server auf Port 7860.
import os
import runpy

os.environ.setdefault("PORT", "7860")
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py"), run_name="__main__")
