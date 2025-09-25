# -*- coding: utf-8 -*-

import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai
import os
import logging
import requests
from bs4 import BeautifulSoup

# --- Logging Setup ---
# Bot ke actions aur errors ko track karne ke liye logging set karein
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- API Keys aur Setup ---
# WARNING: Suraksha ke liye API keys ko seedha code mein daalna aacha nahi hai.
# Behtar hai ki aap environment variables ka istemal karein.
# Lekin, aapke request par, keys yahaan daali ja rahi hain.

# 1. Aapka Telegram Token
# --->>> Yahaan aapka token daal diya gaya hai.
TOKEN = "8328744210:AAF_g7q6DiNzxP3ACXtvWXFBpHsjE5KdmUA"

# 2. Gemini API Key (Aapke dwara di gayi)
GEMINI_API_KEY = "AIzaSyCcmY4mFTBtj0ym96Zq0ObT3cszzhxf8hc"

# Gemini Client ko configure karein
if not GEMINI_API_KEY:
    logger.error("CRITICAL: GEMINI_API_KEY nahi mila!")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
        GEMINI_API_KEY = None # Agar configuration fail ho toh key ko None set kar dein

# --- 🔑 College-Specific Knowledge Base (Bot ka Dimag) ---
# Hum AI ko 'System Instruction' denge jisse woh sirf college ke context mein jawab de.
COLLEGE_CONTEXT = """
Aap Arya Main Campus ke liye ek personal AI assistant hain. 
Aapka kaam sirf college se sambandhit prashnon ka sahi aur sateek (accurate) jawab dena hai. 

College ki kuch mukhya (main) jaankari (information) neeche di gayi hai:
- Faculty of B.Tech CS: Dr. Sharma (HOD), Prof. Verma, Ms. Priya Singh. (Yeh jaankari website se verify karein)
- Exam Schedule: Mid-sem exams September ke teesre (third) hafte (week) mein shuru hote hain.
- Library Hours: Subah 9:00 baje se shaam 7:00 baje tak.
- Important Rule: Har student ke liye 75% attendance anivarya (compulsory) hai.
- Contact Email: admission@aryacollege.org
- Agar prashn college ke bahar ka hai, toh vinamrata (politely) se mana kar dein ki aap sirf college ke mamalon mein sahayata kar sakte hain. Jaise: 'Maaf kijiye, main sirf Arya Main Campus se judi jaankari de sakta hoon.'
"""

# --- 🤖 AI Model Setup ---
# Modern SDK ke hisab se model ko pehle se set kar lein
try:
    if GEMINI_API_KEY:
        generation_config = {
            "temperature": 0.7,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048,
        }
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            system_instruction=COLLEGE_CONTEXT
        )
    else:
        model = None
except Exception as e:
    logger.error(f"Gemini Model initialize nahi ho paya: {e}")
    model = None


# --- 🌐 Web Scraping Function (Updated for Arya College) ---
async def scrape_notices() -> str:
    """Arya Main Campus ke notice board se latest notices scrape karta hai."""
    # Aapke college ki asli notice board URL
    NOTICE_BOARD_URL = "https://www.aryacollege.org/notice-board" 

    try:
        # Website se HTML content fetch karein
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(NOTICE_BOARD_URL, headers=headers, timeout=10)
        response.raise_for_status() # Agar koi HTTP error ho toh exception raise karein

        # HTML ko parse karein
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Notices find karein (Arya College website ke table structure ke hisab se)
        # Yeh selector table ke andar har row ki pehli cell ke link (<a>) ko dhoondhta hai
        notice_elements = soup.select("table tbody tr td:first-child a")
        
        if not notice_elements:
            return "Notice board par koi nayi notice nahi mili ya website ka structure badal gaya hai."

        # Notices ko format karein
        formatted_notices = "📢 *Arya Main Campus Website se Latest Notices:*\n\n"
        count = 0
        for notice in notice_elements:
            text = notice.get_text(strip=True)
            if text:
                formatted_notices += f"• {text}\n"
                count += 1
            if count >= 7: # Sirf top 7 notices dikhayein
                break
        
        return formatted_notices if count > 0 else "Notice board par koi nayi notice nahi mili."

    except requests.exceptions.RequestException as e:
        logger.error(f"Website scrape karte waqt error: {e}")
        return "Maaf kijiye, abhi college ki website se connect nahi ho pa raha. Kripya baad mein prayas karein."
    except Exception as e:
        logger.error(f"Notices parse karte waqt error: {e}")
        return "Website se jaankari nikalte waqt ek anjaan error aayi."


# --- 🤖 AI Handling Function ---
async def ai_response(prompt: str) -> str:
    """Gemini API ko call karke user ke sawal ka jawab nikalta hai."""
    if not model:
        return "AI system abhi taiyar nahi hai. Kripya API key aadi check karein."
    try:
        convo = model.start_chat()
        await convo.send_message_async(prompt)
        return convo.last.text
    except Exception as e:
        logger.error(f"Gemini API se response lete waqt error: {e}")
        return f"Dukhad hai, AI se jawab prapt karte samay ek error aa gayi. Kripya baad mein prayas karein."


# --- 💻 Telegram Handlers ---
async def start(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Jab /start command di jaati hai toh yeh message bhejta hai."""
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"Namaste {user_name}! Main Arya Main Campus ka AI Assistant hoon. "
        "Madad ke liye /help type karein."
    )

async def help_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """Jab /help command di jaati hai toh yeh message bhejta hai."""
    help_text = """
    Aap mujhse neeche diye gaye vishayon par sawal pooch sakte hain:

    - *Faculty*: "B.Tech CS ke faculty kaun hain?"
    - *Exams*: "Exam kab se hain?"
    - *Library*: "Library kitne baje tak khuli rehti hai?"
    
    Aap website se live updates ke liye yeh command bhi use kar sakte hain:
    - /notices - Website se latest notices check karein.

    Bas apna sawal type karein aur bhejein!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def notices_command(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """/notices command ko handle karta hai aur website se notices bhejta hai."""
    processing_message = await update.message.reply_text("Arya Main Campus ki website se latest notices check kar raha hoon...")
    notices_text = await scrape_notices()
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=processing_message.message_id,
        text=notices_text,
        parse_mode='Markdown'
    )

async def handle_message(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    """User ke message ko AI function mein bhejta hai aur jawab deta hai."""
    user_text = update.message.text
    logger.info(f"User '{update.message.from_user.username}' se message mila: {user_text}")
    
    processing_message = await update.message.reply_text("Soch raha hoon...")
    
    ai_answer = await ai_response(user_text)
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=processing_message.message_id,
        text=ai_answer
    )


# --- 🚀 Main Bot Runner ---
def main():
    if not TOKEN or TOKEN == "YAHAN_APNA_TELEGRAM_TOKEN_DAALEIN" or not GEMINI_API_KEY:
        logger.critical("API Keys nahi mili. Bot shuru nahi ho sakta. Kripya is file mein apna Telegram Token daalein.")
        return

    application = Application.builder().token(TOKEN).build()

    # Commands ke liye handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("notices", notices_command))

    # Text messages (non-commands) ke liye handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Bot ko chalao
    logger.info("College AI Bot shuru ho gaya hai. Ab Telegram par test karein.")
    application.run_polling(allowed_updates=telegram.Update.ALL_TYPES)

if __name__ == "__main__":
    main()

