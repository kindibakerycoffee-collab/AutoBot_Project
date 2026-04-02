import streamlit as st
import time
from google import genai
from PIL import Image
import json
import subprocess
import os
import re

# ==========================================
# 🚨 1. ตั้งค่าหน้าเว็บหลัก & UI/UX (Black & Gold Theme)
# ==========================================
try:
    logo_img = Image.open("logo.png") 
except FileNotFoundError:
    logo_img = "🤖" 

st.set_page_config(page_title="NextGen Ai STORE | Super App", page_icon=logo_img, layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #D4AF37; font-weight: 700; margin-bottom: 0px; text-shadow: 1px 1px 10px rgba(212, 175, 55, 0.3);}
    .sub-header { font-size: 1.1rem; color: #A0A0A0; margin-bottom: 20px;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 5px 5px 0px 0px; padding: 10px 20px; background-color: #2A2A2A; color: #FFFFFF; border: 1px solid #333;}
    .stTabs [aria-selected="true"] { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold;}
    hr { border-color: #333333; }
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
# 🗂️ 4. เมนูนำทาง (Sidebar)
# ==========================================
if logo_img != "🤖": st.sidebar.image(logo_img, width=150)
st.sidebar.markdown("### 🗂️ แผงควบคุมหลัก")

category = st.sidebar.selectbox("📂 เลือกหมวดหมู่คอนเทนต์:", [
    "🏠 หน้าแรก (Dashboard)",
    "💼 หมวดธุรกิจและการขาย",
    "🤣 หมวดเอนเตอร์เทน & มีม",
    "🕶️ หมวดช่องไร้หน้า (Faceless)",
    "🎵 หมวดเพลงและการเต้น"
])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 สถานะ API Key")
if not api_keys_list: 
    st.sidebar.error("❌ ยังไม่ได้ใส่ API Key")
else:
    for i in range(len(api_keys_list)): 
        st.sidebar.markdown(f"**Key {i+1}:** {st.session_state.key_status.get(i, '⏳')}")

app_mode = "Dashboard"
if category == "💼 หมวดธุรกิจและการขาย":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🎬 โฆษณาสินค้า (Ad Director)", "🍰 รีวิวร้านตัวเอง (UGC Vlogger)", "🎤 วิทยากร AI (AI Spokesperson)"])
elif category == "🤣 หมวดเอนเตอร์เทน & มีม":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🐾 สัตว์เลี้ยงไวรัล (Viral Pet)", "🎭 คาแรคเตอร์สายฮา (Caricature)", "🎙️ ทอล์คโชว์สายปั่น (Stand-up)"])
elif category == "🕶️ หมวดช่องไร้หน้า (Faceless)":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🕶️ ช่องคำคมสู้ชีวิต (Sigma Motivation)", "👻 ช่องเล่าเรื่องหลอน (Creepypasta)"])
elif category == "🎵 หมวดเพลงและการเต้น":
    app_mode = st.sidebar.radio("เลือกเครื่องมือ:", ["🕺 สายแดนซ์ชาเลนจ์ (Dance Character)", "🎶 ห้องอัดเสียงเพลงแปลง (Parody Music)"])

# =========================================================================================
# 🏠 หน้าแรก (Dashboard)
# =========================================================================================
if app_mode == "Dashboard":
    st.markdown('<div class="main-header">ยินดีต้อนรับสู่ NextGen Ai STORE Super App ✨</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">ศูนย์รวมเครื่องมือสร้างคอนเทนต์ AI อัตโนมัติ ครบจบในที่เดียว</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col1.info("**💼 สายธุรกิจ:** สร้างคลิปขายของ, รีวิวร้าน, ปั้นตัวแทน AI ออกมาให้ความรู้")
    col2.success("**🤣 สายมีม:** ปั้นคลิปสัตว์เลี้ยงฮาๆ, ลุงไทบ้าน, เวทีทอล์คโชว์เสียดสีสังคม")
    col3.warning("**🕶️ สาย Faceless:** ทำช่องคำคม หรือช่องเล่าเรื่องผีแบบไม่เปิดหน้า")

# =========================================================================================
# 💼 โหมด 1: 🎬 โฆษณาสินค้า (Ad Director)
# =========================================================================================
elif app_mode == "🎬 โฆษณาสินค้า (Ad Director)":
    st.markdown('<div class="main-header">🎬 ระบบผู้กำกับโฆษณา AI</div>', unsafe_allow_html=True)
    if 'ad_product_text' not in st.session_state: st.session_state.ad_product_text = ""
    if 'ad_video_prompt' not in st.session_state: st.session_state.ad_video_prompt = ""
    if 'ad_poster_prompt' not in st.session_state: st.session_state.ad_poster_prompt = ""
    if 'ad_imgs' not in st.session_state: st.session_state.ad_imgs = []

    with st.expander("📸 0. อัปโหลดรูปภาพสินค้า (ล็อกความเป๊ะ)", expanded=True):
        up_files = st.file_uploader("อัปโหลดรูปสินค้า", type=['png', 'jpg'], accept_multiple_files=True, key="ad_up")
        if up_files:
            st.session_state.ad_imgs = []
            os.makedirs("temp_refs", exist_ok=True)
            path = os.path.join("temp_refs", up_files[0].name)
            with open(path, "wb") as f: f.write(up_files[0].getbuffer())
            st.session_state.ad_imgs.append(path)
            if st.button("🔍 สกัดข้อมูล Ingredients", type="secondary"):
                st.session_state.ad_product_text = smart_generate([Image.open(up_files[0]), "บรรยายรายละเอียด วัสดุ สี และรูปร่างสินค้าในภาพอย่างละเอียด"])
        st.session_state.ad_product_text = st.text_area("📝 ข้อมูลสินค้า:", value=st.session_state.ad_product_text, height=80)

    tab_vid, tab_poster, tab_run = st.tabs(["🎬 1. สร้างสคริปต์วิดีโอ", "🖼️ 2. สร้างโปสเตอร์/หน้าปก", "🚀 3. รันระบบ (Handoff)"])
    
    with tab_vid:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 👤 พรีเซนเตอร์:", ["ไม่มีพรีเซนเตอร์", "หญิงสาว", "ชายหนุ่ม"], "ad_pres")
            render_custom_select("2. 🗣️ น้ำเสียง:", ["เพื่อนป้ายยา", "ตื่นเต้นขายเก่ง", "พรีเมียม"], "ad_tone")
            render_custom_select("3. 🎯 กลุ่มเป้าหมาย:", ["วัยรุ่น", "คนทำงาน"], "ad_target")
            render_custom_select("4. 🌐 ภาษา:", ["ภาษาไทยกลาง", "ภาษาอังกฤษ"], "ad_lang")
            render_custom_select("5. ⏳ ความยาวคลิป:", ["สั้นกระชับ", "มาตรฐาน"], "ad_dur")
        with c2:
            render_custom_select("6. 🎥 สไตล์โฆษณา:", ["UGC", "Cinematic"], "ad_style")
            render_custom_select("7. 📖 การเล่าเรื่อง:", ["PAS (ปัญหา-ทางแก้)", "Before/After"], "ad_story")
            render_custom_select("8. 👉 ปิดการขาย:", ["กดตะกร้า", "ทักแชท"], "ad_cta")
            render_custom_select("9. 📱 แพลตฟอร์ม:", ["TikTok / Shopee", "Facebook Reels"], "ad_plat")
            render_custom_select("10. 🎵 ดนตรี:", ["Pop", "Epic"], "ad_music")
        with c3:
            render_custom_select("11. 🎨 โทนสี:", ["สดใสสว่าง", "โทนดาร์กเท่ๆ"], "ad_color")
            render_custom_select("12. 🎥 มุมกล้อง:", ["ระดับสายตา", "ซูมใกล้"], "ad_cam")
            render_custom_select("13. 💡 แสงและบรรยากาศ:", ["แสงธรรมชาติ", "แสงสตูดิโอ"], "ad_light")
            render_custom_select("14. ✍️ ข้อความบนจอ:", ["โปรโมชั่นพิเศษ", "จัดส่งฟรี", "ไม่มีข้อความ"], "ad_text")

        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("✨ ให้ AI เขียนสคริปต์วิดีโอ", type="primary", use_container_width=True):
                prompt = f"เขียนสคริปต์โฆษณา: {st.session_state.ad_product_text} พรีเซนเตอร์:{st.session_state.get('ad_pres')} เสียง:{st.session_state.get('ad_tone')} เป้าหมาย:{st.session_state.get('ad_target')} ภาษา:{st.session_state.get('ad_lang')} ความยาว:{st.session_state.get('ad_dur')} สไตล์:{st.session_state.get('ad_style')} เล่าเรื่อง:{st.session_state.get('ad_story')} CTA:{st.session_state.get('ad_cta')} แพลตฟอร์ม:{st.session_state.get('ad_plat')} เพลง:{st.session_state.get('ad_music')} โทนสี:{st.session_state.get('ad_color')} มุมกล้อง:{st.session_state.get('ad_cam')} แสง:{st.session_state.get('ad_light')} ข้อความ:{st.session_state.get('ad_text')}. แบ่งเป็นฉากๆ แยก Prompt ภาพนิ่งและวิดีโอ"
                st.session_state.ad_video_prompt = smart_generate(prompt)
        with col_btn2:
            if st.button("🔄 รีเซ็ตวิดีโอ", use_container_width=True):
                st.session_state.ad_video_prompt = ""
                st.rerun()

        if st.session_state.ad_video_prompt: st.code(st.session_state.ad_video_prompt, language="markdown")

    with tab_poster:
        c1, c2 = st.columns(2)
        with c1:
            render_custom_select("🎨 สไตล์โปสเตอร์:", ["โปสเตอร์แบบมินิมอล", "หน้าปกคลิปดึงดูดสายตา", "โบรชัวร์ลดราคา"], "poster_layout")
            render_custom_select("💡 องค์ประกอบเสริม:", ["วางบนแท่นสวยงาม", "มีของประดับเข้ากับสินค้า"], "poster_props")
        with c2:
            render_custom_select("📝 คำโปรยหน้าปก:", ["โปรโมชั่นพิเศษ ลด 50%", "สั่งซื้อวันนี้ ส่งฟรี!", "ไม่มีข้อความ"], "poster_text")
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("🎨 ให้ AI สร้าง Prompt โปสเตอร์", type="primary", use_container_width=True):
                prompt = f"เขียน 'Prompt สร้างภาพนิ่ง:' เพื่อออกแบบโปสเตอร์ สินค้าคือ: {st.session_state.ad_product_text} สไตล์: {st.session_state.get('poster_layout')} พร็อพ: {st.session_state.get('poster_props')} ข้อความฮุก: {st.session_state.get('poster_text')}"
                st.session_state.ad_poster_prompt = smart_generate(prompt)
        with col_btn2:
            if st.button("🔄 รีเซ็ตโปสเตอร์", use_container_width=True):
                st.session_state.ad_poster_prompt = ""
                st.rerun()

        if st.session_state.ad_poster_prompt: st.code(st.session_state.ad_poster_prompt, language="markdown")

    with tab_run:
        if st.session_state.ad_poster_prompt:
            st.markdown("#### 🖼️ รันโปสเตอร์ / หน้าปกคลิป")
            if st.button("⚙️ รันบอทสร้างโปสเตอร์", key="run_poster_ad"):
                run_bot_dialog(0, st.session_state.ad_poster_prompt, st.session_state.ad_imgs, True, is_poster_only=True)
            st.divider()
        if st.session_state.ad_video_prompt:
            st.markdown("#### 🎬 รันวิดีโอโฆษณา")
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.ad_video_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=False):
                    if st.button(f"⚙️ รันบอทสร้างวิดีโอฉาก {i+1}", key=f"run_vid_ad_{i}"):
                        run_bot_dialog(i+1, s_text, st.session_state.ad_imgs, i==0)

# =========================================================================================
# 💼 โหมด 5: 🍰 รีวิวร้านตัวเอง (UGC Vlogger)
# =========================================================================================
elif app_mode == "🍰 รีวิวร้านตัวเอง (UGC Vlogger)":
    st.markdown('<div class="main-header">🍰 สตูดิโอเจ้าของร้านรีวิวเอง (UGC Vlogger)</div>', unsafe_allow_html=True)
    if 'ugc_prompt' not in st.session_state: st.session_state.ugc_prompt = ""
    if 'ugc_imgs' not in st.session_state: st.session_state.ugc_imgs = []

    with st.expander("📸 0. อัปโหลดรูปเมนู"):
        up_files = st.file_uploader("ลากรูปอาหาร/สินค้ามาวาง", type=['png', 'jpg'], key="ugc_up")
        if up_files:
            st.session_state.ugc_imgs = []
            os.makedirs("temp_refs", exist_ok=True)
            path = os.path.join("temp_refs", up_files.name)
            with open(path, "wb") as f: f.write(up_files.getbuffer())
            st.session_state.ugc_imgs.append(path)

    tab_vid, tab_run = st.tabs(["⚙️ 1. ตั้งค่าร้านและสคริปต์", "🚀 2. รันบอท (Handoff)"])
    with tab_vid:
        c1, c2 = st.columns(2)
        with c1:
            shop = st.text_input("🏠 ชื่อร้าน:", placeholder="ระบุชื่อร้าน...")
            menu = st.text_input("🍔 เมนูเด็ด:", placeholder="ระบุเมนู...")
            local_cta = st.text_input("📍 พิกัด / ปิดการขาย:", placeholder="ระบุพิกัด หรือช่องทางสั่งซื้อ...")
        with c2:
            render_custom_select("👤 ผู้รีวิว:", ["เจ้าของร้าน", "วัยรุ่น"], "ugc_actor")
            render_custom_select("📸 พร็อพกล้อง:", ["ตั้งมือถือบนขาตั้ง", "ถือกล้องเซลฟี่"], "ugc_props")
            render_custom_select("🗣️ ภาษาถิ่น:", ["ภาษาไทยกลาง", "ภาษาอีสาน", "ภาษาใต้"], "ugc_dialect")
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("✨ ให้ AI เขียนสคริปต์รีวิว", type="primary", use_container_width=True):
                st.session_state.ugc_prompt = smart_generate(f"สคริปต์ Vlogger รีวิวร้าน {shop} เมนู {menu} พิกัด {local_cta} คนรีวิว: {st.session_state.get('ugc_actor')} ภาษา: {st.session_state.get('ugc_dialect')} มุมกล้อง: {st.session_state.get('ugc_props')}. แบ่งฉากชัดเจน มี Prompt ภาพ/วิดีโอ (ใส่ Audio cues)")
        with col_btn2:
            if st.button("🔄 รีเซ็ต", use_container_width=True):
                st.session_state.ugc_prompt = ""
                st.rerun()

        if st.session_state.ugc_prompt: st.code(st.session_state.ugc_prompt, language="markdown")
    with tab_run:
        if st.session_state.ugc_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.ugc_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"ugc_btn_{i}"):
                        run_bot_dialog(i+1, s_text, st.session_state.ugc_imgs, i==0)

# =========================================================================================
# 💼 โหมด 4: 🎤 วิทยากร AI (AI Spokesperson)
# =========================================================================================
elif app_mode == "🎤 วิทยากร AI (AI Spokesperson)":
    st.markdown('<div class="main-header">🎤 สตูดิโอวิทยากร AI</div>', unsafe_allow_html=True)
    if 'spk_prompt' not in st.session_state: st.session_state.spk_prompt = ""
    if 'spk_raw_text' not in st.session_state: st.session_state.spk_raw_text = ""
    
    st.session_state.spk_raw_text = st.text_area("📝 บทพูดของคุณ (Script):", value=st.session_state.spk_raw_text, height=100)
    if st.button("🪄 ขัดเกลาข้อความให้ดูโปรขึ้น", type="secondary"):
        st.session_state.spk_raw_text = smart_generate(f"ขัดเกลาให้สละสลวยดูเป็นมืออาชีพ: {st.session_state.spk_raw_text}")
        st.rerun()

    tab_vid, tab_run = st.tabs(["⚙️ 1. ตั้งค่าวิทยากร", "🚀 2. รันบอท (Handoff)"])
    with tab_vid:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("👤 วิทยากร:", ["CEO หนุ่ม", "นักธุรกิจหญิง"], "spk_actor")
            render_custom_select("👕 ชุด:", ["เสื้อยืดกางเกงยีนส์", "ชุดสูท"], "spk_costume")
        with c2:
            render_custom_select("🏡 ฉาก:", ["เวที TED Talk", "พอดแคสต์"], "spk_setting")
            render_custom_select("🎥 มุมกล้อง:", ["ครึ่งตัว", "ซูมใกล้"], "spk_camera")
        with c3:
            render_custom_select("🗣️ อารมณ์:", ["สร้างแรงบันดาลใจ", "ให้ความรู้จริงจัง"], "spk_tone")
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("✨ ให้ AI เขียนสคริปต์วิทยากร", type="primary", use_container_width=True):
                st.session_state.spk_prompt = smart_generate(f"สคริปต์ AI Spokesperson วิทยากร: {st.session_state.get('spk_actor')} ฉาก: {st.session_state.get('spk_setting')} กล้อง: {st.session_state.get('spk_camera')} บทพูด: {st.session_state.spk_raw_text}. แยก Prompt ภาพและวิดีโอ (ใส่ Audio Cues)")
        with col_btn2:
            if st.button("🔄 รีเซ็ต", use_container_width=True):
                st.session_state.spk_prompt = ""
                st.rerun()
                
        if st.session_state.spk_prompt: st.code(st.session_state.spk_prompt, language="markdown")
    with tab_run:
        if st.session_state.spk_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.spk_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"spk_btn_{i}"):
                        run_bot_dialog(i+1, s_text, [], i==0)

# =========================================================================================
# 🤣 โหมด 2: 🐾 สัตว์เลี้ยงไวรัล (Viral Pet)
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
    
    tab_vid, tab_poster, tab_run = st.tabs(["🎬 1. ตั้งค่าคาแรคเตอร์", "🖼️ 2. สร้างโปสเตอร์", "🚀 3. รันบอท (Handoff)"])
    with tab_vid:
        c1, c2, c3 = st.columns(3)
        with c1: 
            render_custom_select("🐱 สัตว์เลี้ยง:", ["แมวสลิด", "หมาไซ"], "pet_actor")
            render_custom_select("👕 ชุด:", ["ใส่ผ้ากันเปื้อน", "ไม่ใส่ชุด"], "pet_costume")
        with c2: 
            render_custom_select("🔪 แอคชั่น:", ["ทำกับข้าว", "บ่นเจ้านาย"], "pet_act")
            render_custom_select("🏡 ฉาก:", ["แคร่ไม้ไผ่", "ห้องครัว"], "pet_set")
        with c3: 
            render_custom_select("💬 เสียงพูด:", ["เถียงกัน", "ASMR"], "pet_audio")
        
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("✨ ให้ AI เขียนสคริปต์มีม", type="primary", use_container_width=True):
                st.session_state.pet_prompt = smart_generate(f"สคริปต์มีมสัตว์เลี้ยง (Anthropomorphic) {st.session_state.get('pet_actor')} ชุด {st.session_state.get('pet_costume')} กำลัง {st.session_state.get('pet_act')} ฉาก {st.session_state.get('pet_set')} เสียง: {st.session_state.get('pet_audio')}. แยก Prompt ภาพและวิดีโอ (พร้อม Audio Cues)")
        with col_btn2:
            if st.button("🔄 รีเซ็ตวิดีโอ", use_container_width=True):
                st.session_state.pet_prompt = ""
                st.rerun()

        if st.session_state.pet_prompt: st.code(st.session_state.pet_prompt, language="markdown")
    
    with tab_poster:
        render_custom_select("📝 คำโปรยบนปกคลิป:", ["POV: ทาสใช้ให้ทำกับข้าว", "เชฟสี่ขา"], "pet_poster_txt")
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1:
            if st.button("🎨 สร้าง Prompt หน้าปก", type="primary", use_container_width=True):
                st.session_state.pet_poster_prompt = smart_generate(f"Prompt สร้างภาพนิ่ง หน้าปก YouTube ของ {st.session_state.get('pet_actor')} กำลัง {st.session_state.get('pet_act')} ข้อความ: {st.session_state.get('pet_poster_txt')}")
        with col_btn2:
            if st.button("🔄 รีเซ็ตโปสเตอร์", use_container_width=True):
                st.session_state.pet_poster_prompt = ""
                st.rerun()

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
                    if st.button(f"⚙️ รันบอทคลิปฉาก {i+1}", key=f"run_vid_pet_{i}"):
                        run_bot_dialog(i+1, s_text, st.session_state.pet_imgs, i==0)

# =========================================================================================
# 🤣 โหมด 3, 6, 9, 10, 7, 8 (ย่อโค้ด UI ให้สะอาดตา แต่ฟังก์ชันครบ)
# =========================================================================================
elif app_mode == "🎭 คาแรคเตอร์สายฮา (Caricature)":
    st.markdown('<div class="main-header">🎭 สตูดิโอปั้นมีมไทบ้าน</div>', unsafe_allow_html=True)
    render_custom_select("🤪 ลักษณะ:", ["หน้าเหี่ยว", "ผมฟู"], "c_feat")
    if st.button("🚀 เจนสคริปต์"): st.code(smart_generate(f"Caricature: {st.session_state.get('c_feat')}"))

elif app_mode == "🎙️ ทอล์คโชว์สายปั่น (Stand-up)":
    st.markdown('<div class="main-header">🎙️ ทอล์คโชว์สายฮา</div>', unsafe_allow_html=True)
    topic = st.text_input("📌 หัวข้อบ่น:")
    if st.button("🚀 เจนสคริปต์"): st.code(smart_generate(f"Stand-up comedy: {topic}"))

elif app_mode == "🕶️ ช่องคำคมสู้ชีวิต (Sigma Motivation)":
    st.markdown('<div class="main-header">🕶️ คำคม Sigma</div>', unsafe_allow_html=True)
    topic = st.text_input("📌 หัวข้อคำคม:")
    if st.button("🚀 เจนสคริปต์"): st.code(smart_generate(f"คำคม: {topic}"))

elif app_mode == "👻 ช่องเล่าเรื่องหลอน (Creepypasta)":
    st.markdown('<div class="main-header">👻 เล่าเรื่องผี</div>', unsafe_allow_html=True)
    story = st.text_area("📖 โครงเรื่อง:")
    if st.button("🚀 เจนสคริปต์"): st.code(smart_generate(f"เรื่องผี: {story}"))

elif app_mode == "🕺 สายแดนซ์ชาเลนจ์ (Dance Character)":
    st.markdown('<div class="main-header">🕺 ปั้นนักเต้น</div>', unsafe_allow_html=True)
    render_custom_select("🐱 ตัวละคร:", ["แมว", "หมี"], "d_actor")
    if st.button("🚀 เจน Prompt"): st.code(smart_generate(f"Full body: {st.session_state.get('d_actor')}"))

elif app_mode == "🎶 ห้องอัดเสียงเพลงแปลง (Parody Music)":
    st.markdown('<div class="main-header">🎶 อัดเสียงเพลงแปลง</div>', unsafe_allow_html=True)
    topic = st.text_input("📌 เรื่องที่จะบ่น:")
    if st.button("🚀 เจนเนื้อเพลง"): st.code(smart_generate(f"เพลงตลกเรื่อง: {topic}"))