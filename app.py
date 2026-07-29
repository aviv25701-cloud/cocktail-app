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
import google.generativeai as genai

st.set_page_config(page_title="מחולל תפריטים דינמי v4.3 AI", layout="centered", page_icon="🍹")

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
            df = pd.read_csv(url)
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"שגיאה בחיבור לגוגל שיטס: {e}")
    return None

df_cocktails = load_data(csv_url)

if df_cocktails is None or df_cocktails.empty:
    st.error("⚠️ לא ניתן לטעון את מאגר הקוקטיילים. אנא ודא שקישור הגוגל שיטס בקוד תקין וציבורי.")
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

                    # התיקון כאן: מניעת Syntax Error עם טיפול נכון במחרוזות
                    clean_res = response.text.replace("```json", "").replace("```", "").strip()
                    ai_config = json.loads(clean_res)
                    
                    st.session_state['ai_bg_color'] = ai_config.get('bg_color', '#000000')
                    st.session_state['ai_text_color'] = ai_config.get('text_color', '#ffffff')
                    st.session_state['ai_border_color'] = ai_config.get('border_color', '#ffffff')
                    st.session_state['ai_line_color'] = ai_config.get('line_color', '#888888')
                    st.session_state['ai_desc_color'] = ai_config.get('desc_color', '#cccccc')
                    
                    prompt_encoded = urllib.parse.quote(ai_config.get('image_prompt', 'abstract cocktail background'))
                    seed = random.randint(1, 100000)
                    pollinations_url = f"[https://pollinations.ai/p/](https://pollinations.ai/p/){prompt_encoded}?width=650&height=1200&seed={seed}&nologo=true"
                    
                    img_res = requests.get(pollinations_url, timeout=15)
                    if img_res.status_code == 200:
                        st.session_state['ai_bg_b64'] = base64.b64encode(img_res.content).decode("utf-8")
                        st.success("🎉 העיצוב הופק בהצלחה על ידי ה-AI!")
                    else:
                        st.warning("פלטת הצבעים יוצרה, אך התמונה לא נטענה. יעשה שימוש בצבע הרקע שנבחר.")
                        
                except Exception as e:
                    st.error(f"שגיאה בייצור עיצוב ה-AI: {e}")

    if 'ai_bg_color' in st.session_state:
        bg_color_css = f"background-color: {st.session_state['ai_bg_color']};"
        text_color_css = st.session_state['ai_text_color']
        border_color_css = st.session_state['ai_border_color']
        line_color_css = st.session_state['ai_line_color']
        desc_color_css = st.session_state['ai_desc_color']
        if 'ai_bg_b64' in st.session_state:
            bg_base64 = st.session_state['ai_bg_b64']

elif bg_style == "שחור קלאסי (רקע שחור, מלל לבן)":
    bg_color_css = "background-color: #000000;"
    text_color_css = "#ffffff"
    border_color_css = "#ffffff"
    line_color_css = "#444444"
    desc_color_css = "#cccccc"
elif bg_style == "לבן קלאסי (רקע לבן, מלל שחור)":
    bg_color_css = "background-color: #ffffff;"
    text_color_css = "#111111"
    border_color_css = "#111111"
    line_color_css = "#cccccc"
    desc_color_css = "#555555"
elif bg_style == "התאמת צבעים אישית (חופשי)":
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        custom_bg = st.color_picker("צבע רקע:", "#000000")
        bg_color_css = f"background-color: {custom_bg};"
    with col_c2:
        text_color_css = st.color_picker("צבע טקסט וכותרת:", "#ffffff")
    with col_c3:
        border_color_css = st.color_picker("צבע מסגרת וקווים:", "#ffffff")
    line_color_css = border_color_css
    desc_color_css = text_color_css
else:
    uploaded_bg = st.file_uploader("העלה קובץ תמונת רקע (מומלץ במידות 130x240 מ\"מ):", type=["png", "jpg", "jpeg"], key="bg_uploader")
    if uploaded_bg:
        bg_base64 = base64.b64encode(uploaded_bg.read()).decode("utf-8")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        text_color_css = st.color_picker("צבע טקסט:", "#ffffff")
    with col_c2:
        border_color_css = st.color_picker("צבע מסגרת:", "#ffffff")
    line_color_css = border_color_css
    desc_color_css = text_color_css

