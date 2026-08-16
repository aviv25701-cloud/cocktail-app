import streamlit as st
import pandas as pd
from weasyprint import HTML
import base64
import os
from PIL import Image
import io
import requests
import re

st.set_page_config(page_title="מחולל תפריטים מהיר לסוכנים", layout="centered", page_icon="🍹")

# --- סגנון ממשק נקי ופשוט ---
st.markdown("""
<style>
    .stCheckbox { font-size: 16px; font-weight: bold; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
    .stButton>button { border-radius: 8px; font-weight: bold; font-size: 18px; }
</style>
""", unsafe_allow_html=True)

st.title("🍹 מחולל תפריטים מהיר")
st.caption("בחירת טמפלייט ⬅️ בחירת מוצרים ⬅️ הורדת תפריט וכרטיסיות ברמן ב-PDF.")

# ==============================================================================
# 🔗 חיבור לגוגל שיטס
# ==============================================================================
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1i0k5wIIgleWMY8LyAJVwrfXywnNP2kKv4WjcNCIvyBE/edit?usp=sharing"

def get_csv_url(url):
    try:
        if "/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    except Exception:
        pass
    return None

@st.cache_data(ttl=5)
def load_data(url):
    if url:
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = df.columns.str.strip()
            df = df.fillna('')
            return df
        except Exception as e:
            st.error(f"שגיאה בחיבור לגוגל שיטס: {e}")
    return None

df_cocktails = load_data(get_csv_url(DEFAULT_GSHEET_URL))

if df_cocktails is None or df_cocktails.empty:
    st.error("⚠️ לא ניתן לטעון את מאגר הקוקטיילים. אנא ודא שקישור הגוגל שיטס תקין וציבורי.")
    st.stop()

