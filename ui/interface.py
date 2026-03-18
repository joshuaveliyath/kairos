import gradio as gr
import asyncio
import re
from core.processor import kairos_query, fact_check_text, check_all_alerts
from core.memory import (
    update_user_memory, get_user_memory,
    add_watch_topic, get_watch_topics, remove_watch_topic,
    update_source_reputation, get_source_reputation
)

# ── Alert Action ─────────────────────────────────────────────
async def run_alert_check(request: gr.Request = None):
    username = request.username if request else "default"
    return await check_all_alerts(username)

# ── Chat Logic ───────────────────────────────────────────────
_last_sources = []  
_last_all_fetched = [] 

async def chat_kairos(message: dict, history: list, complexity: str, request: gr.Request = None):
    global _last_sources, _last_all_fetched
    username = request.username if request else "default"
    text = message.get("text", "").strip()
    files = message.get("files") or []

    if not text and not files:
        yield history + [{"role": "assistant", "content": "⚠️ Please enter a question or upload an image!"}], "", gr.update(visible=False)
        return

    history.append({"role": "assistant", "content": "*Thinking...*" })
    yield history, "", gr.update(visible=False)

    full_answer = ""
    all_fetched = []
    
    async for chunk, fetched in kairos_query(text, files, complexity, username):
        full_answer = chunk
        all_fetched = fetched
        parts = re.split(r'\n(?=Sources:)', full_answer, maxsplit=1)
        main_answer = parts[0].strip()
        sources_text = parts[1].strip() if len(parts) > 1 else "Fetching citations..."
        history[-1]["content"] = main_answer
        yield history, sources_text, gr.update(visible=True)
    
    _last_all_fetched = all_fetched
    parts = re.split(r'\n(?=Sources:)', full_answer, maxsplit=1)
    sources_text = parts[1].strip() if len(parts) > 1 else "No direct citations returned."
    _last_sources = re.findall(r'\[\d+\]\s+([^\(—\n]+)', sources_text)
    _last_sources = [s.strip() for s in _last_sources if s.strip()]

# ── UI CSS ────────────────────────────────────────────────────
block_css = """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    body, .gradio-container {
        font-family: 'Inter', sans-serif !important;
        margin: 0 !important; padding: 0 !important;
        background-color: #ffffff;
    }

    /* Sidebar Layout */
    .sidebar-container {
        background-color: #f9fafb !important;
        border-right: 1px solid #e5e7eb !important;
        height: 100vh !important;
        padding: 1.5rem 1rem !important;
        display: flex !important;
        flex-direction: column !important;
    }

    .nav-btn {
        text-align: left !important;
        justify-content: flex-start !important;
        border: none !important;
        margin-bottom: 0.5rem !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
        border-radius: 8px !important;
        background: transparent !important;
        transition: all 0.2s ease;
        color: #374151 !important;
    }

    .nav-btn:hover { background-color: #f3f4f6 !important; }
    
    .sidebar-footer {
        margin-top: auto !important;
        padding-top: 1rem !important;
        border-top: 1px solid #e5e7eb !important;
    }

    .main-content {
        height: 100vh !important;
        overflow-y: auto !important;
        padding: 0 !important;
    }

    .page-container {
        padding: 2rem 10% !important;
    }

    /* Chat Styling */
    .chat-window { border: none !important; flex-grow: 1 !important; }
    
    .input-bar-container {
        padding: 1rem 15% 2rem 15% !important;
        background: white;
    }

    /* ── BORDERED TYPING BOXES ── */
    /* Targets the Multimodal Textbox and Standard Textboxes */
    .input-bar-container .gradio-textbox, 
    .input-bar-container .block,
    .page-container .gradio-textbox,
    .page-container .block {
        border: 1.5px solid #e5e7eb !important;
        border-radius: 12px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        background-color: #ffffff !important;
    }

    /* Hover & Focus state for the borders */
    .input-bar-container .block:focus-within,
    .page-container .block:focus-within {
        border-color: #6366f1 !important; /* Modern Indigo color */
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }

    /* Fix for Multimodal Textbox specific wrapper */
    div.token-multimodal {
        border: none !important; /* Remove inner border if Gradio adds one */
    }

    @media (max-width: 768px) {
        .sidebar-container { width: 100% !important; height: auto !important; border-right: none; }
        .input-bar-container { padding: 1rem !important; }
    }
"""

