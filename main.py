from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from ui.interface import demo

if __name__ == "__main__":
    print("[!] Kairos initializing...")
    print("[!] Connecting to sources...")
    print("[!] Loading Gemini 3 Flash-Lite...")
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[!] LAN Access enabled at: http://{local_ip}:7860")
    
    demo.queue() # Tier 7: Enable concurrency queueing
    demo.launch(
        server_name=local_ip, # 💀 Tier 7: Bind to specific IP for safety
        server_port=7860,
        show_error=True,
        share=True,
        auth=[("Joshua", "jonathan@123"), ("Jomesh", "Chinnu@123"), ("Ann", "Jomesh@123")], # 💀 Tier 8: Multi-User Support
        theme=gr.themes.Soft(),
        css="""
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body {
            font-family: 'Inter', sans-serif;
        }
        .gradio-container {
            max-width: 900px !important;
            margin: auto !important;
        }
        .gr-button-primary {
            background: #0f172a !important;
            border: none !important;
            font-weight: 600 !important;
        }
        """

    )
