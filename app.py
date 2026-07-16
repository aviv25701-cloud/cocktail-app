import streamlit as st
import pandas as pd
from weasyprint import HTML
import base64
import os

st.set_page_config(page_title="מחולל תפריטים דינמי", layout="centered", page_icon="🍹")

st.title("🍹 מחולל תפריטים והצעות הגשה")
st.write("אפליקציה חכמה לסוכני שטח – הפקת תפריטים וכרטיסיות ברמן ב-PDF בשניות.")

st.sidebar.header("⚙️ הגדרות מאגר הנתונים")

# כתובת ברירת מחדל (החלף בקישור שלך בשטח)
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

@st.cache_data(ttl=60)
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

st.subheader("1. פרטי העסק והעיצוב")

col_title, col_align = st.columns([2, 1])
with col_title:
    menu_title = st.text_input("כותרת התפריט (עברית/אנגלית):", value="COCKTAIL MENU")
with col_align:
    text_align = st.selectbox("כיוון כותרת:", options=["מרכז", "שמאל (אנגלית)", "ימין (עברית)"])

align_css = "center" if "מרכז" in text_align else "left" if "שמאל" in text_align else "right"

uploaded_logo = st.file_uploader("העלה לוגו של בית העסק (PNG / JPG):", type=["png", "jpg", "jpeg"])

logo_base64 = ""
if uploaded_logo:
    logo_bytes = uploaded_logo.read()
    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

st.markdown("---")
st.subheader("2. בחירת מוצרים ותמחור")

selected_rows = []
drink_prices = {}

for idx, row in df_cocktails.iterrows():
    col_check, col_price = st.columns([3, 1])
    with col_check:
        is_selected = st.checkbox(f"**{row['Name']}** — {row['Ingredients']}", key=f"select_{row['ID']}")
    with col_price:
        price = st.text_input("מחיר (₪)", value="45", key=f"price_{row['ID']}", disabled=not is_selected)
    
    if is_selected:
        selected_rows.append(row)
        drink_prices[row['ID']] = price

st.markdown("---")

if st.button("🚀 הפק תפריט וכרטיסיות ברמן", use_container_width=True):
    if not selected_rows:
        st.error("❌ אנא בחר לפחות קוקטייל אחד כדי להפיק קבצים!")
    else:
        # א. יצירת תפריט דינמי (130x240 מ"מ)
        menu_items_html = ""
        for row in selected_rows:
            price = drink_prices[row['ID']]
            menu_items_html += f"""
            <div class="menu-item">
                <div class="item-header">
                    <span class="item-name">{row['Name']}</span>
                    <span class="item-line"></span>
                    <span class="item-price">₪{price}</span>
                </div>
                <div class="item-desc">{row['Ingredients']}</div>
            </div>
            """

        logo_html = f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" class="logo"></div>' if logo_base64 else ''

        menu_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 130mm 240mm;
                margin: 15mm 10mm;
                background-color: #0b0c10;
            }}
            * {{ box-sizing: border-box; }}
            body, html {{
                height: 100%;
                margin: 0;
                padding: 0;
                font-family: 'Arial', sans-serif;
                color: #c5c6c7;
            }}
            .menu-container {{
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                height: 100%;
                border: 2px solid #66fcf1;
                padding: 15px;
            }}
            .header h1 {{
                font-size: 20pt;
                margin: 0;
                color: #66fcf1;
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
            .menu-item {{
                width: 100%;
            }}
            .item-header {{
                display: table;
                width: 100%;
            }}
            .item-name {{
                display: table-cell;
                font-size: 12pt;
                font-weight: bold;
                color: #ffffff;
                white-space: nowrap;
            }}
            .item-line {{
                display: table-cell;
                width: 100%;
                border-bottom: 1px dotted #45f3ff;
                vertical-align: bottom;
            }}
            .item-price {{
                display: table-cell;
                font-size: 12pt;
                font-weight: bold;
                color: #66fcf1;
                padding-right: 5px;
            }}
            .item-desc {{
                font-size: 9.5pt;
                color: #85929e;
                margin-top: 4px;
                line-height: 1.3;
            }}
            .logo-container {{
                text-align: center;
                margin-top: auto;
            }}
            .logo {{
                max-height: 35mm;
                max-width: 80mm;
                object-fit: contain;
            }}
        </style>
        </head>
        <body>
            <div class="menu-container">
                <div class="header">
                    <h1>{menu_title}</h1>
                </div>
                <div class="drinks-list">
                    {menu_items_html}
                </div>
                {logo_html}
            </div>
        </body>
        </html>
        """

        # ב. יצירת כרטיסיות ברמן (A4 - 3 בדף) באמצעות הלבשת קבצי ה-PDF המקוריים
        cards_html = ""
        for row in selected_rows:
            # חיפוש הקובץ לפי עמודת ה-Name ובסיומת .pdf
            card_filename = f"{row['Name']}.pdf"
            card_path = os.path.join("cards", card_filename)
            
            if os.path.exists(card_path):
                # קריאת קובץ ה-PDF של הכרטיסייה והמרתו ל-Base64 כדי להציגו ישירות בדפדפן
                with open(card_path, "rb") as card_file:
                    card_b64 = base64.b64encode(card_file.read()).decode("utf-8")
                card_src = f"data:application/pdf;base64,{card_b64}"
            else:
                card_src = None

            if card_src:
                cards_html += f"""
                <div class="card-wrapper">
                    <embed src="{card_src}" type="application/pdf" class="card-pdf-embed">
                </div>
                """
            else:
                cards_html += f"""
                <div class="card-wrapper missing-card">
                    <h3>{row['Name']}</h3>
                    <p style="color:red;">שגיאה: קובץ ה-PDF בשם "{card_filename}" חסר בתיקיית cards!</p>
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
            body {{
                margin: 0;
                padding: 0;
                background-color: #ffffff;
            }}
            .card-wrapper {{
                width: 210mm;
                height: 99mm;
                overflow: hidden;
                display: block;
                border-bottom: 1px dashed #999999;
                page-break-inside: avoid;
            }}
            .card-wrapper:nth-child(3n) {{
                border-bottom: none;
            }}
            .card-pdf-embed {{
                width: 100%;
                height: 100%;
                border: none;
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
