import streamlit as st
import pandas as pd
from weasyprint import HTML
import base64
import os

st.set_page_config(page_title="מחולל תפריטים דינמי", layout="centered", page_icon="🍹")

st.title("🍹 מחולל תפריטים והצעות הגשה")
st.write("מערכת חכמה לסוכני שטח – הפקת תפריטים וכרטיסיות ברמן ב-PDF בשניות.")

# --- הגדרות מערכת בסרגל הצד ---
st.sidebar.header("⚙️ הגדרות מאגר הנתונים")

default_sheet = "https://docs.google.com/spreadsheets/d/1YourActualSpreadsheetIdHere/edit?usp=sharing"
gsheet_url = st.sidebar.text_input("קישור לגוגל שיטס שלך:", value=default_sheet)

def get_csv_url(url):
    try:
        if "/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    except Exception:
        pass
    return None

csv_url = get_csv_url(gsheet_url)

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
    st.warning("⚠️ אנא הזן קישור גוגל שיטס תקין וציבורי בתפריט הצד כדי להתחיל.")
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

# --- 1. פרטי העסק והעיצוב ---
st.subheader("1. פרטי העסק והעיצוב")

col_title, col_align = st.columns([2, 1])
with col_title:
    menu_title = st.text_input("כותרת התפריט (עברית/אנגלית):", value="COCKTAIL MENU")
with col_align:
    text_align = st.selectbox("כיוון כותרת:", options=["מרכז", "שמאל (אנגלית)", "ימין (עברית)"])

align_css = "center" if "מרכז" in text_align else "left" if "שמאל" in text_align else "right"

st.write("**בחירת עיצוב רקע לתפריט (130x240 מ\"מ):**")
bg_style = st.selectbox("בחר סגנון עיצוב:", ["יוקרתי כהה", "מינימליסטי בהיר", "רקע תמונה מותאם אישית (העלאת קובץ)"])

bg_base64 = ""
bg_color_css = ""
text_color_css = "#ffffff"
border_color_css = "#66fcf1"
line_color_css = "#45f3ff"
desc_color_css = "#85929e"

if bg_style == "יוקרתי כהה":
    bg_color_css = "background-color: #0b0c10;"
    text_color_css = "#ffffff"
    border_color_css = "#66fcf1"
    line_color_css = "#45f3ff"
    desc_color_css = "#85929e"
elif bg_style == "מינימליסטי בהיר":
    bg_color_css = "background-color: #f8f9fa;"
    text_color_css = "#2b2b2b"
    border_color_css = "#d4a373"
    line_color_css = "#d4a373"
    desc_color_css = "#666666"
else:
    uploaded_bg = st.file_uploader("העלה קובץ תמונת רקע (מומלץ במידות 130x240 מ\"מ):", type=["png", "jpg", "jpeg"], key="bg_uploader")
    if uploaded_bg:
        bg_base64 = base64.b64encode(uploaded_bg.read()).decode("utf-8")
    text_color_css = st.color_picker("בחר צבע גופן לתפריט:", "#ffffff")
    border_color_css = st.color_picker("בחר צבע למסגרת התפריט:", "#ffffff")
    line_color_css = border_color_css
    desc_color_css = text_color_css

uploaded_logo = st.file_uploader("העלה לוגו של בית העסק (PNG / JPG):", type=["png", "jpg", "jpeg"], key="logo_uploader")
logo_base64 = ""
if uploaded_logo:
    logo_bytes = uploaded_logo.read()
    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

st.markdown("---")
st.subheader("2. בחירת מוצרים, תמחור ועריכה בזמן אמת")

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
        # א. יצירת תפריט דינמי (130x240 מ"מ)
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

        bg_css_rule = f"background-image: url(data:image/png;base64,{bg_base64}); background-size: cover;" if bg_base64 else bg_color_css

        menu_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 130mm 240mm;
                margin: 15mm 10mm;
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
                border: 2px solid {border_color_css};
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
            .drinks-list {{
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                flex-grow: 1;
                margin: 20px 0;
            }}
            .menu-item {{ width: 100%; }}
            .item-header {{ display: table; width: 100%; }}
            .item-name {{
                display: table-cell;
                font-size: 12pt;
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
                font-size: 12pt;
                font-weight: bold;
                padding-right: 5px;
            }}
            .item-desc {{
                font-size: 9.5pt;
                color: {desc_color_css};
                margin-top: 4px;
                line-height: 1.3;
            }}
            .logo-container {{ text-align: center; margin-top: auto; }}
            .logo {{ max-height: 35mm; max-width: 80mm; object-fit: contain; }}
        </style>
        </head>
        <body>
            <div class="menu-container">
                <div class="header"><h1>{menu_title}</h1></div>
                <div class="drinks-list">{menu_items_html}</div>
                {logo_html}
            </div>
        </body>
        </html>
        """

        # ב. יצירת כרטיסיות ברמן (A4 - 3 בדף בדיוק)
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
                height: 98mm; /* מובטח להיכנס 3 פעמים בתוך 297 מ"מ של דף A4 */
                overflow: hidden;
                display: block;
                border-bottom: 1px dashed #999999;
                page-break-inside: avoid;
                margin: 0;
                padding: 0;
            }}
            .card-wrapper:nth-child(3n) {{
                border-bottom: none;
                page-break-after: always; /* מעבר דף אוטומטי אך ורק לאחר כל כרטיסייה שלישית */
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
