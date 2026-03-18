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

# ─────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────
_last_sources = []  # Track sources from last response for reputation feedback
_last_all_fetched = [] # Track all fetched sources to punish the unused ones

def chat_kairos(message: dict, history: list, complexity: str, request: gr.Request = None) -> tuple[str, str, gr.update]:
    global _last_sources
    username = request.username if request else "default"
    text = message.get("text", "").strip()
    files = message.get("files") or []

    if not text and not files:
        return "⚠️ Please enter a question or upload an image!", "", gr.update(visible=False)

    # Ensure we have a placeholder question if only files are uploaded
    if files and not text:
        text = "Describe this image and check for any related real-time news."

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    answer, all_fetched = loop.run_until_complete(kairos_query(text, files, complexity, username))
    loop.close()
    
    global _last_all_fetched
    _last_all_fetched = all_fetched
    
    # 💀 Tier 4: Split sources out of main answer
    parts = re.split(r'\n(?=Sources:)', answer, maxsplit=1)
    main_answer = parts[0].strip()
    sources_text = parts[1].strip() if len(parts) > 1 else "No direct citations returned."
    
    # 💀 Tier 6: Parse source names from the citations block for reputation feedback
    _last_sources = re.findall(r'\[\d+\]\s+([^\(—\n]+)', sources_text)
    _last_sources = [s.strip() for s in _last_sources if s.strip()]
    
    return main_answer, sources_text, gr.update(visible=True)

async def run_fact_check(text: str, request: gr.Request = None):
    username = request.username if request else "default"
    return await fact_check_text(text, username)

# ─────────────────────────────────────────────────────────────
# USER MEMORY
# ─────────────────────────────────────────────────────────────
def save_user_pref(key, value, request: gr.Request = None):
    username = request.username if request else "default"
    if not key.strip():
        return load_user_prefs(request)
    update_user_memory(username, key.strip(), value.strip())
    return load_user_prefs(request)

def load_user_prefs(request: gr.Request = None):
    username = request.username if request else "default"
    prefs = get_user_memory(username)
    if not prefs:
        return "No preferences saved yet."
    return "\n".join([f"- **{k}**: {v}" for k, v in prefs.items() if k.lower() not in ["response style", "theme"]])

# ─────────────────────────────────────────────────────────────
# PROACTIVE ALERTS
# ─────────────────────────────────────────────────────────────
def add_alert(topic, request: gr.Request = None):
    username = request.username if request else "default"
    if not topic.strip():
        return refresh_alerts(request)
    add_watch_topic(topic.strip(), username)
    return refresh_alerts(request)

def refresh_alerts(request: gr.Request = None):
    username = request.username if request else "default"
    topics = get_watch_topics(username)
    if not topics:
        return "No topics being watched."
    return "\n".join([f"- 👁️ **{t}**" for t in topics])

def remove_alert(topic, request: gr.Request = None):
    username = request.username if request else "default"
    if not topic.strip():
        return refresh_alerts(request)
    remove_watch_topic(topic.strip(), username)
    return refresh_alerts(request)

# ─────────────────────────────────────────────────────────────
# SOURCE REPUTATION FEEDBACK
# ─────────────────────────────────────────────────────────────
def mark_sources_true(request: gr.Request = None):
    global _last_sources
    global _last_all_fetched
    username = request.username if request else "default"
    results = []
    
    # Good sources get +5 points
    for src in _last_sources:
        new_score = update_source_reputation(src, +5)
        results.append(f"📈 **{src}**: {new_score}/100 (Cited & Verified)")
        
    # Other fetched sources that lacked correct/relevant info: -2 points
    for src in _last_all_fetched:
        if src not in _last_sources:
            new_score = update_source_reputation(src, -2)
            results.append(f"📉 **{src}**: {new_score}/100 (Fetched but Unused)")
            
    return "\n".join(results) if results else "No sources to rate."

def mark_sources_false(request: gr.Request = None):
    global _last_sources
    username = request.username if request else "default"
    results = []
    
    # Sources gave false info: -5 points
    for src in _last_sources:
        new_score = update_source_reputation(src, -5)
        results.append(f"🔴 **{src}**: {new_score}/100 (False Information)")
        
    return "\n".join(results) if results else "No sources to rate."

