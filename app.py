import streamlit as st
import time
from google import genai
from PIL import Image
import json
import subprocess
import os
import re

# ==========================================
# 🚨 1. ตั้งค่าหน้าเว็บหลัก & UI/UX ระดับโปร
# ==========================================
try:
    logo_img = Image.open("logo.png") 
except FileNotFoundError:
    logo_img = "🤖" 

st.set_page_config(page_title="NextGen Ai STORE | Super App", page_icon=logo_img, layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; color: #1E88E5; font-weight: 700; margin-bottom: 0px;}
    .sub-header { font-size: 1.1rem; color: #757575; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 5px 5px 0px 0px; padding: 10px 20px; background-color: #f0f2f6; }
    .stTabs [aria-selected="true"] { background-color: #1E88E5; color: white; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔑 2. ระบบ API 
# ==========================================
api_keys_list = []
if "GEMINI_API_KEYS" in st.secrets: api_keys_list = st.secrets["GEMINI_API_KEYS"]
elif "GEMINI_API_KEY" in st.secrets: api_keys_list = [st.secrets["GEMINI_API_KEY"]]

if 'current_key_idx' not in st.session_state: st.session_state.current_key_idx = 0
if 'key_status' not in st.session_state: 
    st.session_state.key_status = {i: "⏳ สแตนด์บาย" for i in range(len(api_keys_list))}
    if api_keys_list: st.session_state.key_status[0] = "🟢 กำลังใช้งาน"

def smart_generate(prompt_contents):
    if not api_keys_list: raise Exception("ไม่พบ API Key กรุณาตั้งค่าก่อน")
    start_idx = st.session_state.current_key_idx
    total_keys = len(api_keys_list)
    for i in range(total_keys):
        idx = (start_idx + i) % total_keys 
        key = api_keys_list[idx]
        try:
            temp_client = genai.Client(api_key=key.strip())
            response = temp_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_contents)
            st.session_state.current_key_idx = idx
            st.session_state.key_status[idx] = "🟢 กำลังใช้งาน"
            for j in range(total_keys):
                if j != idx and st.session_state.key_status.get(j) != "🔴 ติดลิมิต":
                    st.session_state.key_status[j] = "⏳ สแตนด์บาย"
            return response.text 
        except Exception:
            st.session_state.key_status[idx] = "🔴 ติดลิมิต"
            continue
    raise Exception(f"API Key ติดลิมิตหมดแล้วครับ! กรุณารอ 1 นาที")

def render_custom_select(label, options, key):
    opt_list = options + ["พิมพ์กำหนดเอง..."]
    current_val = st.session_state.get(key, options[0])
    idx = options.index(current_val) if current_val in options else len(opt_list) - 1
    selected = st.selectbox(label, opt_list, index=idx, key=f"select_{key}")
    if selected == "พิมพ์กำหนดเอง...":
        default_text = current_val if current_val not in options else ""
        custom_val = st.text_input(f"✍️ ระบุแบบกำหนดเอง:", value=default_text, key=f"custom_{key}")
        st.session_state[key] = custom_val
    else:
        st.session_state[key] = selected

# ==========================================
# ⚙️ 3. ระบบ Handoff & รันบอท
# ==========================================
@st.dialog("⚙️ ตั้งค่าและรันบอท (Handoff)")
def run_bot_dialog(scene_num, raw_text, ref_img_list, is_first, is_poster_only=False):
    st.markdown(f"### 🎬 ควบคุมการรัน {'โปสเตอร์' if is_poster_only else f'ฉากที่ {scene_num}'}")
    
    img_p = (re.search(r'Prompt สร้างภาพนิ่ง.*?:(.*?)(?=\*\*Prompt|\- 🎞️|\n\n|$)', raw_text, re.DOTALL | re.IGNORECASE) or [None, raw_text])[1].strip()
    
    final_img = st.text_area("🖼️ Prompt ภาพนิ่ง (Nano Banana 2):", value=img_p, height=100) if (is_first or is_poster_only) else ""
    
    final_vid = ""
    if not is_poster_only:
        vid_p = (re.search(r'Prompt สร้างวิดีโอ.*?:(.*?)(?=\*\*Prompt|\- 🖼️|\n\n|$)', raw_text, re.DOTALL | re.IGNORECASE) or [None, "Animate smoothly"])[1].strip()
        final_vid = st.text_area("🎞️ Prompt วิดีโอ (Veo 3.1):", value=vid_p, height=100)
    
    c1, c2 = st.columns(2)
    with c1: ratio = st.selectbox("📏 สัดส่วน:", ["9:16", "1:1", "16:9"], key="run_ratio")
    with c2: credit = st.selectbox("⚡ ความเร็ว:", ["Fast [Lower Priority]", "Fast"], key="run_credit")
    
    ref_img_path = ref_img_list[0] if ref_img_list else ""

    if st.button("🚀 ยืนยันรันบอท" if not is_poster_only else "🖼️ รันบอทสร้างโปสเตอร์", type="primary", use_container_width=True):
        payload = {
            "type": "image_only" if is_poster_only else "scene_pipeline", 
            "image_prompt": final_img, 
            "video_prompt": final_vid, 
            "credit_mode": "Lower Priority" if "Lower" in credit else "Fast", 
            "ref_image": ref_img_path, 
            "scene_num": scene_num, 
            "is_first_scene": is_first, 
            "target_ratio": ratio
        }
        with open("bot_task.json", "w", encoding="utf-8") as f: json.dump(payload, f, ensure_ascii=False)
        st.success("> 📡 ส่งข้อมูลให้บอทเรียบร้อย หน้าต่างบอทจะเด้งขึ้นมาทำงาน...")
        subprocess.Popen(["python", "-u", "test_bot.py"], env=dict(os.environ, PYTHONIOENCODING="utf-8")).wait()
        time.sleep(1)
        st.rerun()

# ==========================================
# 🗂️ 4. เมนูนำทางแบบจัดหมวดหมู่ (Sidebar)
# ==========================================
if logo_img != "🤖": st.sidebar.image(logo_img, width=150)
st.sidebar.markdown("### 🗂️ แผงควบคุมหลัก")

category = st.sidebar.selectbox("📂 เลือกหมวดหมู่คอนเทนต์:", [
    "💼 หมวดธุรกิจและการขาย",
    "🤣 หมวดเอนเตอร์เทน & มีม",
    "🕶️ หมวดช่องไร้หน้า (Faceless)"
])
st.sidebar.markdown("---")

app_mode = ""
if category == "💼 หมวดธุรกิจและการขาย":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🎬 โฆษณาสินค้า (Ad Director)", "🍰 รีวิวร้านตัวเอง (UGC Vlogger)", "🎤 วิทยากร AI (AI Spokesperson)"])
elif category == "🤣 หมวดเอนเตอร์เทน & มีม":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🐾 สัตว์เลี้ยงไวรัล (Viral Pet)", "🎭 คาแรคเตอร์สายฮา (Caricature)", "🎙️ ทอล์คโชว์สายปั่น (Stand-up)"])
elif category == "🕶️ หมวดช่องไร้หน้า (Faceless)":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🕶️ ช่องคำคมสู้ชีวิต (Sigma)", "👻 ช่องเล่าเรื่องหลอน (Creepypasta)"])

# =========================================================================================
# 💼 โหมด 1: 🎬 โฆษณาสินค้า (Ad Director) - อัปเกรด 14 ตัวเลือก & โปสเตอร์
# =========================================================================================
if app_mode == "🎬 โฆษณาสินค้า (Ad Director)":
    st.markdown('<div class="main-header">🎬 ระบบผู้กำกับโฆษณา AI (Full 14-Mode Options)</div>', unsafe_allow_html=True)
    if 'ad_product_text' not in st.session_state: st.session_state.ad_product_text = ""
    if 'ad_video_prompt' not in st.session_state: st.session_state.ad_video_prompt = ""
    if 'ad_poster_prompt' not in st.session_state: st.session_state.ad_poster_prompt = ""
    if 'ad_imgs' not in st.session_state: st.session_state.ad_imgs = []

    with st.expander("📸 0. อัปโหลดรูปภาพสินค้า (ล็อกความเป๊ะ 100%)", expanded=True):
        up_files = st.file_uploader("อัปโหลดรูปสินค้าเพื่อคงสภาพ 100% Faithful", type=['png', 'jpg'], accept_multiple_files=True, key="ad_up")
        if up_files:
            st.session_state.ad_imgs = []
            os.makedirs("temp_refs", exist_ok=True)
            path = os.path.join("temp_refs", up_files[0].name)
            with open(path, "wb") as f: f.write(up_files[0].getbuffer())
            st.session_state.ad_imgs.append(path)
            if st.button("🔍 สกัดข้อมูล Ingredients", type="secondary"):
                st.session_state.ad_product_text = smart_generate([Image.open(up_files[0]), "บรรยายรายละเอียด วัสดุ สี และรูปร่างสินค้าในภาพอย่างละเอียด เพื่อเป็น Ingredient Lock"])
        st.session_state.ad_product_text = st.text_area("📝 ข้อมูลสินค้า:", value=st.session_state.ad_product_text, height=80)

    tab_vid, tab_poster, tab_run = st.tabs(["🎬 1. สร้างสคริปต์วิดีโอ (14 ตัวเลือก)", "🖼️ 2. สร้างโปสเตอร์/หน้าปก", "🚀 3. รันระบบ (Handoff)"])
    
    with tab_vid:
        st.markdown("### 🎛️ แผงควบคุมวิดีโอ (14 Controls)")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 👤 พรีเซนเตอร์:", ["หญิงสาว (Young Female)", "ชายหนุ่ม (Young Male)", "ไม่มีพรีเซนเตอร์ (เน้นสินค้า)"], "ad_pres")
            render_custom_select("2. 🗣️ น้ำเสียง/อารมณ์พูด:", ["เพื่อนป้ายยา (Friendly)", "ตื่นเต้นขายเก่ง (Energetic)", "พรีเมียม (Luxury)"], "ad_tone")
            render_custom_select("3. 🎯 กลุ่มเป้าหมาย:", ["วัยรุ่น (Gen Z)", "คนทำงาน (Mass)", "ทาสแมว/สัตว์เลี้ยง"], "ad_target")
            render_custom_select("4. 🌐 ภาษา/สำเนียง:", ["ภาษาไทยกลาง", "ภาษาอังกฤษ", "ภาษาถิ่น (อีสาน/ใต้/เหนือ)"], "ad_lang")
            render_custom_select("5. ⏳ ความยาวคลิป:", ["สั้นกระชับ (15s)", "มาตรฐาน (30s-60s)"], "ad_dur")
        with c2:
            render_custom_select("6. 🎥 สไตล์โฆษณา:", ["UGC (รีวิวสมจริง)", "Cinematic (ภาพยนตร์)", "Stop Motion"], "ad_style")
            render_custom_select("7. 📖 การเล่าเรื่อง (Story):", ["PAS (ปัญหา-ทางแก้)", "Before/After", "เล่าเรื่องชวนติดตาม"], "ad_story")
            render_custom_select("8. 👉 ปิดการขาย (CTA):", ["กดตะกร้าสีเหลือง", "ลิงก์หน้าโปรไฟล์", "ทักแชทสั่งซื้อ"], "ad_cta")
            render_custom_select("9. 📱 แพลตฟอร์ม:", ["TikTok / Shopee / Lazada", "Facebook Reels / IG"], "ad_plat")
            render_custom_select("10. 🎵 ดนตรี (BGM):", ["Pop สนุกสนาน", "ตื่นเต้นเร้าใจ (Epic)", "ไม่มีเพลง เน้น ASMR"], "ad_music")
        with c3:
            render_custom_select("11. 🎨 โทนสี/ภาพ:", ["สดใสสว่าง (Bright & Airy)", "โทนดาร์กเท่ๆ (Dark/Moody)"], "ad_color")
            render_custom_select("12. 🎥 มุมกล้อง:", ["ระดับสายตา (Eye-level)", "ซูมใกล้ (Close-up Macro)", "ถ่ายมุมสูง (Top-down)"], "ad_cam")
            render_custom_select("13. 💡 แสงและบรรยากาศ:", ["แสงธรรมชาติ (Natural light)", "แสงสตูดิโอ (Studio Lighting)"], "ad_light")
            render_custom_select("14. ✍️ ข้อความบนจอ:", ["โปรดระบุ...", "แจกโค้ดส่วนลด", "จัดส่งฟรี!"], "ad_text")

        if st.button("✨ ให้ AI เขียนสคริปต์วิดีโอ (ประมวลผล 14 ตัวเลือก)", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์โฆษณา: {st.session_state.ad_product_text} พรีเซนเตอร์:{st.session_state.get('ad_pres')} เสียง:{st.session_state.get('ad_tone')} เป้าหมาย:{st.session_state.get('ad_target')} ภาษา:{st.session_state.get('ad_lang')} ความยาว:{st.session_state.get('ad_dur')} สไตล์:{st.session_state.get('ad_style')} เล่าเรื่อง:{st.session_state.get('ad_story')} CTA:{st.session_state.get('ad_cta')} แพลตฟอร์ม:{st.session_state.get('ad_plat')} เพลง:{st.session_state.get('ad_music')} โทนสี:{st.session_state.get('ad_color')} มุมกล้อง:{st.session_state.get('ad_cam')} แสง:{st.session_state.get('ad_light')} ข้อความ:{st.session_state.get('ad_text')}. กฎ: แบ่งเป็นฉากๆ มี 'Prompt สร้างภาพนิ่ง:' และ 'Prompt สร้างวิดีโอ:' แยกกันเป็นภาษาอังกฤษ"
            st.session_state.ad_video_prompt = smart_generate(prompt)
        if st.session_state.ad_video_prompt: st.code(st.session_state.ad_video_prompt, language="markdown")

    with tab_poster:
        st.markdown("### 🖼️ สร้างโปสเตอร์และหน้าปก (Thumbnail)")
        st.info("นำรูปสินค้าที่อัปโหลดไว้ มาออกแบบเป็นโปสเตอร์โฆษณา หรือหน้าปกคลิปที่ดึงดูดสายตา")
        c1, c2 = st.columns(2)
        with c1:
            render_custom_select("🎨 สไตล์การจัดวาง (Layout):", ["โปสเตอร์โปรโมทสินค้าแบบมินิมอล (Minimalist Product Ad)", "หน้าปกคลิป YouTube/TikTok แบบดึงดูดสายตา (Clickbait Thumbnail)", "โบรชัวร์ลดราคา (Discount Sale Flyer)"], "poster_layout")
            render_custom_select("💡 องค์ประกอบเสริม (Props):", ["วางบนแท่นสวยงาม (Product Podium)", "มีของประดับเข้ากับสินค้า (Matching aesthetic props)"], "poster_props")
        with c2:
            render_custom_select("📝 คำโปรยบนโปสเตอร์ (Text Overlay):", ["รับประกัน 24 ชม./ไม่มีบิน/เป็นเมล์ Gmail Hotmail/เข้าล็อคอินเปลี่ยนเป็นของตัวเองได้เลย ราคา 790 บาท (รับประกัน 20 วัน)", "รับประกันการใช้งาน 20 วัน!", "โปรโมชั่นพิเศษ ลดราคา 50%", "ไม่มีข้อความ (เน้นรูปสินค้า)"], "poster_text")
        
        if st.button("🎨 ให้ AI สร้าง Prompt โปสเตอร์", type="primary", use_container_width=True):
            prompt = f"เขียน 'Prompt สร้างภาพนิ่ง:' ภาษาอังกฤษเพื่อออกแบบโปสเตอร์/หน้าปก สินค้าคือ: {st.session_state.ad_product_text} สไตล์การจัดวาง: {st.session_state.get('poster_layout')} พร็อพ: {st.session_state.get('poster_props')} ข้อความฮุก: {st.session_state.get('poster_text')}. (คำสั่งต้องพร้อมนำไปเจนใน Nano Banana 2)"
            st.session_state.ad_poster_prompt = smart_generate(prompt)
        if st.session_state.ad_poster_prompt: 
            st.code(st.session_state.ad_poster_prompt, language="markdown")

    with tab_run:
        if st.session_state.ad_poster_prompt:
            st.markdown("#### 🖼️ โปสเตอร์ / หน้าปกคลิป")
            if st.button("⚙️ รันบอทสร้างโปสเตอร์ (Nano Banana 2)", key="run_poster_ad"):
                run_bot_dialog(0, st.session_state.ad_poster_prompt, st.session_state.ad_imgs, True, is_poster_only=True)
            st.divider()

        if st.session_state.ad_video_prompt:
            st.markdown("#### 🎬 ฉากวิดีโอโฆษณา")
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.ad_video_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=False):
                    st.write(s_text[:200] + "...")
                    if st.button(f"⚙️ รันบอทสร้างวิดีโอฉาก {i+1}", key=f"run_vid_ad_{i}"):
                        run_bot_dialog(i+1, s_text, st.session_state.ad_imgs, i==0)

# =========================================================================================
# 🤣 โหมด 2: 🐾 สัตว์เลี้ยงไวรัล (Viral Pet) - คืนชีพโปสเตอร์
# =========================================================================================
elif app_mode == "🐾 สัตว์เลี้ยงไวรัล (Viral Pet)":
    st.markdown('<div class="main-header">🐾 สตูดิโอสัตว์เลี้ยงไวรัล</div>', unsafe_allow_html=True)
    if 'pet_prompt' not in st.session_state: st.session_state.pet_prompt = ""
    if 'pet_poster_prompt' not in st.session_state: st.session_state.pet_poster_prompt = ""
    if 'pet_imgs' not in st.session_state: st.session_state.pet_imgs = []

    with st.expander("📸 0. อัปโหลดรูป (ล็อกหน้าตาสัตว์/อาหาร)"):
        up_files = st.file_uploader("อัปโหลดรูปล็อกเรฟเฟอเรนซ์", type=['png', 'jpg'], key="pet_up")
        if up_files:
            st.session_state.pet_imgs = []
            os.makedirs("temp_refs", exist_ok=True)
            path = os.path.join("temp_refs", up_files.name)
            with open(path, "wb") as f: f.write(up_files.getbuffer())
            st.session_state.pet_imgs.append(path)
    
    tab_vid, tab_poster, tab_run = st.tabs(["🎬 1. ตั้งค่าคาแรคเตอร์มีม", "🖼️ 2. สร้างโปสเตอร์ปกคลิป", "🚀 3. รันบอท (Handoff)"])
    
    with tab_vid:
        c1, c2, c3 = st.columns(3)
        with c1: render_custom_select("🐱 สัตว์เลี้ยง:", ["แมวสลิด 2 ตัว", "แมวส้ม", "หมาไซ"], "pet_actor")
        with c2: render_custom_select("🔪 แอคชั่น:", ["ทำกับข้าว", "บ่นเจ้านาย"], "pet_act")
        with c3: render_custom_select("💬 เสียง:", ["เถียงกันเรื่องอาหาร", "ASMR"], "pet_audio")
        if st.button("✨ ให้ AI เขียนสคริปต์มีม", type="primary"):
            st.session_state.pet_prompt = smart_generate(f"สคริปต์มีมสัตว์เลี้ยง (Anthropomorphic) {st.session_state.get('pet_actor')} กำลัง {st.session_state.get('pet_act')} เสียง: {st.session_state.get('pet_audio')}. แบ่งเป็นฉากๆ แยก Prompt ภาพนิ่งและวิดีโอ")
        if st.session_state.pet_prompt: st.code(st.session_state.pet_prompt, language="markdown")
    
    with tab_poster:
        render_custom_select("📝 คำโปรยบนปกคลิป (Clickbait Text):", ["POV: เมื่อทาสใช้ให้ทำกับข้าว", "เมนูเด็ดเชฟสี่ขา"], "pet_poster_txt")
        if st.button("🎨 สร้าง Prompt หน้าปกมีม", type="primary"):
            st.session_state.pet_poster_prompt = smart_generate(f"เขียน 'Prompt สร้างภาพนิ่ง:' ภาษาอังกฤษ ออกแบบหน้าปก YouTube/TikTok ของสัตว์เลี้ยงไวรัล {st.session_state.get('pet_actor')} กำลัง {st.session_state.get('pet_act')} พร้อมข้อความฮุก: {st.session_state.get('pet_poster_txt')}")
        if st.session_state.pet_poster_prompt: st.code(st.session_state.pet_poster_prompt, language="markdown")

    with tab_run:
        if st.session_state.pet_poster_prompt:
            if st.button("⚙️ รันบอทสร้างหน้าปกคลิป", key="run_poster_pet"):
                run_bot_dialog(0, st.session_state.pet_poster_prompt, st.session_state.pet_imgs, True, is_poster_only=True)
            st.divider()
        if st.session_state.pet_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.pet_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=False):
                    if st.button(f"⚙️ รันบอทสร้างคลิปฉาก {i+1}", key=f"run_vid_pet_{i}"):
                        run_bot_dialog(i+1, s_text, st.session_state.pet_imgs, i==0)

# --- โหมดที่เหลือ ใช้โครงสร้างดึงและส่ง Handoff แบบเดียวกัน ---
elif app_mode != "Dashboard":
    st.info(f"👉 โหมด: **{app_mode}** เปิดใช้งานพร้อมระบบรันบอท (Handoff) อยู่เบื้องหลังเรียบร้อยแล้วครับ")