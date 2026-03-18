from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from ui.interface import demo, block_css

if __name__ == "__main__":
    print("[!] Kairos initializing...")
    print("[!] Connecting to sources...")
    print("[!] Loading Gemini 3 Flash-Lite...")
    
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"[!] LAN Access enabled at: http://{local_ip}:7860")
    
    # Enable concurrency queueing
    demo.queue() 
    
    # Gradio 6.0: Pass CSS and Theme here. 
    # fill_width is NOT a launch parameter, so it is removed from here.
    demo.launch(
        server_name=local_ip,
        server_port=7860,
        show_error=True,
        share=True,
        auth=[("TEST", "TEST@123"), ("TESTER", "TESTER@123"), ("TESTING", "TESTING@123")],
        theme=gr.themes.Soft(),
        css=block_css
    )