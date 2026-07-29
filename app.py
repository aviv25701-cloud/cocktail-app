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

st.set_page_config(page_title="מחולל תפריטים דינמי v13.0 Clean BG", layout="centered", page_icon="🍹")

st.title("🍹 מחולל תפריטים והצעות הגשה")
st.write("מערכת חכמה לסוכני שטח – התאמה אישית, טיפוגרפיה מתקדמת, רקעים נקיים וייצוא PDF.")

# ==============================================================================
# 🔗 קישור קבוע ומובנה לגוגל שיטס של העסק
# ==============================================================================
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1i0k5wIIgleWMY8LyAJVwrfXywnNP2kKv4WjcNCIvyBE/edit?usp=sharing"

# --- הגדרת מנוע Gemini API ---
gemini_key = st.secrets.get("GEMINI_API_KEY", None)
if gemini_key:
    genai.configure(api_key=gemini_key)

def get_csv_url(url):
    try:
        if "/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    except Exception:
        pass
    return None

csv_url = get_csv_url(DEFAULT_GSHEET_URL)

@st.cache_data(ttl=10)
def load_data(url):
    if url:
        try:
            response = requests.get(url, timeout=8)
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

# --- פונקציה חכמה לכפיית רקע נקי, חלק וללא אובייקטים ---
def build_guarded_clean_prompt(text):
    if not text:
        base_desc = "dark luxury marble texture"
    else:
        # מילון תרגום מהיר למילות מפתח
        dictionary = {
            "שיש": "marble texture",
            "עץ": "rustic wood texture",
            "כהה": "dark dark background",
            "בהיר": "light clean background",
            "זהב": "subtle gold veins",
            "יוקרתי": "luxurious background",
            "בטון": "smooth concrete texture",
            "פשתן": "linen paper texture",
            "שחור": "solid black texture",
            "חלק": "smooth plain background"
        }
        
        words = str(text).split()
        translated = []
        for w in words:
            clean_w = re.sub(r'[^\w\s]', '', w)
            if clean_w in dictionary:
                translated.append(dictionary[clean_w])
            elif re.match(r'^[a-zA-Z0-9\s,-]+$', w):
                translated.append(w)
                
        base_desc = " ".join(translated) if translated else "dark elegant texture"
        
    # הנחיה קשיחה למנוע התמונות לקבלת רקע חלק ונקי 100%
    strict_clean_suffix = "minimalist plain surface texture, subtle smooth background, full bleed, no objects, no glasses, no cups, no frames, no borders, no chalkboards, no text, no drawings, no clutter"
    return f"{base_desc}, {strict_clean_suffix}"

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

# --- פונקציית עזר לפנייה מהירה ל-Gemini ---
def safe_gemini_generate(prompt_contents):
    candidate_models = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
    for m_name in candidate_models:
        try:
            model = genai.GenerativeModel(m_name)
            res = model.generate_content(prompt_contents)
            if res and res.text:
                return res.text
        except Exception:
            continue
    return None

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
        "🎨 עיצוב חכם ב-AI (רקע חלק ונקי / תמונת רפרנס / דיוק בצ'אט)",
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

