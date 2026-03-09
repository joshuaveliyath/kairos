from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from ui.interface import demo

if __name__ == "__main__":
    print("⚡ Kairos initializing...")
    print("🌍 Connecting to sources...")
    print("🤖 Loading Gemini 2.5 Flash...")
    print("💾 Starting ChromaDB cache...")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        share=True,
        theme=gr.themes.Soft(),
        css="""
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        *, *::before, *::after {
            font-family: 'Inter', sans-serif !important;
        }
        .gradio-container {
            max-width: 900px;
            margin: auto;
            font-family: 'Inter', sans-serif !important;
        }
        .gr-button-primary {
            background: #0f172a !important;
            border: none !important;
            font-weight: 600 !important;
            font-family: 'Inter', sans-serif !important;
        }
        textarea, input, label, p, h1, h2, h3,
        h4, span, div, button {
            font-family: 'Inter', sans-serif !important;
        }
        """
    )