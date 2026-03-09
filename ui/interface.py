import gradio as gr
import asyncio
from core.processor import kairos_query

def chat_kairos(message: str, history: list) -> str:
    if not message.strip():
        return "⚠️ Please enter a question!"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    answer = loop.run_until_complete(kairos_query(message))
    loop.close()
    return answer

with gr.Blocks(
    title="Kairos — Real-time AI",
) as demo:

    gr.Markdown("""
    # ⚡ Kairos
    ### *Real-time AI. Cross-verified. Always current.*
    ---
    """)

    chat = gr.ChatInterface(
        fn=chat_kairos,
        examples=[
            "What happened in the world today?",
            "Latest IPL predictions?",
            "Current AI news?",
            "Latest news from India?",
            "Who won the cricket match today?",
        ],
        title="Kairos Chat"
    )

    gr.Markdown("""
    ---
    *⚡ Kairos — Built by Joshua*
    *Powered by Gemini 2.5 Flash + DuckDuckGo + RSS + NewsAPI*
    """)