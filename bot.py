import telebot
import re
import time
import os
from openai import OpenAI
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG (from environment) =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Missing BOT_TOKEN or OPENAI_API_KEY environment variables.")

bot = telebot.TeleBot(BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# In-memory storage for user scripts
user_data = {}

# ============ INLINE KEYBOARD ============
def main_menu_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    btn_upload = InlineKeyboardButton("📤 Upload Script", callback_data="upload")
    btn_generate = InlineKeyboardButton("🆕 Generate New", callback_data="generate")
    btn_help = InlineKeyboardButton("❓ Help", callback_data="help")
    btn_clear = InlineKeyboardButton("🗑️ Clear Script", callback_data="clear")
    markup.add(btn_upload, btn_generate, btn_help, btn_clear)
    return markup

# ============== COMMAND HANDLERS ==============

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    welcome_text = (
        "🤖 **Welcome to the Pro Script Editor Bot!**\n\n"
        "I can edit or generate Python scripts using AI, and also answer general questions.\n"
        "Use the buttons below to get started."
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

# ============ CALLBACK QUERY HANDLERS ============
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "upload":
        bot.send_message(chat_id, "📤 Please upload your Python script file (as a document).")
    elif call.data == "generate":
        bot.send_message(
            chat_id,
            "🆕 Describe the script you want me to generate.\n"
            "Example: *write a script that fetches weather from an API*",
            parse_mode='Markdown'
        )
    elif call.data == "help":
        help_text = (
            "❓ **How to use**\n\n"
            "1. Upload a script using the button or send a `.py` file.\n"
            "2. Send any instruction like:\n"
            "   • `rename function old to new`\n"
            "   • `change 'var' to 'variable'`\n"
            "   • `add a function to log the output`\n"
            "3. Or ask me to generate a new script from scratch.\n"
            "4. I'll return the updated `.py` file.\n"
            "5. You can also ask me general questions – I'll answer without touching your script.\n\n"
            "Use the menu buttons anytime."
        )
        bot.send_message(chat_id, help_text, parse_mode='Markdown')
    elif call.data == "clear":
        if chat_id in user_data:
            del user_data[chat_id]
            bot.send_message(chat_id, "🗑️ Script cleared. You can upload a new one or generate a new script.")
        else:
            bot.send_message(chat_id, "You don't have any script stored yet.")

# ============ FILE UPLOAD ============
@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        script_content = downloaded_file.decode('utf-8')
        user_data[chat_id] = script_content

        bot.reply_to(
            message,
            "✅ File received and saved!\n\nNow send any instruction, or use the menu.",
            reply_markup=main_menu_keyboard()
        )
    except Exception:
        bot.reply_to(message, "❌ Error reading file. Please upload a valid text/script file.")

# ============ TEXT MESSAGES ============
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    user_text = message.text.strip()

    # Check if the user has a script stored
    has_script = chat_id in user_data
    script_content = user_data.get(chat_id, "")

    # ------------------- Determine request type -------------------
    is_generation = bool(re.search(
        r'(write|create|generate|make|new)\s+(a\s+)?(script|code|program|function)',
        user_text, re.IGNORECASE
    ))

    is_edit = bool(re.search(
        r'(change|rename|replace|add|remove|delete|update|modify|edit)\s+',
        user_text, re.IGNORECASE
    )) or bool(re.search(r'\b(function|variable|class|method|import)\b', user_text, re.IGNORECASE))

    is_general = not (is_generation or is_edit)

    # ------------------- Branch logic -------------------
    if is_generation:
        anim_msg = bot.send_message(chat_id, "⏳ *Generating new script...*", parse_mode='Markdown')
        time.sleep(0.8)
        bot.edit_message_text("🧠 *AI is writing the code...*", chat_id, anim_msg.message_id, parse_mode='Markdown')
        try:
            new_script = call_openai_edit("", user_text, is_new=True)
            user_data[chat_id] = new_script
            bot.edit_message_text("✅ *Script generated!*", chat_id, anim_msg.message_id, parse_mode='Markdown')
            send_updated_file(message, new_script, "Here is your new script.")
        except Exception as e:
            bot.edit_message_text(f"❌ AI error: {e}", chat_id, anim_msg.message_id, parse_mode='Markdown')
        return

    if is_edit and has_script:
        # Fast regex fallback
        command, old, new = parse_command(user_text)
        if command is not None:
            modified = apply_replacement(script_content, old, new)
            user_data[chat_id] = modified
            send_updated_file(message, modified, f"✅ Replaced `{old}` → `{new}`")
            return

        # AI edit
        anim_msg = bot.send_message(chat_id, "⏳ *Analyzing your request...*", parse_mode='Markdown')
        time.sleep(0.8)
        bot.edit_message_text("🧠 *Editing with AI...*", chat_id, anim_msg.message_id, parse_mode='Markdown')
        try:
            modified = call_openai_edit(script_content, user_text, is_new=False)
            user_data[chat_id] = modified
            bot.edit_message_text("✅ *Script updated!*", chat_id, anim_msg.message_id, parse_mode='Markdown')
            send_updated_file(message, modified, "Here is your updated script.")
        except Exception as e:
            bot.edit_message_text(f"❌ AI error: {e}", chat_id, anim_msg.message_id, parse_mode='Markdown')
        return

    if is_edit and not has_script:
        bot.send_message(
            chat_id,
            "⚠️ You need to upload a script first before editing it, or ask me to generate a new one.",
            reply_markup=main_menu_keyboard()
        )
        return

    # ---------- GENERAL QUESTION (no code modification) ----------
    anim_msg = bot.send_message(chat_id, "⏳ *Thinking...*", parse_mode='Markdown')
    time.sleep(0.6)
    try:
        answer = ask_general_question(user_text)
        bot.edit_message_text(answer, chat_id, anim_msg.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {e}", chat_id, anim_msg.message_id, parse_mode='Markdown')

# =============== HELPER FUNCTIONS ===============

def call_openai_edit(original_script, instruction, is_new=False):
    if is_new:
        system_prompt = (
            "You are an expert Python developer. Write a new Python script based on the user's request. "
            "Output ONLY the Python code, no explanations, no markdown formatting."
        )
        user_prompt = f"Write a Python script that does the following:\n{instruction}"
    else:
        system_prompt = (
            "You are an expert Python developer. Modify the given script according to the user's instruction. "
            "Output ONLY the full, updated Python code, no extra text."
        )
        user_prompt = f"Original script:\n```python\n{original_script}\n```\n\nInstruction: {instruction}"

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=3000
    )
    output = response.choices[0].message.content.strip()
    # Remove markdown fences if present
    if output.startswith("```python"):
        output = output[9:]
        if output.endswith("```"):
            output = output[:-3]
    elif output.startswith("```"):
        output = output[3:]
        if output.endswith("```"):
            output = output[:-3]
    return output.strip()

def ask_general_question(question):
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer the user's question concisely."},
            {"role": "user", "content": question}
        ],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def send_updated_file(message, script_content, caption):
    chat_id = message.chat.id
    filename = f"modified_script_{chat_id}.py"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(script_content)
        with open(filename, "rb") as f:
            bot.send_document(chat_id, f, caption=caption)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error generating file: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def parse_command(text):
    match = re.search(
        r'rename\s+(function|variable|func|var)\s+[\'"]?(.+?)[\'"]?\s+to\s+[\'"]?(.+?)[\'"]?$',
        text, re.IGNORECASE
    )
    if match:
        return ("rename", match.group(2).strip(), match.group(3).strip())
    match = re.search(
        r'change\s+[\'"]?(.+?)[\'"]?\s+to\s+[\'"]?(.+?)[\'"]?$',
        text, re.IGNORECASE
    )
    if match:
        return ("change", match.group(1).strip(), match.group(2).strip())
    match = re.search(
        r'replace\s+[\'"]?(.+?)[\'"]?\s+with\s+[\'"]?(.+?)[\'"]?$',
        text, re.IGNORECASE
    )
    if match:
        return ("replace", match.group(1).strip(), match.group(2).strip())
    return (None, None, None)

def apply_replacement(script, old, new):
    old_esc = re.escape(old)
    pattern = r'\b' + old_esc + r'\b'
    return re.sub(pattern, new, script)

# ================ START BOT =================

print("🤖 Pro Script Editor Bot is running...")
bot.infinity_polling()