with gr.Blocks(title="Kairos — Real-time AI", fill_width=True) as demo:
    
    raw_input = gr.State({})

    with gr.Row(equal_height=False):
        # ── SIDEBAR COLUMN ──
        with gr.Column(scale=1, elem_classes="sidebar-container", min_width=250):
            gr.Markdown("## ⚡ Kairos")
            btn_chat = gr.Button("💬 Chat", elem_classes="nav-btn")
            btn_fact = gr.Button("🕵️ Fact Checker", elem_classes="nav-btn")
            btn_profile = gr.Button("🧠 My Profile", elem_classes="nav-btn")
            btn_alerts = gr.Button("🔔 Alerts", elem_classes="nav-btn")
            btn_trust = gr.Button("📊 Source Trust", elem_classes="nav-btn")
            btn_settings = gr.Button("⚙️ Settings", elem_classes="nav-btn")
            
            # Using a sub-column with the footer class to push to bottom
            with gr.Column(elem_classes="sidebar-footer"):
                gr.Markdown("*Built by Joshua*")
                gr.Markdown("V 2.5 | Gemini 3.1 Flash-Lite")

        # ── CONTENT COLUMN ──
        with gr.Column(scale=5, elem_classes="main-content"):
            
            # 1. Chat Page
            with gr.Column(visible=True) as chat_page:
                chatbot = gr.Chatbot(show_label=False, elem_classes="chat-window", height="78vh")
                with gr.Column(elem_classes="input-bar-container"):
                    with gr.Row():
                        msg = gr.MultimodalTextbox(
                            placeholder="Message Kairos...", 
                            container=False, scale=9
                        )
                        complexity = gr.Dropdown(
                            ["ELI5", "Standard", "Expert"], 
                            value="Standard", container=False, scale=1
                        )
                    sources_acc = gr.Accordion("📚 Citations", open=False, visible=False)
                    with sources_acc:
                        sources_md = gr.Markdown("No citations yet.")

            # 2. Fact Checker Page
            with gr.Column(visible=False, elem_classes="page-container") as fact_page:
                gr.Markdown("# 🕵️ Fact Checker")
                fc_in = gr.Textbox(label="Paste content to verify", lines=10)
                fc_btn = gr.Button("Verify Facts 🔥", variant="primary")
                fc_out = gr.Markdown("Results will appear here.")

            # 3. Profile Page
            with gr.Column(visible=False, elem_classes="page-container") as profile_page:
                gr.Markdown("# 🧠 User Memory")
                with gr.Row():
                    pref_k = gr.Textbox(label="Preference Name")
                    pref_v = gr.Textbox(label="Value")
                save_pref = gr.Button("Save Preference", variant="primary")
                gr.Markdown("### Your Saved Data")
                profile_display = gr.Markdown("Loading preferences...")

            # 4. Alerts Page
            with gr.Column(visible=False, elem_classes="page-container") as alerts_page:
                gr.Markdown("# 🔔 Proactive Alerts")
                alert_in = gr.Textbox(label="Topic to watch")
                reg_btn = gr.Button("Register Watch Topic", variant="primary")
                alert_list_md = gr.Markdown("No active alerts.")

            # 5. Trust Page
            with gr.Column(visible=False, elem_classes="page-container") as trust_page:
                gr.Markdown("# 📊 Source Reputation")
                src_in = gr.Textbox(label="Enter Domain (e.g. bbc.com)")
                check_src_btn = gr.Button("Check Score", variant="primary")
                trust_out = gr.Markdown("")

            # 6. Settings Page
            with gr.Column(visible=False, elem_classes="page-container") as settings_page:
                gr.Markdown("# ⚙️ Settings")
                theme_rad = gr.Radio(["Light", "Dark"], value="Light", label="Interface Theme")
                style_over = gr.Textbox(label="Response Style Override")
                save_set = gr.Button("Apply Settings", variant="primary")

    # ── Navigation Logic ──
    pages = [chat_page, fact_page, profile_page, alerts_page, trust_page, settings_page]
    
    def navigate(target):
        return [gr.update(visible=(target == "Chat")), 
                gr.update(visible=(target == "Fact")),
                gr.update(visible=(target == "Profile")),
                gr.update(visible=(target == "Alerts")),
                gr.update(visible=(target == "Trust")),
                gr.update(visible=(target == "Settings"))]

    btn_chat.click(lambda: navigate("Chat"), outputs=pages)
    btn_fact.click(lambda: navigate("Fact"), outputs=pages)
    btn_profile.click(lambda: navigate("Profile"), outputs=pages)
    btn_alerts.click(lambda: navigate("Alerts"), outputs=pages)
    btn_trust.click(lambda: navigate("Trust"), outputs=pages)
    btn_settings.click(lambda: navigate("Settings"), outputs=pages)

    # ── Chat Functionality ──
    def user_step(user_msg, history):
        txt = user_msg.get("text", "")
        imgs = user_msg.get("files", [])
        new_hist = history + [{"role": "user", "content": txt}]
        for img in imgs: new_hist.append({"role": "user", "content": {"path": img}})
        return gr.update(value={"text": "", "files": []}), new_hist, {"text": txt, "files": imgs}

    msg.submit(user_step, [msg, chatbot], [msg, chatbot, raw_input]).then(
        chat_kairos, [raw_input, chatbot, complexity], [chatbot, sources_md, sources_acc]
    )