# ─────────────────────────────────────────────────────────────
# UI LAYOUT
# ─────────────────────────────────────────────────────────────
with gr.Blocks(
    title="Kairos — Real-time AI"
) as demo:

    gr.Markdown("""
    # ⚡ Kairos
    ### *Real-time AI. Cross-verified. Always current.*
    ---
    """)

    with gr.Tabs():

        # ── Tab 1: Chat ──────────────────────────────────────
        with gr.Tab("💬 Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(height=500, label="Kairos")
                    with gr.Row():
                        complexity_toggle = gr.Dropdown(
                            choices=["ELI5", "Simple", "Standard", "Expert"],
                            value="Standard", label="Complexity"
                        )
                    msg = gr.MultimodalTextbox(
                        interactive=True, file_types=["image"],
                        placeholder="Ask anything or upload an image...", show_label=False
                    )
                with gr.Column(scale=1):
                    sources_accordion = gr.Accordion("📚 Sources & Citations", open=False, visible=False)
                    with sources_accordion:
                        sources_box = gr.Markdown("Sources will appear here.")
                    
                    # 💀 Tier 6: True/False feedback
                    gr.Markdown("---\n**Was this answer correct?**")
                    with gr.Row():
                        btn_true = gr.Button("👍 True", variant="primary")
                        btn_false = gr.Button("👎 False", variant="stop")
                    feedback_out = gr.Markdown("")
                    
                    btn_true.click(mark_sources_true, outputs=feedback_out)
                    btn_false.click(mark_sources_false, outputs=feedback_out)

        # ── Tab 2: Fact Checker ──────────────────────────────
        with gr.Tab("🕵️ Fact Checker"):
            gr.Markdown("### Paste text. Kairos checks it sentence-by-sentence.")
            fc_input = gr.Textbox(
                label="Text to verify", lines=6,
                placeholder="Article, WhatsApp forward, Tweet, anything..."
            )
            fc_btn = gr.Button("Verify Facts 🔥", variant="primary")
            fc_output = gr.Markdown("Results will appear here.")
            fc_btn.click(run_fact_check, fc_input, fc_output)

        # ── Tab 3: User Memory ───────────────────────────────
        with gr.Tab("🧠 My Profile"):
            gr.Markdown("### Tell Kairos about yourself. Every answer will be personalized.")
            with gr.Row():
                pref_key = gr.Textbox(label="Preference Name", placeholder="e.g. My Location")
                pref_val = gr.Textbox(label="Preference Value", placeholder="e.g. Kerala, India")
            save_btn = gr.Button("Save Preference 💾", variant="primary")
            gr.Markdown("#### Saved Preferences:")
            prefs_display = gr.Markdown(load_user_prefs())
            save_btn.click(save_user_pref, [pref_key, pref_val], prefs_display)

        # ── Tab 4: Alerts ────────────────────────────────────
        with gr.Tab("🔔 Alerts"):
            gr.Markdown("### Watch topics proactively. Kairos alerts you when things change.")
            with gr.Row():
                with gr.Column():
                    alert_input = gr.Textbox(label="Topic to watch", placeholder="e.g. Bitcoin price, India elections...")
                    alert_btn = gr.Button("Register Watch Topic 👁️", variant="primary")
                    
                    gr.Markdown("#### Watchlist:")
                    alert_list = gr.Markdown(refresh_alerts())
                    
                    remove_input = gr.Textbox(label="Remove Topic", placeholder="Enter exact name to remove")
                    remove_btn = gr.Button("Unwatch 🗑️")
                
                with gr.Column():
                    check_btn = gr.Button("Check for Updates Now 🔥", variant="primary", scale=2)
                    alert_results = gr.Markdown("Click 'Check for Updates' to scan your watchlist.")

            alert_btn.click(add_alert, alert_input, alert_list)
            remove_btn.click(remove_alert, remove_input, alert_list)
            check_btn.click(run_alert_check, outputs=alert_results)

        # ── Tab 5: Source Reputation ─────────────────────────
        with gr.Tab("📊 Source Trust"):
            gr.Markdown("### Check source reputation scores (0-100, base 50).")
            src_query = gr.Textbox(label="Source name (e.g. Reuters, BBC News, Times of India)")
            src_btn = gr.Button("Check Score 🔍", variant="primary")
            src_result = gr.Markdown("")

            def check_score(source):
                if not source.strip():
                    return "Enter a source name."
                score = get_source_reputation(source.strip())
                bar = "█" * (score // 10) + "░" * (10 - score // 10)
                level = "🟢 Trusted" if score >= 60 else ("🟡 Neutral" if score >= 40 else "🔴 Distrusted")
                return f"### **{source}**: {score}/100\nStatus: {level}\n\n`{bar}`"

            src_btn.click(check_score, src_query, src_result)

        # ── Tab 6: Settings ──────────────────────────────
        with gr.Tab("⚙️ Settings"):
            gr.Markdown("### Personalize your Kairos experience.")
            
            with gr.Row():
                theme_toggle = gr.Radio(
                    choices=["Light", "Dark"],
                    label="UI Theme",
                    value="Light"
                )
                style_input = gr.Textbox(
                    label="Response Style Override",
                    placeholder="e.g. Concise and professional, or Funny with emojis..."
                )
            
            save_set_btn = gr.Button("Save Settings ⚙️", variant="primary")
            set_status = gr.Markdown("Settings apply on save.")

            def save_settings(theme, style, request: gr.Request = None):
                username = request.username if request else "default"
                update_user_memory(username, "Theme", theme)
                update_user_memory(username, "Response Style", style)
                # Apply theme change via HTML injection if possible
                css = f"<style>body {{ background-color: {'#1a1a1a' if theme == 'Dark' else 'white'}; color: {'white' if theme == 'Dark' else 'black'}; }}</style>"
                return f"✅ Settings saved for {username}. Theme: {theme}, Style override active.", gr.update(value=css)

            # We need an HTML element to inject the CSS
            theme_inject = gr.HTML("", visible=False)
            save_set_btn.click(save_settings, [theme_toggle, style_input], [set_status, theme_inject])
            
            # Load initial settings
            def load_settings(request: gr.Request = None):
                username = request.username if request else "default"
                prefs = get_user_memory(username)
                theme = prefs.get("Theme", "Light")
                style = prefs.get("Response Style", "")
                css = f"<style>body {{ background-color: {'#1a1a1a' if theme == 'Dark' else 'white'}; color: {'white' if theme == 'Dark' else 'black'}; }}</style>"
                return theme, style, css

            demo.load(load_settings, outputs=[theme_toggle, style_input, theme_inject])
            demo.load(load_user_prefs, outputs=prefs_display)
            demo.load(refresh_alerts, outputs=alert_list)

    # Stores raw (text, files) per turn so files are never lost through Gradio state
    raw_input = gr.State({})

    def user(user_message, history):
        text = user_message.get("text", "") or ""
        files = user_message.get("files") or []
        
        new_history = history.copy()
        # Show text message in chat if present
        if text:
            new_history.append({"role": "user", "content": text})
        # Show each image in chat as a file message
        for f in files:
            new_history.append({"role": "user", "content": {"path": f}})
        # Ensure at least a placeholder if only image sent
        if not text and not files:
            pass  # will be caught in chat_kairos
            
        return gr.update(value={"text": "", "files": []}), new_history, {"text": text, "files": files}
        
    def bot(history, raw, complexity, request: gr.Request = None):
        # Use raw input to reliably pass text + files to backend
        text = (raw.get("text") or "").strip()
        files = raw.get("files") or []
        
        print("TEXT:", text)
        print("FILES:", files)

        message_dict = {"text": text, "files": files}
             
        ans, src, accordion_update = chat_kairos(message_dict, history, complexity, request)
        new_history = history + [{"role": "assistant", "content": ans}]
        return new_history, src, accordion_update

    msg.submit(user, [msg, chatbot], [msg, chatbot, raw_input], queue=False).then(
        bot, [chatbot, raw_input, complexity_toggle], [chatbot, sources_box, sources_accordion]
    )

    gr.Markdown("""
    ---
    *⚡ Kairos — Built by Joshua | Powered by Gemini 2.5 Flash + DuckDuckGo + RSS + NewsAPI*
    """)