border_option = st.radio("סגנון מסגרת סביב התפריט:", ["מסגרת עדינה (ברירת מחדל)", "מסגרת עבה", "ללא מסגרת"], horizontal=True)

if border_option == "מסגרת עדינה (ברירת מחדל)":
    border_style_css = f"border: 1.5px solid {border_color_css};"
elif border_option == "מסגרת עבה":
    border_style_css = f"border: 3.5px solid {border_color_css};"
else:
    border_style_css = "border: none;"

st.markdown("---")
st.subheader("3. לוגו והערות בתחתית (Footer)")

col_l1, col_l2 = st.columns([2, 1])
with col_l1:
    uploaded_logo = st.file_uploader("העלה לוגו של בית העסק (PNG / JPG):", type=["png", "jpg", "jpeg"], key="logo_uploader")
    auto_remove_bg = st.checkbox("🧹 הסר רקע לבן מהלוגו באופן אוטומטי", value=True)
with col_l2:
    footer_text = st.text_input("הערת שוליים בתחתית (רשות):", value="", placeholder="למשל: המחירים כוללים מע\"מ | ט.ל.ח")

logo_base64 = ""
if uploaded_logo:
    logo_bytes = uploaded_logo.read()
    if auto_remove_bg:
        logo_bytes = remove_white_background(logo_bytes)
    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

st.markdown("---")
st.subheader("4. בחירת מוצרים, תמחור ועריכה בזמן אמת")

selected_drinks_data = []

for idx, row in df_cocktails.iterrows():
    is_selected = st.checkbox(f"🍹 **{row['Name']}**", key=f"select_{row['ID']}")
    
    if is_selected:
        with st.expander(f"עריכת פרטים עבור: {row['Name']}", expanded=True):
            col_name, col_price = st.columns([3, 1])
            with col_name:
                editable_name = st.text_input("שם המשקה בתפריט:", value=row['Name'], key=f"name_edit_{row['ID']}")
            with col_price:
                editable_price = st.text_input("מחיר (₪):", value="45", key=f"price_edit_{row['ID']}")
                
            editable_ingredients = st.text_area("מרכיבים (הפרד באמצעות |):", value=row['Ingredients'], key=f"ing_edit_{row['ID']}")
            
        selected_drinks_data.append({
            "ID": row['ID'],
            "Name": editable_name,
            "OriginalName": row['Name'],
            "Price": editable_price,
            "Ingredients": editable_ingredients
        })

st.markdown("---")