if bg_style == "🎨 עיצוב חכם ב-AI (רקע חלק ונקי / תמונת רפרנס / דיוק בצ'אט)":
    st.info("🤖 **מעצב ה-AI מוכן!** המערכת תייצר עבורך רקע חלק, נקי ומקצועי ללא קשקושים או אובייקטים מסיחים.")
    
    col_prompt, col_ref = st.columns([2, 1])
    with col_prompt:
        ai_prompt = st.text_area(
            "תאר את הקונספט או האווירה:", 
            placeholder="למשל: מרקם שיש שחור חלק עם נגיעות זהב עדינות..."
        )
    with col_ref:
        ref_image_file = st.file_uploader("📷 תמונת רפרנס (רשות):", type=["png", "jpg", "jpeg"])

    if st.button("🪄 הפיקו עיצוב חלק ב-AI", use_container_width=True):
        if not ai_prompt and not ref_image_file:
            st.warning("אנא הקלד תיאור קצר או העלה תמונת רפרנס.")
        else:
            with st.spinner("✨ מנוע ה-AI מייצר רקע חלק ונקי..."):
                ai_config = None
                
                if gemini_key:
                    system_instructions = """
                    Graphic designer for high-end cocktail menus.
                    CRITICAL: Generate a FLAT, CLEAN, MINIMALIST background texture ONLY.
                    NO glasses, NO bottles, NO frames, NO center objects, NO chalkboards, NO text.
                    
                    Return ONLY a JSON object:
                    {"bg_color": "#...", "text_color": "#...", "border_color": "#...", "line_color": "#...", "desc_color": "#...", "image_prompt": "English prompt for clean flat background texture"}
                    """
                    prompt_contents = [f"{system_instructions}\nUser request: {ai_prompt}"]
                    if ref_image_file:
                        prompt_contents.append(Image.open(ref_image_file))
                    
                    res_text = safe_gemini_generate(prompt_contents)
                    if res_text:
                        start_pos = res_text.find("{")
                        end_pos = res_text.rfind("}")
                        if start_pos != -1 and end_pos != -1:
                            try:
                                ai_config = json.loads(res_text[start_pos:end_pos+1])
                            except Exception:
                                ai_config = None

                if not ai_config:
                    ai_config = {
                        "bg_color": "#121212",
                        "text_color": "#ffffff",
                        "border_color": "#c5a059",
                        "line_color": "#c5a059",
                        "desc_color": "#dddddd",
                        "image_prompt": ai_prompt or "dark marble texture"
                    }

                st.session_state['ai_bg_color'] = ai_config.get('bg_color', '#121212')
                st.session_state['ai_text_color'] = ai_config.get('text_color', '#ffffff')
                st.session_state['ai_border_color'] = ai_config.get('border_color', '#ffffff')
                st.session_state['ai_line_color'] = ai_config.get('line_color', '#888888')
                st.session_state['ai_desc_color'] = ai_config.get('desc_color', '#cccccc')
                st.session_state['ai_image_prompt'] = ai_config.get('image_prompt', 'dark marble texture')
                
                # הפעלת מנוע החסימה לרקע חלק ונקי
                guarded_prompt = build_guarded_clean_prompt(st.session_state['ai_image_prompt'])
                prompt_encoded = urllib.parse.quote(guarded_prompt)
                seed = random.randint(1, 999999)
                pollinations_url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=650&height=1200&seed={seed}&nologo=true"
                
                try:
                    img_res = requests.get(pollinations_url, timeout=7)
                    if img_res.status_code == 200:
                        st.session_state['ai_bg_b64'] = base64.b64encode(img_res.content).decode("utf-8")
                except Exception:
                    st.session_state['ai_bg_b64'] = ""
                st.rerun()

    # --- מנגנון צ'אט עם כפיית רקע חלק ונקי ---
    if 'ai_bg_color' in st.session_state:
        st.markdown("---")
        st.markdown("### 💬 לדייק ולשפר את העיצוב הקיים בצ'אט")
        refine_input = st.text_input(
            "רוצה לשנות משהו בעיצוב הנוכחי? הקלד הנחיות לדיוק:", 
            placeholder="למשל: תעשה את הרקע כהה יותר, תשנה למרקם עץ..."
        )
        
        if st.button("✏️ עדכן עיצוב לפי ההנחיות שלי", use_container_width=True):
            if not refine_input:
                st.warning("אנא הקלד הנחיה לשיפור העיצוב.")
            else:
                with st.spinner("🔄 מעדכן לרקע חלק ונקי..."):
                    current_prompt = st.session_state.get('ai_image_prompt', 'dark marble background')
                    
                    translation_prompt = f"""
                    Convert Hebrew design tweak into English prompt for FLAT CLEAN BACKGROUND TEXTURE ONLY.
                    Current prompt: "{current_prompt}"
                    Hebrew tweak: "{refine_input}"
                    Return ONLY JSON: {{"updated_prompt": "english clean texture prompt"}}
                    """
                    
                    res_text = safe_gemini_generate([translation_prompt])
                    updated_prompt_en = f"{current_prompt} {refine_input}"
                    
                    if res_text:
                        start_pos = res_text.find("{")
                        end_pos = res_text.rfind("}")
                        if start_pos != -1 and end_pos != -1:
                            try:
                                parsed = json.loads(res_text[start_pos:end_pos+1])
                                updated_prompt_en = parsed.get("updated_prompt", updated_prompt_en)
                            except Exception:
                                pass

                    st.session_state['ai_image_prompt'] = updated_prompt_en
                    
                    # הפעלת מנוע החסימה לרקע חלק
                    guarded_prompt = build_guarded_clean_prompt(updated_prompt_en)
                    prompt_encoded = urllib.parse.quote(guarded_prompt)
                    seed = random.randint(1, 999999)
                    pollinations_url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=650&height=1200&seed={seed}&nologo=true"
                    
                    try:
                        img_res = requests.get(pollinations_url, timeout=7)
                        if img_res.status_code == 200:
                            st.session_state['ai_bg_b64'] = base64.b64encode(img_res.content).decode("utf-8")
                    except Exception:
                        pass
                        
                    st.rerun()

        bg_color_css = f"background-color: {st.session_state['ai_bg_color']};"
        text_color_css = st.session_state['ai_text_color']
        border_color_css = st.session_state['ai_border_color']
        line_color_css = st.session_state['ai_line_color']
        desc_color_css = st.session_state['ai_desc_color']
        
        st.markdown("#### 🎨 תצוגה מקדימה של פלטת הצבעים והרקע החלק:")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.color_picker("צבע רקע:", st.session_state['ai_bg_color'], disabled=True, key="pv_bg")
        with c2:
            st.color_picker("צבע טקסט:", st.session_state['ai_text_color'], disabled=True, key="pv_txt")
        with c3:
            st.color_picker("צבע מסגרת:", st.session_state['ai_border_color'], disabled=True, key="pv_brd")

        if 'ai_bg_b64' in st.session_state and st.session_state['ai_bg_b64']:
            bg_base64 = st.session_state['ai_bg_b64']
            st.image(
                base64.b64decode(st.session_state['ai_bg_b64']), 
                caption="🖼️ תמונת הרקע החלקה והנקייה שנוצרה לתפריט", 
                use_container_width=True
            )

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

