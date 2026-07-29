import streamlit as st
import pandas as pd
from weasyprint import HTML
import base64
import os
from PIL import Image
import io
import urllib.parse
import requests
import json
import random
import re
import google.generativeai as genai

st.set_page_config(page_title="מחולל תפריטים דינמי v4.5 AI", layout="centered", page_icon="🍹")

st.title("🍹 מחולל תפריטים והצעות הגשה")
st.write("מערכת חכמה לסוכני שטח – התאמה אישית, עריכה בזמן אמת ומנוע עיצוב AI.")

# ==============================================================================
# 🔗 קישור קבוע ומובנה לגוגל שיטס של העסק
# ==============================================================================
DEFAULT_GSHEET_URL = "[https://docs.google.com/spreadsheets/d/1i0k5wIIgleWMY8LyAJVwrfXywnNP2kKv4WjcNCIvyBE/edit?usp=sharing](https://docs.google.com/spreadsheets/d/1i0k5wIIgleWMY8LyAJVwrfXywnNP2kKv4WjcNCIvyBE/edit?usp=sharing)"

# --- הגדרת מנוע Gemini API ---
gemini_key = st.secrets.get("GEMINI_API_KEY", None)
if gemini_key:
    genai.configure(api_key=gemini_key)

def get_csv_url(url):
    try:
        if "/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            return f"[https://docs.google.com/spreadsheets/d/](https://docs.google.com/spreadsheets/d/){sheet_id}/export?format=csv"
    except Exception:
        pass
    return None

csv_url = get_csv_url(DEFAULT_GSHEET_URL)

@st.cache_data(ttl=10)
def load_data(url):
    if url:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"שגיאה בחיבור לגוגל שיטס: {e}")
    return None

df_cocktails = load_data(csv_url)

if df_cocktails is None or df_cocktails.empty:
    st.error("⚠️ לא ניתן לטעון את מאגר הקוקטיילים. אנא ודא שקישור הגוגל שיטס תקין וציבורי.")
    st.stop()

# --- פונקציית סריקה רקורסיבית מקיפה וחכמה ---
def find_card_file_unbeatable(drink_name):
    def clean_str(s):
        return "".join(c.lower() for c in str(s) if c.isalnum())

    target_clean = clean_str(drink_name)
    valid_extensions = ['.png', '.jpg', '.jpeg', '.pdf']

    for root, dirs, files in os.walk("."):
        if "/." in root or root.startswith("./."):
            continue
            
        for filename in files:
            name_without_ext, ext = os.path.splitext(filename)
            ext_lower = ext.lower()
            
            if ext_lower in valid_extensions:
                if clean_str(name_without_ext) == target_clean:
                    full_path = os.path.join(root, filename)
                    return full_path, ext_lower

    return None, None

# --- פונקציה חכמה להסרת רקע לבן מתמונות לוגו ---
def remove_white_background(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        datas = img.getdata()
        
        new_data = []
        for item in datas:
            if item[0] > 225 and item[1] > 225 and item[2] > 225:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
                
        img.putdata(new_data)
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()
    except Exception:
        return image_bytes

# --- 1. פרטי העסק והכותרות ---
st.subheader("1. פרטי העסק והכותרות")

col_title, col_align = st.columns([2, 1])
with col_title:
    menu_title = st.text_input("כותרת ראשית לתפריט:", value="COCKTAIL MENU")
with col_align:
    text_align = st.selectbox("כיוון כותרת:", options=["מרכז", "שמאל (אנגלית)", "ימין (עברית)"])

menu_subtitle = st.text_input("תת-כותרת / תיאור קצר (רשות):", value="", placeholder="למשל: תפריט קוקטיילים קלאסי | Happy Hour")

align_css = "center" if "מרכז" in text_align else "left" if "שמאל" in text_align else "right"

st.markdown("---")
st.subheader("2. עיצוב, צבעים ומנוע AI")

bg_style = st.selectbox(
    "בחר סגנון עיצוב לתפריט (130x240 מ\"מ):", 
    [
        "🎨 עיצוב אומנותי אוטומטי ב-AI (הקלדת תיאור חופשי)",
        "שחור קלאסי (רקע שחור, מלל לבן)", 
        "לבן קלאסי (רקע לבן, מלל שחור)", 
        "התאמת צבעים אישית (חופשי)", 
        "רקע תמונה מותאם אישית (העלאת קובץ)"
    ]
)

bg_base64 = ""
bg_color_css = "background-color: #000000;"
text_color_css = "#ffffff"
border_color_css = "#ffffff"
line_color_css = "#555555"
desc_color_css = "#cccccc"

# --- טיפול בייצור עיצוב AI חסין שגיאות ---
if bg_style == "🎨 עיצוב אומנותי אוטומטי ב-AI (הקלדת תיאור חופשי)":
    st.info("🤖 **מעצב ה-AI מוכן!** הקלד את האווירה/הנושא המבוקש והמערכת תייצר עבורך פלטת צבעים ורקע ייחודי.")
    ai_prompt = st.text_area(
        "תאר את הקונספט או האווירה של האירוע/הבר:", 
        placeholder="למשל: מסיבת שקיעה בחוף במיקונוס, צבעי תכלת וזהב, קליל ויוקרתי..."
    )
    
    if st.button("🪄 הפיקו עיצוב ב-AI", use_container_width=True):
        if not ai_prompt:
            st.warning("אנא הקלד תיאור קצר כדי שה-AI יידע מה לעצב.")
        elif not gemini_key:
            st.error("מפתח GEMINI_API_KEY חסר ב-Secrets של Streamlit.")
        else:
            with st.spinner("✨ מנוע ה-AI מעצב כעת את התפריט..."):
                try:
                    system_instructions = """
                    You are an expert graphic designer for cocktail menus.
                    Analyze the user's concept prompt and return ONLY a valid JSON object (without markdown code blocks) containing:
                    - bg_color: Hex color string for background (e.g. "#000000")
                    - text_color: Hex color string for text
                    - border_color: Hex color string for borders
                    - line_color: Hex color string for lines
                    - desc_color: Hex color string for descriptions
                    - image_prompt: A detailed English prompt describing an artistic, atmospheric background graphic with NO text, suitable for a menu background.
                    """
                    
                    candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash']
                    response = None
                    last_err = None
                    
                    for m_name in candidate_models:
                        try:
                            model = genai.GenerativeModel(m_name)
                            res = model.generate_content(f"{system_instructions}\nUser concept: {ai_prompt}")
                            if res and res.text:
                                response = res
                                break
                        except Exception as e:
                            last_err = e
                            continue
                    
                    if not response:
                        raise last_err or Exception("לא התקבל מענה מאף אחד מדגמי Gemini.")

                    # ניקוי בטוח ועמיד מפני שגיאות מירכאות
                    clean_res = response.text
                    for fence in ["