if st.button("🚀 הפק תפריט וכרטיסיות ברמן מעוצבות", use_container_width=True):
    if not selected_drinks_data:
        st.error("❌ אנא בחר לפחות קוקטייל אחד כדי להפיק קבצים!")
    else:
        menu_items_html = ""
        for item in selected_drinks_data:
            menu_items_html += f"""
            <div class="menu-item">
                <div class="item-header">
                    <span class="item-name">{item['Name']}</span>
                    <span class="item-line"></span>
                    <span class="item-price">₪{item['Price']}</span>
                </div>
                <div class="item-desc">{item['Ingredients']}</div>
            </div>
            """

        logo_html = f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" class="logo"></div>' if logo_base64 else ''
        footer_note_html = f'<div class="footer-note">{footer_text}</div>' if footer_text else ''
        subtitle_html = f'<div class="subtitle">{menu_subtitle}</div>' if menu_subtitle else ''

        bg_css_rule = f"background-image: url(data:image/png;base64,{bg_base64}); background-size: cover;" if bg_base64 else bg_color_css

        menu_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 130mm 240mm;
                margin: 12mm 10mm;
                {bg_css_rule}
            }}
            * {{ box-sizing: border-box; }}
            body, html {{
                height: 100%;
                margin: 0;
                padding: 0;
                font-family: 'Arial', sans-serif;
                color: {text_color_css};
            }}
            .menu-container {{
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                height: 100%;
                {border_style_css}
                padding: 15px;
            }}
            .header h1 {{
                font-size: 20pt;
                margin: 0;
                color: {text_color_css};
                text-align: {align_css};
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            .subtitle {{
                font-size: 10pt;
                text-align: {align_css};
                color: {desc_color_css};
                margin-top: 4px;
                letter-spacing: 0.5px;
            }}
            .drinks-list {{
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                flex-grow: 1;
                margin: 15px 0;
            }}
            .menu-item {{ width: 100%; }}
            .item-header {{ display: table; width: 100%; }}
            .item-name {{
                display: table-cell;
                font-size: 11.5pt;
                font-weight: bold;
                white-space: nowrap;
            }}
            .item-line {{
                display: table-cell;
                width: 100%;
                border-bottom: 1px dotted {line_color_css};
                vertical-align: bottom;
            }}
            .item-price {{
                display: table-cell;
                font-size: 11.5pt;
                font-weight: bold;
                padding-right: 5px;
            }}
            .item-desc {{
                font-size: 9pt;
                color: {desc_color_css};
                margin-top: 3px;
                line-height: 1.3;
            }}
            .footer-section {{
                text-align: center;
                margin-top: auto;
            }}
            .footer-note {{
                font-size: 8pt;
                color: {desc_color_css};
                margin-bottom: 5px;
            }}
            .logo-container {{
                background: transparent !important;
                background-color: transparent !important;
            }}
            .logo {{
                max-height: 30mm;
                max-width: 75mm;
                object-fit: contain;
                background: transparent !important;
                border: none !important;
            }}
        </style>
        </head>
        <body>
            <div class="menu-container">
                <div class="header">
                    <h1>{menu_title}</h1>
                    {subtitle_html}
                </div>
                <div class="drinks-list">{menu_items_html}</div>
                <div class="footer-section">
                    {footer_note_html}
                    {logo_html}
                </div>
            </div>
        </body>
        </html>
        """

        cards_html = ""
        for item in selected_drinks_data:
            card_path, ext = find_card_file_unbeatable(item['OriginalName'])
            
            if not card_path:
                card_path, ext = find_card_file_unbeatable(item['Name'])

            if card_path and os.path.exists(card_path):
                with open(card_path, "rb") as card_file:
                    card_b64 = base64.b64encode(card_file.read()).decode("utf-8")
                
                mime_type = "application/pdf" if ext == '.pdf' else "image/png"
                
                if mime_type.startswith("image"):
                    cards_html += f"""
                    <div class="card-wrapper">
                        <img src="data:{mime_type};base64,{card_b64}" class="card-img">
                    </div>
                    """
                else:
                    cards_html += f"""
                    <div class="card-wrapper">
                        <embed src="data:{mime_type};base64,{card_b64}" type="application/pdf" class="card-img">
                    </div>
                    """
            else:
                cards_html += f"""
                <div class="card-wrapper missing-card">
                    <h3>{item['Name']}</h3>
                    <p style="color:red; font-size:12pt;">
                        שגיאה: לא נמצא קובץ גרפיקה עבור "{item['OriginalName']}" באף תיקייה בפרויקט!
                    </p>
                </div>
                """

        instructions_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 0;
            }}
            * {{ box-sizing: border-box; }}
            html, body {{
                margin: 0;
                padding: 0;
                background-color: #ffffff;
            }}
            .card-wrapper {{
                width: 210mm;
                height: 98mm;
                overflow: hidden;
                display: block;
                border-bottom: 1px dashed #999999;
                page-break-inside: avoid;
                margin: 0;
                padding: 0;
            }}
            .card-wrapper:nth-child(3n) {{
                border-bottom: none;
                page-break-after: always;
            }}
            .card-img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                border: none;
                display: block;
            }}
            .missing-card {{
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-family: Arial, sans-serif;
                border: 2px dashed red;
            }}
        </style>
        </head>
        <body>
            {cards_html}
        </body>
        </html>
        """

        HTML(string=menu_html).write_pdf("temp_menu.pdf")
        HTML(string=instructions_html).write_pdf("temp_instructions.pdf")

        st.success("🎉 המסמכים הופקו בהצלחה!")

        with open("temp_menu.pdf", "rb") as f_menu:
            st.download_button("📥 הורד תפריט מוכן (130x240 מ\"מ)", data=f_menu, file_name="menu.pdf", mime="application/pdf", use_container_width=True)

        with open("temp_instructions.pdf", "rb") as f_inst:
            st.download_button("📥 הורד כרטיסיות ברמן מוכנות (A4)", data=f_inst, file_name="serving_cards.pdf", mime="application/pdf", use_container_width=True)