# ==============================================================================
# 🔤 3. הגדרות טיפוגרפיה, גודל פונט, מרווחים וצבעים
# ==============================================================================
st.markdown("---")
st.subheader("3. עיצוב טקסט, פונטים ומרווחים (שליטת סוכן מלאה)")

with st.expander("🛠️ לחץ כאן לשינוי פונט, גודל גופנים, מרווחים וצבעים", expanded=True):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        font_family = st.selectbox(
            "סוג גופן (Font Family):", 
            ["Heebo", "Assistant", "Rubik", "Varela Round", "Frank Ruhl Libre", "Arial"]
        )
    with col_f2:
        custom_text_color = st.color_picker("דריסת צבע טקסט (רשות):", value=text_color_css)

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        title_font_size = st.slider("גודל כותרת ראשית (pt):", min_value=14, max_value=32, value=20)
    with col_s2:
        item_font_size = st.slider("גודל שם משקה (pt):", min_value=9, max_value=20, value=12)
    with col_s3:
        desc_font_size = st.slider("גודל תיאור מרכיבים (pt):", min_value=7, max_value=14, value=9)

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        line_height_val = st.slider("מרווח בין שורות (Line Height):", min_value=1.0, max_value=2.2, value=1.3, step=0.1)
    with col_m2:
        item_spacing_val = st.slider("מרווח אנכי בין מוצרים (px):", min_value=2, max_value=25, value=8)

final_text_color = custom_text_color

st.markdown("---")
st.subheader("4. לוגו והערות בתחתית (Footer)")

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
st.subheader("5. בחירת מוצרים, תמחור ועריכה בזמן אמת")

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
            raw_price = str(item['Price']).strip()
            if raw_price:
                price_display = raw_price if raw_price.startswith("₪") else f"₪{raw_price}"
            else:
                price_display = ""

            menu_items_html += f"""
            <div class="menu-item">
                <div class="item-header">
                    <span class="item-name">{item['Name']}</span>
                    <span class="item-line"></span>
                    <span class="item-price">{price_display}</span>
                </div>
                <div class="item-desc">{item['Ingredients']}</div>
            </div>
            """

        logo_html = f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" class="logo"></div>' if logo_base64 else ''
        footer_note_html = f'<div class="footer-note">{footer_text}</div>' if footer_text else ''
        subtitle_html = f'<div class="subtitle">{menu_subtitle}</div>' if menu_subtitle else ''

        bg_css_rule = f"background-image: url(data:image/png;base64,{bg_base64}); background-size: cover; background-position: center;" if bg_base64 else bg_color_css

        menu_html = f"""
        <!DOCTYPE html>
        <html lang="he" dir="rtl">
        <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&family=Frank+Ruhl+Libre:wght@400;700&family=Heebo:wght@400;700&family=Rubik:wght@400;700&family=Varela+Round&display=swap');
            
            @page {{
                size: 130mm 240mm;
                margin: 0;
            }}
            * {{ box-sizing: border-box; }}
            html, body {{
                width: 130mm;
                height: 240mm;
                margin: 0;
                padding: 0;
                {bg_css_rule}
                font-family: '{font_family}', sans-serif;
                color: {final_text_color};
            }}
            .menu-container {{
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                width: 100%;
                height: 100%;
                padding: 15mm 12mm;
                {border_style_css}
            }}
            .header {{
                text-align: {align_css};
                margin-bottom: 10px;
            }}
            .header h1 {{
                font-size: {title_font_size}pt;
                margin: 0;
                color: {final_text_color};
                letter-spacing: 1px;
                text-transform: uppercase;
                line-height: {line_height_val};
            }}
            .subtitle {{
                font-size: 10pt;
                color: {desc_color_css};
                margin-top: 5px;
                letter-spacing: 0.5px;
            }}
            .drinks-list {{
                display: flex;
                flex-direction: column;
                justify-content: space-around;
                flex-grow: 1;
                margin: 10px 0;
            }}
            .menu-item {{ 
                width: 100%; 
                margin-bottom: {item_spacing_val}px;
            }}
            .item-header {{ 
                display: table; 
                width: 100%; 
            }}
            .item-name {{
                display: table-cell;
                font-size: {item_font_size}pt;
                font-weight: bold;
                white-space: nowrap;
            }}
            .item-line {{
                display: table-cell;
                width: 100%;
            }}
            .item-price {{
                display: table-cell;
                font-size: {item_font_size}pt;
                font-weight: bold;
                padding-right: 8px;
                white-space: nowrap;
                text-align: left;
            }}
            .item-desc {{
                font-size: {desc_font_size}pt;
                color: {desc_color_css};
                margin-top: 3px;
                line-height: {line_height_val};
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
            }}
            .logo {{
                max-height: 25mm;
                max-width: 70mm;
                object-fit: contain;
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