# --- פונקציה חכמה לטעינת קבצי הרקע שהעלית (תומכת גם בסיומת .png.jpg) ---
def get_template_bg_base64(template_keyword):
    for root, dirs, files in os.walk("."):
        if "/." in root or root.startswith("./."):
            continue
        for filename in files:
            clean_name = filename.lower()
            if template_keyword.lower() in clean_name:
                if any(clean_name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    with open(os.path.join(root, filename), "rb") as f:
                        return base64.b64encode(f.read()).decode("utf-8")
    return ""

# --- פונקציית סריקת כרטיסיות ברמן ---
def find_card_file_unbeatable(drink_name):
    valid_extensions = ['.png', '.jpg', '.jpeg', '.pdf']

    def clean_strict(s):
        name_only = os.path.splitext(str(s))[0]
        return "".join(c.lower() for c in name_only if c.isalnum())

    target_strict = clean_strict(drink_name)
    for root, dirs, files in os.walk("."):
        if "/." in root or root.startswith("./."):
            continue
        for filename in files:
            name_without_ext, ext = os.path.splitext(filename)
            ext_lower = ext.lower()
            if ext_lower in valid_extensions and clean_strict(name_without_ext) == target_strict:
                return os.path.join(root, filename), ext_lower

    def clean_lenient(s):
        s_clean = re.sub(r'(מיקסר|mixer|[-_,\(\)])', '', str(s), flags=re.IGNORECASE)
        return "".join(c.lower() for c in s_clean if c.isalnum())

    target_lenient = clean_lenient(drink_name)
    for root, dirs, files in os.walk("."):
        if "/." in root or root.startswith("./."):
            continue
        for filename in files:
            name_without_ext, ext = os.path.splitext(filename)
            ext_lower = ext.lower()
            if ext_lower in valid_extensions and clean_lenient(name_without_ext) == target_lenient:
                return os.path.join(root, filename), ext_lower

    return None, None

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

# ==============================================================================
# 📝 שלב 1: פרטי הלקוח והתפריט
# ==============================================================================
st.subheader("1. פרטי התפריט")

col_t1, col_t2 = st.columns([2, 1])
with col_t1:
    menu_title = st.text_input("כותרת התפריט:", value="COCKTAIL MENU")
with col_t2:
    uploaded_logo = st.file_uploader("לוגו בית העסק (PNG/JPG):", type=["png", "jpg", "jpeg"])

logo_base64 = ""
if uploaded_logo:
    logo_bytes = remove_white_background(uploaded_logo.read())
    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

st.markdown("---")

# ==============================================================================
# 🎨 שלב 2: בחירת טמפלייט (2 טמפלייטים קבועים בלבד)
# ==============================================================================
st.subheader("2. בחר טמפלייט לתפריט")

template_choice = st.radio(
    "בחר תבנית עיצוב:",
    ["טמפלייט 1 (מלל בהיר #f6f6f6)", "טמפלייט 2 (מלל שחור #000000)"],
    horizontal=True
)

if "טמפלייט 1" in template_choice:
    text_color = "#f6f6f6"
    desc_color = "#f6f6f6"
    bg_b64 = get_template_bg_base64("template2")
    fallback_color = "#1a1a1a"
else:  # טמפלייט 2
    text_color = "#000000"
    desc_color = "#000000"
    bg_b64 = get_template_bg_base64("template3")
    fallback_color = "#ffffff"

if bg_b64:
    bg_css_rule = f"background-image: url(data:image/jpeg;base64,{bg_b64}); background-size: 100% 100%; background-position: center; background-repeat: no-repeat;"
else:
    bg_css_rule = f"background-color: {fallback_color};"

st.caption(f"🎨 צבע המלל נקבע אוטומטית ל: `{text_color}`")

st.markdown("---")

# ==============================================================================
# 🍹 שלב 3: בחירת קוקטיילים לתפריט
# ==============================================================================
st.subheader("3. בחר קוקטיילים לתפריט")

col_search, col_filter = st.columns([2, 1])
with col_search:
    search_q = st.text_input("🔍 חיפוש משקה לפי שם:", placeholder="הקלד שם קוקטייל / מיקסר...")
with col_filter:
    cat_filter = st.selectbox("📂 סנן לפי סוג:", ["הכל", "קוקטיילים בלבד", "מיקסרים בלבד"])

col_btn1, col_btn2, _ = st.columns([1, 1, 2])
with col_btn1:
    if st.button("✅ בחר הכל", use_container_width=True):
        for idx_b in range(len(df_cocktails)):
            st.session_state[f"select_state_{idx_b}"] = True
        st.rerun()
with col_btn2:
    if st.button("❌ נקה הכל", use_container_width=True):
        for idx_b in range(len(df_cocktails)):
            st.session_state[f"select_state_{idx_b}"] = False
        st.rerun()

selected_drinks = []

for idx, row in df_cocktails.iterrows():
    drink_name = str(row.get('Name', ''))
    ingredients = str(row.get('Ingredients', ''))
    item_id = str(row.get('ID', idx))

    is_mixer = "מיקסר" in drink_name or "mixer" in drink_name.lower()
    if cat_filter == "קוקטיילים בלבד" and is_mixer:
        continue
    if cat_filter == "מיקסרים בלבד" and not is_mixer:
        continue
    if search_q and search_q.lower() not in drink_name.lower():
        continue

    state_key = f"select_state_{idx}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    is_sel = st.checkbox(f"🍹 {drink_name}", value=st.session_state[state_key], key=f"chk_{idx}_{item_id}")
    st.session_state[state_key] = is_sel
    
    if is_sel:
        col_n, col_p = st.columns([3, 1])
        with col_n:
            e_name = st.text_input("שם בתפריט:", value=drink_name, key=f"n_{idx}_{item_id}")
        with col_p:
            e_price = st.text_input("מחיר (₪):", value="45", key=f"p_{idx}_{item_id}")
        
        selected_drinks.append({
            "OriginalName": drink_name,
            "Name": e_name,
            "Price": e_price.strip(),
            "Ingredients": ingredients
        })

st.markdown("---")

# ==============================================================================
# 🚀 הפקת התפריט והורדת PDF
# ==============================================================================
if st.button("🚀 הפק תפריט וכרטיסיות ברמן (PDF)", use_container_width=True, type="primary"):
    if not selected_drinks:
        st.error("❌ אנא בחר לפחות משקה אחד!")
    else:
        num_items = len(selected_drinks)
        if num_items <= 4:
            font_title, font_item, font_desc, item_gap = "22pt", "14pt", "10pt", "18px"
        elif num_items <= 7:
            font_title, font_item, font_desc, item_gap = "19pt", "12pt", "9pt", "12px"
        else:
            font_title, font_item, font_desc, item_gap = "16pt", "10.5pt", "8pt", "6px"

        menu_items_html = ""
        for item in selected_drinks:
            price_str = f"₪{item['Price']}" if item['Price'] else ""
            menu_items_html += f"""
            <div class="menu-item">
                <div class="item-header">
                    <span class="item-name">{item['Name']}</span>
                    <span class="item-price">{price_str}</span>
                </div>
                <div class="item-desc">{item['Ingredients']}</div>
            </div>
            """

        logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo">' if logo_base64 else ''

        menu_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;700&display=swap');
            @page {{ size: 130mm 240mm; margin: 0; }}
            * {{ box-sizing: border-box; }}
            html, body {{
                width: 130mm; height: 240mm; margin: 0; padding: 0;
                {bg_css_rule}
                font-family: 'Heebo', sans-serif;
                color: {text_color};
            }}
            .menu-container {{
                display: flex; flex-direction: column; justify-content: space-between;
                width: 100%; height: 100%; padding: 14mm 10mm;
            }}
            .header {{
                text-align: center;
                margin-bottom: 25px;
            }}
            .header h1 {{
                font-size: {font_title};
                margin: 0;
                color: {text_color};
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            .drinks-list {{
                display: flex; flex-direction: column; justify-content: space-around; flex-grow: 1;
            }}
            .menu-item {{ margin-bottom: {item_gap}; }}
            .item-header {{ display: flex; justify-content: space-between; font-weight: bold; font-size: {font_item}; color: {text_color}; }}
            .item-desc {{ font-size: {font_desc}; color: {desc_color}; margin-top: 2px; line-height: 1.2; }}
            .footer {{ text-align: center; margin-top: auto; }}
            .logo {{ max-height: 22mm; max-width: 60mm; object-fit: contain; }}
        </style>
        </head>
        <body>
            <div class="menu-container">
                <div class="header"><h1>{menu_title}</h1></div>
                <div class="drinks-list">{menu_items_html}</div>
                <div class="footer">{logo_html}</div>
            </div>
        </body>
        </html>
        """

        cards_html = ""
        for item in selected_drinks:
            card_path, ext = find_card_file_unbeatable(item['OriginalName'])
            if not card_path:
                card_path, ext = find_card_file_unbeatable(item['Name'])

            if card_path and os.path.exists(card_path):
                with open(card_path, "rb") as card_file:
                    card_b64 = base64.b64encode(card_file.read()).decode("utf-8")
                mime_type = "application/pdf" if ext == '.pdf' else "image/png"
                cards_html += f'<div class="card-wrapper"><img src="data:{mime_type};base64,{card_b64}" class="card-img"></div>'
            else:
                cards_html += f'<div class="card-wrapper missing"><h3>{item["Name"]}</h3><p>קובץ כרטיסייה לא נמצא</p></div>'

        instructions_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0; }}
            body {{ margin: 0; background: white; }}
            .card-wrapper {{ width: 210mm; height: 98mm; border-bottom: 1px dashed #ccc; page-break-inside: avoid; }}
            .card-wrapper:nth-child(3n) {{ border-bottom: none; page-break-after: always; }}
            .card-img {{ width: 100%; height: 100%; object-fit: cover; }}
            .missing {{ display: flex; flex-direction: column; align-items: center; justify-content: center; color: red; }}
        </style>
        </head>
        <body>{cards_html}</body>
        </html>
        """

        HTML(string=menu_html).write_pdf("temp_menu.pdf")
        HTML(string=instructions_html).write_pdf("temp_instructions.pdf")

        st.success("🎉 התפריט והכרטיסיות מוכנים!")
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            with open("temp_menu.pdf", "rb") as f_m:
                st.download_button("📥 הורד תפריט (PDF)", data=f_m, file_name="menu.pdf", mime="application/pdf", use_container_width=True)
        with c_d2:
            with open("temp_instructions.pdf", "rb") as f_i:
                st.download_button("📥 הורד כרטיסיות ברמן (A4)", data=f_i, file_name="serving_cards.pdf", mime="application/pdf", use_container_width=True)
