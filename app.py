import streamlit as st
import time
from google import genai
from PIL import Image
import json
import subprocess
import os
import re
import uuid 

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

def render_custom_select(label, options, key, help_text=None):
    opt_list = options + ["พิมพ์กำหนดเอง..."]
    
    if key not in st.session_state:
        st.session_state[key] = options[0]
        
    current_val = st.session_state[key]
    idx = options.index(current_val) if current_val in options else len(opt_list) - 1
    
    selected = st.selectbox(label, opt_list, index=idx, key=f"ui_widget_{key}", help=help_text)
    
    if selected == "พิมพ์กำหนดเอง...":
        default_text = current_val if current_val not in options else ""
        custom_val = st.text_input(f"✍️ ระบุแบบกำหนดเอง:", value=default_text, key=f"ui_custom_{key}")
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
        session_id = uuid.uuid4().hex[:6]
        task_filename = f"bot_task_{session_id}.json"
        
        payload = {
            "type": "image_only" if is_poster_only else "scene_pipeline", 
            "image_prompt": final_img, 
            "video_prompt": final_vid, 
            "credit_mode": "Lower Priority" if "Lower" in credit else "Fast", 
            "ref_image": ref_img_path, 
            "scene_num": scene_num, 
            "is_first_scene": is_first, 
            "target_ratio": ratio,
            "task_file": task_filename
        }
        with open(task_filename, "w", encoding="utf-8") as f: json.dump(payload, f, ensure_ascii=False)
        
        st.success(f"> 📡 ส่งคำสั่งเรียบร้อย (ID: {session_id}) บอทกำลังทำงานเบื้องหลัง หน้าเว็บใช้งานต่อได้ทันที...")
        
        subprocess.Popen(["python", "-u", "test_bot.py", task_filename], env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        time.sleep(1)
        st.rerun()

# ==========================================
# 🗂️ 4. เมนูนำทาง (Sidebar) - โชว์เต็ม 10 โหมด
# ==========================================
if logo_img != "🤖": st.sidebar.image(logo_img, width=150)
st.sidebar.markdown("### 🗂️ แผงควบคุมหลัก")

app_mode = st.sidebar.radio("เลือกโหมดการทำงาน:", [
    "🏠 หน้าแรก (Dashboard)",
    "🎬 โฆษณาสินค้า (Ad Director)",
    "🍰 รีวิวร้านตัวเอง (UGC Vlogger)",
    "🎤 วิทยากร AI (AI Spokesperson)",
    "🐾 สัตว์เลี้ยงไวรัล (Viral Pet)",
    "🎭 คาแรคเตอร์สายฮา (Caricature)",
    "🎙️ ทอล์คโชว์สายปั่น (Stand-up)",
    "🕶️ ช่องคำคมสู้ชีวิต (Sigma Motivation)",
    "👻 ช่องเล่าเรื่องหลอน (Creepypasta)",
    "🕺 สายแดนซ์ชาเลนจ์ (Dance Character)",
    "🎶 ห้องอัดเสียงเพลงแปลง (Parody Music)"
])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 สถานะ API Key")
if not api_keys_list: 
    st.sidebar.error("❌ ยังไม่ได้ใส่ API Key")
else:
    for i in range(len(api_keys_list)): 
        st.sidebar.markdown(f"**Key {i+1}:** {st.session_state.key_status.get(i, '⏳')}")

# =========================================================================================
# 🏠 หน้าแรก (Dashboard)
# =========================================================================================
if app_mode == "🏠 หน้าแรก (Dashboard)":
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
    if 'ad_extra_note' not in st.session_state: st.session_state.ad_extra_note = ""
    if 'ad_video_prompt' not in st.session_state: st.session_state.ad_video_prompt = ""
    if 'ad_poster_prompt' not in st.session_state: st.session_state.ad_poster_prompt = ""
    if 'ad_poster_prompt_th' not in st.session_state: st.session_state.ad_poster_prompt_th = ""
    if 'ad_imgs' not in st.session_state: st.session_state.ad_imgs = []
    if 'ad_presenter_img' not in st.session_state: st.session_state.ad_presenter_img = []

    with st.expander("📸 0. อัปโหลดรูปภาพ (สินค้า & พรีเซนเตอร์)", expanded=True):
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            st.markdown("**📦 1. รูปสินค้า/ฉลาก (จำเป็น)**")
            up_product = st.file_uploader("ใช้อ่านส่วนผสมและดีเทล", type=['png', 'jpg'], accept_multiple_files=True, key="ad_up_prod")
            if up_product:
                st.session_state.ad_imgs = []
                os.makedirs("temp_refs", exist_ok=True)
                for img_file in up_product:
                    path = os.path.join("temp_refs", img_file.name)
                    with open(path, "wb") as f: f.write(img_file.getbuffer())
                    st.session_state.ad_imgs.append(path)
                
                st.image(up_product, width=150)
                
                if st.button("🔍 สกัดข้อมูล Ingredients", type="secondary"):
                    prompt_contents = [Image.open(img_file) for img_file in up_product]
                    prompt_contents.append("บรรยายรายละเอียด วัสดุ สี และรูปร่างสินค้าในภาพอย่างละเอียด")
                    st.session_state.ad_product_text = smart_generate(prompt_contents)
        
        with col_up2:
            st.markdown("**👤 2. รูปพรีเซนเตอร์ (ทางเลือก)**")
            up_presenter = st.file_uploader("ใช้เป็น Reference หน้าตา", type=['png', 'jpg'], accept_multiple_files=False, key="ad_up_pres")
            if up_presenter:
                st.session_state.ad_presenter_img = []
                os.makedirs("temp_refs", exist_ok=True)
                path_pres = os.path.join("temp_refs", up_presenter.name)
                with open(path_pres, "wb") as f: f.write(up_presenter.getbuffer())
                st.session_state.ad_presenter_img.append(path_pres)
                st.image(up_presenter, width=200) 

        st.session_state.ad_product_text = st.text_area("📝 ข้อมูลสินค้า:", value=st.session_state.ad_product_text, height=80)
        st.session_state.ad_extra_note = st.text_area("📌 บรีฟพิเศษ / สิ่งที่ต้องเน้น (Director's Note):", value=st.session_state.ad_extra_note, height=80, placeholder="เช่น พรีเซนเตอร์คือแมวตัวผู้ชื่อ 'บุญช่วย' นิสัยกวนๆ เรียกคนดูว่า 'นุด' ให้เน้นความคุ้มค่า...")

    tab_vid, tab_poster, tab_run = st.tabs(["🎬 1. สร้างสคริปต์วิดีโอ", "🖼️ 2. สร้างโปสเตอร์/หน้าปก", "🚀 3. รันระบบ (Handoff)"])
    
    with tab_vid:
        st.markdown("##### 🎯 ล็อกเป้าหมายให้ AI (Pre-AI Controls)")
        col_ai_dir1, col_ai_dir2 = st.columns(2)
        with col_ai_dir1:
            ai_dir_len = st.selectbox("⏱️ ล็อกความยาวคลิป:", ["🤖 ปล่อย AI คิดเอง (Free Style)", "⚡ บังคับสั้นกระแทกตา (Bumper 6 วิ)", "📱 บังคับคลิปกระแส (Shorts/Reels 15-30 วิ)", "🎬 บังคับคลิปเล่าเรื่อง (1 นาทีขึ้นไป)"], key="ai_dir_len")
        with col_ai_dir2:
            ai_dir_ratio = st.selectbox("📏 ล็อกสัดส่วนภาพ:", ["🤖 ปล่อย AI คิดเอง (Free Style)", "📱 แนวตั้ง (9:16) - เหมาะกับมือถือ", "📺 แนวนอน (16:9) - เหมาะกับ YouTube/TV", "⬛ จัตุรัส (1:1) - เหมาะกับ Facebook/IG Feed"], key="ai_dir_ratio")
        
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าอัตโนมัติ (Auto-Fill)", key="ad_vid_ai", use_container_width=True):
                if not st.session_state.ad_product_text:
                    st.warning("⚠️ กรุณาระบุหรือสกัดข้อมูลสินค้าในช่อง '📝 ข้อมูลสินค้า' ก่อนครับ")
                else:
                    with st.spinner("🧠 AI กำลังวิเคราะห์ข้อมูลทั้งหมดและจัดเตรียมผู้พากย์เสียงที่เป๊ะที่สุด..."):
                        dur_options = '["Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"]'
                        if "6 วิ" in ai_dir_len: dur_options = '["Bumper Ads (6 วิ)"]'
                        elif "15-30" in ai_dir_len: dur_options = '["Shorts/Reels (15-30 วิ)"]'
                        elif "1 นาที" in ai_dir_len: dur_options = '["มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"]'
                        
                        plat_options = '["TikTok / Shopee Video", "Facebook Reels", "YouTube In-stream", "IG Story (เน้นภาพสวย)"]'
                        if "9:16" in ai_dir_ratio: plat_options = '["TikTok / Shopee Video", "IG Story (เน้นภาพสวย)"]'
                        elif "16:9" in ai_dir_ratio: plat_options = '["YouTube In-stream"]'
                        elif "1:1" in ai_dir_ratio: plat_options = '["Facebook Reels"]'

                        context = f"สินค้า: {st.session_state.ad_product_text} | บรีฟพิเศษ: {st.session_state.ad_extra_note}"
                        prompt = f"""คุณคือผู้กำกับโฆษณามืออาชีพ วิเคราะห์ข้อมูลต่อไปนี้: "{context}"
                        แล้วทำหน้าที่ "เลือก" ตัวเลือกที่เหมาะสมที่สุดจากรายการด้านล่างนี้เท่านั้น:
                        
                        - ad_pres: ["ไม่มีพรีเซนเตอร์", "KOL / Influencer", "ผู้เชี่ยวชาญ / หมอ", "ผู้ใช้งานจริง (User)", "มาสคอตแบรนด์", "หญิงสาว", "ชายหนุ่ม", "สัตว์เลี้ยง (หมา/แมว)"]
                        - ad_voice: ["👨 ผู้ชาย (ผม/ครับ/แมนๆ)", "👩 ผู้หญิง (ฉัน/ค่ะ/สาวๆ)", "🐾 สัตว์เลี้ยงตัวผู้ (นุด/ค้าบ/ผม/กวนโอ๊ย)", "🐾 สัตว์เลี้ยงตัวเมีย (นุด/ม้าว/หนู/อ้อนๆ เสียงสอง)", "🧔 ชายสายลุย/ฮาร์ดคอร์ (พี่/ผม/โคตรสุด/ดุดัน)", "💅 ตัวแม่ / LGBTQ+ (แม่/พวกหล่อน/โฮ่งมาก/สับๆ)", "👴👵 ผู้ใหญ่/ลุงป้า (ลุง/ป้า/ลูกหลานเอ๊ย/อบอุ่น)", "👶 เด็กน้อยน่ารัก (หนู/ค้าบ/ค่า/สดใส)"]
                        - ad_tone: ["เพื่อนป้ายยา", "ตื่นเต้นขายเก่ง", "พรีเมียม / หรูหรา", "ASMR (กระซิบ)", "เล่าเรื่องน่าติดตาม (Storytelling)", "ดุดันจริงจัง", "ตลกขบขัน"]
                        - ad_target: ["วัยรุ่น Gen Z", "คนทำงาน / มนุษย์เงินเดือน", "แม่และเด็ก", "สายรักษ์สุขภาพ", "ผู้สูงอายุ"]
                        - ad_lang: ["ภาษาไทยกลาง", "อีสานมาตรฐาน (ขอนแก่น/อุดรฯ)", "อังกฤษ US Native"]
                        - ad_dur: {dur_options}
                        - ad_style: ["UGC (User Generated Content)", "Cinematic (สวยงามเหมือนภาพยนตร์)", "Vlog เที่ยว/กิน", "ซิทคอมสั้นตลกๆ"]
                        - ad_story: ["PAS (ปัญหา-ทางแก้)", "Before / After", "AIDA (ดึงดูด-สนใจ-ต้องการ-ซื้อ)", "สาธิตวิธีใช้ (How-to)"]
                        - ad_cta: ["กดตะกร้าด้านซ้ายล่าง", "ทักแชท", "แจกโค้ดส่วนลด", "คลิกลิงก์หน้าโปรไฟล์"]
                        - ad_plat: {plat_options}
                        - ad_music: ["Pop สนุกสนาน", "Epic อลังการ", "EDM (ตื่นเต้นเร้าใจ)"]
                        - ad_color: ["สดใสสว่างคลีนๆ", "พาสเทลละมุนตา", "โทนดาร์กเท่ๆ (Dark/Moody)"]
                        - ad_cam: ["ระดับสายตา (Eye Level)", "ซูมใกล้ (Macro)", "POV (มุมมองบุคคลที่ 1)"]
                        - ad_light: ["แสงธรรมชาติ (Daylight)", "แสงสตูดิโอ", "Golden Hour (แสงเย็น)"]
                        - ad_text: ["ซับไตเติ้ลคำต่อคำ", "ไฮไลท์เฉพาะคำสำคัญ", "ไม่มีข้อความ"]
                        - ad_pacing: ["ตัดฉับไว (Jump Cut)", "Beat Sync"]
                        - ad_vfx: ["ไม่มีเอฟเฟกต์ (เน้นสมจริง)", "โทนฟิล์มเก่า (Retro/VHS)"]

                        ⚠️ กฎเหล็ก (CRITICAL JSON RULES):
                        1. ห้ามเลือกคำว่า "🤖 ปล่อย AI คิดเอง" โดยเด็ดขาด ให้เลือกตัวเลือกอื่นในวงเล็บก้ามปูที่เหมาะสมแทน
                        2. ตอบกลับเป็น JSON Format เท่านั้น ตัวอย่าง: {{"ad_pres": "หญิงสาว", "ad_voice": "👩 ผู้หญิง (ฉัน/ค่ะ/สาวๆ)"}}
                        """
                        try:
                            res = smart_generate(prompt)
                            json_str = re.search(r'\{.*\}', res, re.DOTALL)
                            if json_str:
                                ai_config = json.loads(json_str.group(0))
                                for k, v in ai_config.items():
                                    if isinstance(v, list) and len(v) > 0: 
                                        v = str(v[0])
                                    elif isinstance(v, str): 
                                        v = re.sub(r"^\[['\"]|['\"]\]$", "", v.strip())
                                    st.session_state[k] = v
                                st.rerun()
                            else:
                                st.error("❌ รูปแบบ JSON ไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {e}")

        with col_res:
            if st.button("🔄 รีเซ็ตการตั้งค่าวิดีโอ (Reset)", key="ad_vid_res", use_container_width=True):
                st.session_state.ad_video_prompt = ""
                vid_keys = ["ad_pres", "ad_voice", "ad_tone", "ad_target", "ad_lang", "ad_dur", "ad_style", "ad_story", "ad_cta", "ad_plat", "ad_music", "ad_color", "ad_cam", "ad_light", "ad_text", "ad_pacing", "ad_vfx"]
                for k in vid_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"ui_widget_{k}" in st.session_state: del st.session_state[f"ui_widget_{k}"]
                    if f"ui_custom_{k}" in st.session_state: del st.session_state[f"ui_custom_{k}"]
                st.rerun()
                
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 👤 พรีเซนเตอร์:", ["🤖 ปล่อย AI คิดเอง", "ไม่มีพรีเซนเตอร์", "KOL / Influencer", "ผู้เชี่ยวชาญ / หมอ", "ผู้ใช้งานจริง (User)", "มาสคอตแบรนด์", "หญิงสาว", "ชายหนุ่ม", "สัตว์เลี้ยง (หมา/แมว)"], "ad_pres", "ผู้เชี่ยวชาญ=อาหารเสริม/สกินแคร์, ผู้ใช้งานจริง=ของใช้ทั่วไป")
            render_custom_select("2. 🚻 เพศเสียงพากย์:", ["🤖 ปล่อย AI คิดเอง", "👨 ผู้ชาย (ผม/ครับ/แมนๆ)", "👩 ผู้หญิง (ฉัน/ค่ะ/สาวๆ)", "🐾 สัตว์เลี้ยงตัวผู้ (นุด/ค้าบ/ผม/กวนโอ๊ย)", "🐾 สัตว์เลี้ยงตัวเมีย (นุด/ม้าว/หนู/อ้อนๆ เสียงสอง)", "🧔 ชายสายลุย/ฮาร์ดคอร์ (พี่/ผม/โคตรสุด/ดุดัน)", "💅 ตัวแม่ / LGBTQ+ (แม่/พวกหล่อน/โฮ่งมาก/สับๆ)", "👴👵 ผู้ใหญ่/ลุงป้า (ลุง/ป้า/ลูกหลานเอ๊ย/อบอุ่น)", "👶 เด็กน้อยน่ารัก (หนู/ค้าบ/ค่า/สดใส)"], "ad_voice", "สำคัญมาก: ช่วยล็อกเพศและสรรพนามของเสียง (แก้ปัญหาแมวตัวผู้เสียงสาว)")
            render_custom_select("3. 🗣️ น้ำเสียง (Tone):", ["🤖 ปล่อย AI คิดเอง", "เพื่อนป้ายยา", "ตื่นเต้นขายเก่ง", "พรีเมียม / หรูหรา", "ASMR (กระซิบ)", "เล่าเรื่องน่าติดตาม (Storytelling)", "ดุดันจริงจัง", "ตลกขบขัน"], "ad_tone", "ASMR=สินค้าของกิน/สกินแคร์, ตลก=เพิ่มการแชร์")
            render_custom_select("4. 🎯 กลุ่มเป้าหมาย:", ["🤖 ปล่อย AI คิดเอง", "วัยรุ่น Gen Z", "คนทำงาน / มนุษย์เงินเดือน", "แม่และเด็ก", "สายรักษ์สุขภาพ", "ผู้สูงอายุ"], "ad_target", "ช่วยให้ AI เลือกใช้ศัพท์ให้ตรงกับวัยของลูกค้า")
            render_custom_select("5. 🌐 ภาษาและสำเนียง:", ["🤖 ปล่อย AI คิดเอง", "ภาษาไทยกลาง", "อีสานมาตรฐาน (ขอนแก่น/อุดรฯ)", "อีสานโคราช", "อีสานใต้ (สุรินทร์/บุรีรัมย์)", "ใต้ลึก (นครศรีธรรมราช)", "ใต้ตอนล่าง (สงขลา/หาดใหญ่)", "ใต้ฝั่งอันดามัน (ภูเก็ต)", "เหนือล้านนา (เชียงใหม่)", "เหนือตะวันออก (แพร่/น่าน)", "กลางเหน่อ (สุพรรณบุรี)", "ตะวันออก (ระยอง/จันทบุรี)", "อังกฤษ US Native", "อังกฤษ UK (บริติช)", "อังกฤษ Aussie (ออสเตรเลีย)"], "ad_lang", "เลือกภาษาให้ตรงกับถิ่นฐานกลุ่มเป้าหมายเพื่อความเนียน")
            render_custom_select("6. ⏳ ความยาวคลิป:", ["🤖 ปล่อย AI คิดเอง", "Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"], "ad_dur", "Shorts/Reels=ดันยอดวิวการเข้าถึง, Long-form=เน้นข้อมูลแน่น")
            render_custom_select("7. 🎥 สไตล์โฆษณา:", ["🤖 ปล่อย AI คิดเอง", "UGC (User Generated Content)", "Cinematic (สวยงามเหมือนภาพยนตร์)", "Vlog เที่ยว/กิน", "ซิทคอมสั้นตลกๆ", "Stop Motion", "3D Animation"], "ad_style", "UGC=เน้นความจริงใจ/รีวิว, Cinematic=สร้างแบรนด์หรู")
        with c2:
            render_custom_select("8. 📖 การเล่าเรื่อง:", ["🤖 ปล่อย AI คิดเอง", "PAS (ปัญหา-ทางแก้)", "Before / After", "AIDA (ดึงดูด-สนใจ-ต้องการ-ซื้อ)", "ขยี้ Pain Point", "สาธิตวิธีใช้ (How-to)"], "ad_story", "PAS และ Pain Point เหมาะกับสินค้าแก้ปัญหา (สิว/ปวดเมื่อย)")
            render_custom_select("9. 👉 ปิดการขาย (CTA):", ["🤖 ปล่อย AI คิดเอง", "กดตะกร้าด้านซ้ายล่าง", "ทักแชท", "แจกโค้ดส่วนลด", "ให้รีบซื้อก่อนหมด (FOMO)", "คลิกลิงก์หน้าโปรไฟล์", "สมัครสมาชิก"], "ad_cta", "FOMO=กระตุ้นการตัดสินใจทันที")
            render_custom_select("10. 📱 แพลตฟอร์ม:", ["🤖 ปล่อย AI คิดเอง", "TikTok / Shopee Video", "Facebook Reels", "YouTube In-stream", "IG Story (เน้นภาพสวย)"], "ad_plat", "กำหนดสัดส่วนภาพและพฤติกรรมคนดูบนแพลตฟอร์ม")
            render_custom_select("11. 🎵 ดนตรี:", ["🤖 ปล่อย AI คิดเอง", "Pop สนุกสนาน", "Epic อลังการ", "Lofi (ชิลๆสบายๆ)", "EDM (ตื่นเต้นเร้าใจ)", "ดนตรีประกอบระทึกขวัญ", "ไม่มีเพลงเน้นเสียงพูด"], "ad_music", "Lofi=คลิป ASMR/สโลว์ไลฟ์, EDM=โปรโมชั่น/ของเซลล์")
            render_custom_select("12. 🎨 โทนสี:", ["🤖 ปล่อย AI คิดเอง", "สดใสสว่างคลีนๆ", "พาสเทลละมุนตา", "โทนดาร์กเท่ๆ (Dark/Moody)", "ขาวดำคลาสสิก", "นีออนไซเบอร์พังก์"], "ad_color", "พาสเทล=บิวตี้, นีออน/ดาร์ก=แก็ดเจ็ต/เกมมิ่ง")
        with c3:
            render_custom_select("13. 🎥 มุมกล้อง:", ["🤖 ปล่อย AI คิดเอง", "ระดับสายตา (Eye Level)", "ซูมใกล้ (Macro/Close-up)", "POV (มุมมองบุคคลที่ 1)", "มุมสูง (Drone/Top-down)", "มุมเอียง (Dutch Angle)"], "ad_cam", "POV=ทำให้คนดูรู้สึกเหมือนใช้งานเอง, มุมเอียง=ฉากแอคชั่น/ตื่นเต้น")
            render_custom_select("14. 💡 แสงและบรรยากาศ:", ["🤖 ปล่อย AI คิดเอง", "แสงธรรมชาติ (Daylight)", "แสงสตูดิโอ", "Golden Hour (แสงเย็น/พระอาทิตย์ตก)", "Cinematic Rim Light (แสงขอบ)", "แสงจัดจ้านสไตล์ป๊อป"], "ad_light", "Golden hour=ฟีลลิ่งอบอุ่น/สกินแคร์")
            render_custom_select("15. ✍️ ข้อความบนจอ:", ["🤖 ปล่อย AI คิดเอง", "โปรโมชั่นพิเศษ/ราคา", "ซับไตเติ้ลคำต่อคำ", "ไฮไลท์เฉพาะคำสำคัญ", "ป้ายราคาเด้งกระแทกตา", "ไม่มีข้อความ"], "ad_text", "TikTok/Reels ขาดไม่ได้คือซับไตเติ้ลเพื่อหยุดนิ้วคนดู")
            render_custom_select("16. 🎞️ จังหวะการตัดต่อ:", ["🤖 ปล่อย AI คิดเอง", "ตัดฉับไว (Jump Cut)", "สมูทและสโลว์โมชั่น", "ตัดตามจังหวะเพลง (Beat Sync)", "Long Take (แช่กล้องนาน)"], "ad_pacing", "Jump cut=วัยรุ่น/สั้นกระชับ, สโลว์โมชั่น=โชว์ดีเทล/สินค้าหรู")
            render_custom_select("17. ✨ เอฟเฟกต์ (VFX):", ["🤖 ปล่อย AI คิดเอง", "ไม่มีเอฟเฟกต์ (เน้นสมจริง)", "โทนฟิล์มเก่า (Retro/VHS)", "เทคนิคกลิทช์ (Cyberpunk Glitch)", "แสงแฟลร์ (Lens Flare)"], "ad_vfx", "VHS=วินเทจ/Y2K, Glitch=สินค้าเทคโนโลยี/แฟชั่น")

        if st.button("🚀 เริ่มเขียนสคริปต์วิดีโอ & แคปชั่นป้ายยา", type="primary", use_container_width=True):
            voice_persona = st.session_state.get('ad_voice')
            if voice_persona == "🤖 ปล่อย AI คิดเอง":
                voice_instruction = "ให้พิจารณา 'พรีเซนเตอร์' และสินค้าเพื่อเลือกสรรพนามที่เหมาะสม"
            else:
                voice_instruction = f"บังคับล็อกเพศและสรรพนามเสียงพากย์ตามที่กำหนดไว้เด็ดขาด: {voice_persona}"

            prompt = f"""คุณคือผู้กำกับโฆษณาระดับโลก (Commercial Director) เขียนสคริปต์โฆษณาสินค้าแบบแบ่งฉาก (ฉากละ 8 วินาที) อ้างอิงจากการตั้งค่า:
สินค้า: {st.session_state.ad_product_text}
📌 บรีฟพิเศษ/สิ่งที่ต้องเน้น: {st.session_state.ad_extra_note}
ผู้พากย์เสียง/สรรพนาม (Hard Constraint): {voice_instruction}
พรีเซนเตอร์: {st.session_state.get('ad_pres')}
เสียง (Tone): {st.session_state.get('ad_tone')}
เป้าหมาย: {st.session_state.get('ad_target')}
ภาษา: {st.session_state.get('ad_lang')}
ความยาว: {st.session_state.get('ad_dur')}
สไตล์: {st.session_state.get('ad_style')}
เล่าเรื่อง: {st.session_state.get('ad_story')}
CTA: {st.session_state.get('ad_cta')}
แพลตฟอร์ม: {st.session_state.get('ad_plat')}
เพลง: {st.session_state.get('ad_music')}
โทนสี: {st.session_state.get('ad_color')}
มุมกล้อง: {st.session_state.get('ad_cam')}
แสง: {st.session_state.get('ad_light')}
ข้อความบนจอ: {st.session_state.get('ad_text')}
การตัดต่อ: {st.session_state.get('ad_pacing')}
VFX: {st.session_state.get('ad_vfx')}

⚠️ กฎการตั้งค่าอัตโนมัติ (AI Auto-Decision): หากหัวข้อใดถูกตั้งค่าเป็น "🤖 ปล่อย AI คิดเอง" ให้คุณวิเคราะห์จาก 'สินค้า' และ 'บรีฟพิเศษ' แล้วกำหนดรายละเอียดนั้นขึ้นมาเองให้เหมาะสมและปังที่สุด ห้ามพิมพ์คำว่า "ปล่อย AI คิดเอง" ลงในสคริปต์หรือ Prompt วาดภาพเด็ดขาด

⚠️ กฎเหล็กเรื่องสรรพนามและน้ำเสียง (สำคัญมาก Must Follow):
- พิจารณา 'ผู้พากย์เสียง/สรรพนาม' ที่กำหนดไว้ และนำข้อมูลใน '📌 บรีฟพิเศษ' ไปสร้างบทพูดที่เนียนตา หากระบุว่าเป็น 'สัตว์เลี้ยงตัวผู้' และบรีฟพิเศษสั่งให้ใช้คำว่า 'นุด'/'ผม' หรือระบุสรรพนามอื่น ห้าม AI เผลอใช้คำว่า แก, ดีย์, เริ่ด, ค่ะ, สิคะ เด็ดขาด

🎬 ฉากที่ 1: เปิดตัวดึงดูดสายตา (The Hook - 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายภาพรวมว่าเกิดอะไรขึ้น
* ข้อความบนจอ (Text on Screen): (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (เขียนตามสรรพนามเพศและบรีฟพิเศษที่กำหนดอย่างเคร่งครัด)
* Prompt สร้างภาพนิ่ง: (ภาษาอังกฤษ - สำหรับ Nano Banana 2) อธิบายหน้าตาพรีเซนเตอร์, เสื้อผ้า, สถานที่, แสง, โทนสี และมุมกล้องตั้งต้นอย่างละเอียดที่สุด เพื่อใช้เป็นภาพอ้างอิง (เขียนแบบบรรทัดเดียวห้ามขึ้นบรรทัดใหม่)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ - สำหรับ Veo 3.1) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ โดยระบุจังหวะตัดกล้อง (เช่น 0-4s: [แอคชั่น], 4-8s: Quick cut to [แอคชั่นใหม่]) และลงท้ายด้วยคำว่า "Audio: [เสียง SFX/ดนตรี]"

🎬 ฉากที่ 2, 3, 4... : ต่อเนื่องเนื้อหา (Extend Scene - ฉากละ 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายแอคชั่นที่สานต่อจากฉากที่แล้ว เพื่อเดินเรื่องไปสู่การปิดการขาย
* ข้อความบนจอ (Text on Screen): (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (ขยี้ Pain Point หรือ Call to Action ตามสรรพนามเพศ)
* (ห้ามเขียน Prompt สร้างภาพนิ่งในฉากที่ 2 เป็นต้นไปเด็ดขาด)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ เริ่มด้วย "Continuing from the previous frame..." ระบุจังหวะตัดกล้อง และลงท้ายด้วย "Audio: [เสียงประกอบที่สอดคล้อง]"

📱 ส่วนท้ายสุด: แคปชั่นป้ายยา 3 แพลตฟอร์ม
- TikTok: เน้นฮุกกระแส + แฮชแท็กมาแรง (ความยาวปกติ)
- Facebook (Shopee Affiliate): เน้นสตอรี่เทลลิ่งโน้มน้าวให้กดลิงก์ (ความยาวปกติ)
- Shopee Video/Feed: ฮาร์ดเซลล์กระชับ *(กฎเหล็ก: ห้ามเกิน 150 ตัวอักษรรวมแฮชแท็ก)*
"""
            st.session_state.ad_video_prompt = smart_generate(prompt)

        if st.session_state.ad_video_prompt: st.text_area("📄 สคริปต์วิดีโอฉบับเต็ม:", value=st.session_state.ad_video_prompt, height=400, key="ad_vid_text_output")

    with tab_poster:
        st.markdown("##### 🎯 ล็อกเป้าหมายให้ AI (Pre-AI Controls - Poster)")
        ai_dir_ratio_pos = st.selectbox("📏 ล็อกสัดส่วนภาพหน้าปก (Aspect Ratio):", ["🤖 ปล่อย AI คิดเอง", "16:9 (YouTube/TV แนวนอน)", "4:3 (แนวนอนมาตรฐาน)", "1:1 (Facebook/IG จัตุรัส)", "3:4 (Portrait แมนยง)", "9:16 (TikTok/Reels แนวตั้ง)"], key="ai_dir_ratio_pos")

        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าโปสเตอร์อัตโนมัติ", key="pos_ai", use_container_width=True):
                if not st.session_state.ad_product_text:
                    st.warning("⚠️ กรุณาระบุหรือสกัดข้อมูลสินค้าในช่อง '📝 ข้อมูลสินค้า' ก่อนครับ")
                else:
                    with st.spinner("🧠 AI กำลังสแกนข้อมูลสินค้า รูปภาพ และบรีฟพิเศษ เพื่อออกแบบโปสเตอร์สุดปัง..."):
                        ratio_constraint_pos = ""
                        if "16:9" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกเลย์เอาต์ยิงแอด (ad_pos_ad_comp) ให้เหมาะสมกับแนวนอนกว้าง 16:9'
                        elif "1:1" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกเลย์เอาต์ยิงแอด (ad_pos_ad_comp) ให้เหมาะสมกับจัตุรัส 1:1 เน้นจุดสนใจตรงกลาง'
                        elif "9:16" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกเลย์เอาต์ยิงแอด (ad_pos_ad_comp) และตำแหน่งข้อความให้เหมาะสมกับแนวตั้ง 9:16 หลบปุ่ม Safe Zone มือถือ'

                        context = f"สินค้า: {st.session_state.ad_product_text} | บรีฟพิเศษ: {st.session_state.ad_extra_note}"
                        
                        prompt_contents = []
                        if st.session_state.ad_imgs:
                            prompt_contents = [Image.open(img_file) for img_file in st.session_state.ad_imgs]
                        
                        prompt_text = f"""วิเคราะห์ข้อมูล: "{context}" และภาพเหล่านี้
                        แล้วทำหน้าที่ "เลือก" ตัวเลือกที่เหมาะสมที่สุดจากรายการด้านล่างนี้เท่านั้น:
                        
                        - ad_pos_style: ["Vlog / UGC Review Style (เน้นความเรียลปังๆ)", "Social Media Clickbait Ad (หน้าปกไวรัลดึงดูดตา)", "High-end E-commerce Catalog (หรูหราแคตตาล็อก)", "Hyper-Realistic 3D Render (3D สมจริง)", "Cyberpunk Neon (นีออนล้ำสมัย)"]
                        - ad_pos_color: ["สดใสอมส้มกระตุ้นความหิว (Warm & Appetizing)", "โทนแดง-ทอง ดุดันพรีเมียม (Red & Gold Premium)", "จัดจ้านตัดกัน (Vibrant Contrast)", "สว่างสดใสคลีนๆ (Clean & Bright)", "โทนดาร์กเท่ๆ (Dark Moody)"]
                        - ad_pos_cam: ["ระดับสายตาเห็นคนและสินค้า (Eye-level portrait)", "ซูมใกล้เนื้ออาหาร/สินค้าฉ่ำๆ (Macro Close-up)", "มุมมองแทนสายตาตอนกิน (First-Person POV)", "มุมสูงถ่ายเจาะเต็มโต๊ะ (Top-down Flat Lay)"]
                        - ad_pos_light: ["แสงธรรมชาติริมหน้าต่าง (Soft Window Light)", "สาดแฟลชตรงๆ สไตล์Y2K (Hard Flash)", "นีออนสตรีทฟู้ดกลางคืน (Street Neon Light)", "Golden Hour (แสงเย็นอบอุ่น)"]
                        - ad_pos_display: ["พรีเซนเตอร์ถือและยิ้มหวาน (Presenter holding and smiling)", "พรีเซนเตอร์ถือสินค้าข้างแก้ม (Hand holding near face)", "น้ำสาดกระจายความสดชื่น (Liquid Splash)", "ลอยอยู่กลางอากาศแบบมีมิติ (Floating)", "วัตถุดิบกระจายรอบๆ (Exploding Ingredients)"]
                        - ad_pos_ad_comp: ["คนอยู่ซ้าย-ข้อความอยู่ขวา (Presenter Left, Text Right)", "สินค้าไซส์ยักษ์อลังการ (Oversized Product Focus)", "เลย์เอาต์แบ่งครึ่ง บน-ล่าง (Split Top-Bottom)", "กฎสามส่วน (Rule of Thirds)"]
                        - ad_pos_graphics: ["ประกายแสงวิบวับและออร่า (Sparkles &Glowing Aura)", "สายฟ้าและพลังงาน (Lightning Energy FX)", "ลูกศรนีออนชี้ไปที่สินค้า (Glowing Arrow Pointer)", "เส้นสปีดไลน์พุ่งเข้าหาตรงกลาง (Action Speed Lines)"]
                        - ad_pos_bg: ["ฉากเบลอเน้นพรีเซนเตอร์ (Blurred Bokeh)", "ฉากครัว (Kitchen Area)", "สวนหลังบ้าน (Backyard Garden)", "ร้านสตรีทฟู้ด (Street Food Stall)", "สตูดิโอสีพื้น (Solid Studio Color)"]
                        - ad_pos_typography: ["ฟอนต์ตัวหนากระแทกตาแบบ Youtuber (Bold with Stroke)", "ฟอนต์ลายมือดูเป็นมิตร (Friendly Handwritten)", "ฟอนต์คาเฟ่มินิมอล (Minimalist Sans-serif)"]
                        - ad_pos_typo_effect: ["ข้อความเรืองแสงมีขอบนีออน (Neon Glowing Text)", "ป้ายราคาห้อยเชือก/ป้ายแท็ก 3D (3D Hanging Price Tag)", "ข้อความตัวหนาซ้อนเลเยอร์ (Layered Bold)", "ไม่มีเอฟเฟกต์ (Clean)"]
                        - ad_pos_badge_style: ["ป้าย 3D เด้งทะลุจอ (3D Pop-up Badge)", "ป้ายนีออนสว่างวาบ (Glowing Neon Sign)", "ป้ายวงกลมสไตล์มินิมอล (Minimalist Circle Sticker)", "ริบบิ้นพาดมุมภาพ (Corner Ribbon Tag)"]
                        - ad_pos_trust: ["ป้ายรีวิว 5 ดาว (5-Star Rating)", "โลโก้แอปส้ม/แอปตะกร้าตะกร้าตะกร้า (E-com Platform โลโก้)", "ป้ายยอดขาย 100k+ (Top Seller Badge)", "ป้ายรับประกัน/โล่ทอง (Warranty Shield)", "ไม่ใส่ป้าย"]
                        - ad_pos_text_pos: ["Safe Zone แนวตั้ง (9:16 หลบปุ่ม)", "บนซ้าย (Top-Left)", "บนขวา (Top-Right)", "พาดกลางภาพ (Center Bold)"]
                        - ad_pos_main_headline: ["โปรโมชั่นพิเศษ/Sale", "Flash Sale สุดช็อก", "อร่อยแสงออกปาก!", "ร้านลับต้องลอง!", "ให้เยอะจนจุก!", "ชื่อสินค้าโดดๆ", "ไม่มีข้อความ"]
                        - ad_pos_sub_text: ["ส่งฟรี!", "ซื้อ 1 แถม 1", "ราคาหลักสิบ", "คุ้มมากแม่!", "คิวยาวมาก", "รีวิว 5 ดาว", "ไม่มีข้อความ"]

                        ⚠️ กฎพิเศษในการตั้งค่า:
                        {ratio_constraint_pos}

                        ⚠️ กฎเหล็ก (CRITICAL JSON RULES):
                        1. ห้ามเลือกคำว่า "🤖 ปล่อย AI คิดเอง" โดยเด็ดขาด ให้เลือกตัวเลือกอื่นในวงเล็บก้ามปูที่เหมาะสมแทน
                        2. ตอบกลับเป็น JSON Format เท่านั้น ตัวอย่าง: {{"ad_pos_style": "Vlog / UGC Review Style (เน้นความเรียลปังๆ)"}}
                        """
                        prompt_contents.append(prompt_text)
                        
                        try:
                            res = smart_generate(prompt_contents)
                            json_str = re.search(r'\{.*\}', res, re.DOTALL)
                            if json_str:
                                ai_config = json.loads(json_str.group(0))
                                for k, v in ai_config.items():
                                    if isinstance(v, list) and len(v) > 0: 
                                        v = str(v[0])
                                    elif isinstance(v, str): 
                                        v = re.sub(r"^\[['\"]|['\"]\]$", "", v.strip())
                                    st.session_state[k] = v
                                st.rerun()
                            else:
                                st.error("❌ รูปแบบ JSON ไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {e}")

        with col_res:
            if st.button("🔄 รีเซ็ตการตั้งค่าโปสเตอร์", key="pos_res", use_container_width=True):
                st.session_state.ad_poster_prompt = ""
                st.session_state.ad_poster_prompt_th = ""
                pos_keys = ["ad_pos_style", "ad_pos_color", "ad_pos_cam", "ad_pos_light", "ad_pos_display", "ad_pos_ad_comp", "ad_pos_graphics", "ad_pos_bg", "ad_pos_typography", "ad_pos_typo_effect", "ad_pos_badge_style", "ad_pos_trust", "ad_pos_text_pos", "ad_pos_main_headline", "ad_pos_sub_text"]
                for k in pos_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"ui_widget_{k}" in st.session_state: del st.session_state[f"ui_widget_{k}"]
                    if f"ui_custom_{k}" in st.session_state: del st.session_state[f"ui_custom_{k}"]
                st.rerun()

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_custom_select("1. 🎨 สไตล์ภาพ (Style):", ["🤖 ปล่อย AI คิดเอง", "Vlog / UGC Review Style (เน้นความเรียลปังๆ)", "Social Media Clickbait Ad (หน้าปกไวรัลดึงดูดตา)", "High-end E-commerce Catalog (หรูหราแคตตาล็อก)", "Hyper-Realistic 3D Render (3D สมจริง)", "Cyberpunk Neon (นีออนล้ำสมัย)"], "ad_pos_style", "UGC Style = เน้นความจริงใจ/รีวิว, Cinematic = สร้างแบรนด์หรู")
            render_custom_select("2. 🌈 โทนสี (Color Grading):", ["🤖 ปล่อย AI คิดเอง", "สดใสอมส้มกระตุ้นความหิว (Warm & Appetizing)", "โทนแดง-ทอง ดุดันพรีเมียม (Red & Gold Premium)", "จัดจ้านตัดกัน (Vibrant Contrast)", "สว่างสดใสคลีนๆ (Clean & Bright)", "โทนดาร์กเท่ๆ (Dark Moody)"], "ad_pos_color", "โทนอมส้ม/จัดจ้าน = กระตุ้นความหิวได้ดีที่สุด")
            render_custom_select("3. 📸 มุมกล้อง (Camera Angle):", ["🤖 ปล่อย AI คิดเอง", "ระดับสายตาเห็นคนและสินค้า (Eye-level portrait)", "ซูมใกล้เนื้ออาหาร/สินค้าฉ่ำๆ (Macro Close-up)", "มุมมองแทนสายตาตอนกิน (First-Person POV)", "มุมสูงถ่ายเจาะเต็มโต๊ะ (Top-down Flat Lay)"], "ad_pos_cam", "Macro Close-up = โชว์ความน่ากินของอาหาร/เนื้อสกินแคร์")
            render_custom_select("4. 💡 แสงและบรรยากาศ:", ["🤖 ปล่อย AI คิดเอง", "แสงธรรมชาติริมหน้าต่าง (Soft Window Light)", "สาดแฟลชตรงๆ สไตล์Y2K (Hard Flash)", "นีออนสตรีทฟู้ดกลางคืน (Street Neon Light)", "Golden Hour (แสงเย็นอบอุ่น)"], "ad_pos_light", "Hard Flash = กำลังฮิตในวัยรุ่น Y2K/สตรีทฟู้ด")
        with c2:
            render_custom_select("5. 📦 การนำเสนอสินค้า (Display):", ["🤖 ปล่อย AI คิดเอง", "พรีเซนเตอร์ถือและยิ้มหวาน (Presenter holding and smiling)", "พรีเซนเตอร์ถือสินค้าข้างแก้ม (Hand holding near face)", "น้ำสาดกระจายความสดชื่น (Liquid Splash)", "ลอยอยู่กลางอากาศแบบมีมิติ (Floating)", "วัตถุดิบกระจายรอบๆ (Exploding Ingredients)"], "ad_pos_display", " water splash = สกินแคร์/เครื่องดื่ม, Exploding = โชว์ไส้ขนม")
            render_custom_select("6. 📐 เลย์เอาต์ยิงแอด:", ["🤖 ปล่อย AI คิดเอง", "คนอยู่ซ้าย-ข้อความอยู่ขวา (Presenter Left, Text Right)", "สินค้าไซส์ยักษ์อลังการ (Oversized Product Focus)", "เลย์เอาต์แบ่งครึ่ง บน-ล่าง (Split Top-Bottom)", "กฎสามส่วน (Rule of Thirds)"], "ad_pos_ad_comp", "คนอยู่ซ้าย-ข้อความขวา = อ่านง่ายสุดบนมือถือ")
            render_custom_select("7. ✨ กราฟิก/VFX:", ["🤖 ปล่อย AI คิดเอง", "ประกายแสงวิบวับและออร่า (Sparkles &Glowing Aura)", "สายฟ้าและพลังงาน (Lightning Energy FX)", "ลูกศรนีออนชี้ไปที่สินค้า (Glowing Arrow Pointer)", "เส้นสปีดไลน์พุ่งเข้าหาตรงกลาง (Action Speed Lines)"], "ad_pos_graphics", "ลูกศร/เส้นนำสายตา = บังคับคนดูให้มองจุดสำคัญ")
            render_custom_select("8. 🖼️ พื้นหลัง (Background):", ["🤖 ปล่อย AI คิดเอง", "ฉากเบลอเน้นพรีเซนเตอร์ (Blurred Bokeh)", "ฉากครัว (Kitchen Area)", "สวนหลังบ้าน (Backyard Garden)", "ร้านสตรีทฟู้ด (Street Food Stall)", "สตูดิโอสีพื้น (Solid Studio Color)"], "ad_pos_bg", "ฉากหลังที่สอดคล้องกับสินค้าช่วยเพิ่มความเรียล")
        with c3:
            render_custom_select("9. 🔠 สไตล์ฟอนต์ (Typography):", ["🤖 ปล่อย AI คิดเอง", "ฟอนต์ตัวหนากระแทกตาแบบ Youtuber (Bold with Stroke)", "ฟอนต์ลายมือดูเป็น มิตร (Friendly Handwritten)", "ฟอนต์คาเฟ่มินิมอล (Clean Sans-serif)", "ฟอนต์รายการทีวี (TV Show Variety)"], "ad_pos_typography", " Bold with Stroke = อ่านง่ายสุดบนมือถือ ยอดนิยมบน TikTok/Shopee")
            render_custom_select("10. 💅 เอฟเฟกต์ฟอนต์:", ["🤖 ปล่อย AI คิดเอง", "ข้อความเรืองแสงมีขอบนีออน (Neon Glowing Text)", "ป้ายราคาห้อยเชือก/ป้ายแท็ก 3D (3D Hanging Price Tag)", "ข้อความตัวหนาซ้อนเลเยอร์ (Layered Bold)", "ไม่มีเอฟเฟกต์ (Clean)"], "ad_pos_typo_effect", "3D Price Tag = เหมาะกับโปรแรงๆ, Neon Glowing = ข้อความลอยเด่น")
            render_custom_select("11. 📌 ตำแหน่งข้อความ:", ["🤖 ปล่อย AI คิดเอง", "Safe Zone แนวตั้ง (9:16 หลบปุ่ม)", "บนซ้าย (Top-Left)", "บนขวา (Top-Right)", "พาดกลางภาพ (Center Bold)"], "ad_pos_text_pos", "Safe Zone = สำหรับ 9:16 แนวตั้ง หลบปุ่ม Like/Share TikTok")
            render_custom_select("12. 🏞️ องค์ประกอบภาพ:", ["🤖 ปล่อย AI คิดเอง", "กฎสามส่วน (Rule of Thirds)", "สมมาตรตรงกลางเป๊ะ (Symmetrical)", "สไตล์หน้าปกนิตยสาร (Magazine Layout)"], "ad_pos_comp", "Symmetrical = สินค้าเด่นเด้งขึ้นมาทันที")
        with c4:
            render_custom_select("13. 🛡️ ป้ายน่าเชื่อถือ (Trust):", ["🤖 ปล่อย AI คิดเอง", "ป้ายรีวิว 5 ดาว (5-Star Rating)", "โลโก้แอปส้ม/แอปตะกร้าตะกร้าตะกร้า (E-com Platform โลโก้)", "ป้ายยอดขาย 100k+ (Top Seller Badge)", "ป้ายรับประกัน/โล่ทอง (Warranty Shield)", "ไม่ใส่ป้าย"], "ad_pos_trust", "5 ดาว = สร้างความมั่นใจ, ตะกร้า = เร่งให้กดซื้อ")
            render_custom_select("14. 📢 สไตล์ป้ายโปร (Promo Badge):", ["🤖 ปล่อย AI คิดเอง", "ป้าย 3D เด้งทะลุจอ (3D Pop-up Badge)", "ป้ายนีออนสว่างวาบ (Glowing Neon Sign)", "ป้ายวงกลมสไตล์มินิมอล (Minimalist Circle Sticker)", "ริบบิ้นพาดมุมภาพ (Corner Ribbon Tag)"], "ad_pos_badge_style", "3D Badge = ฮาร์ดเซลล์ดุดัน")
            render_custom_select("15. 📣 พาดหัวหลัก (Headline):", ["🤖 ปล่อย AI คิดเอง", "โปรโมชั่นพิเศษ/Sale", "Flash Sale สุดช็อก", "อร่อยแสงออกปาก!", "ร้านลับต้องลอง!", "ให้เยอะจนจุก!", "ชื่อสินค้าโดดๆ", "ไม่มีข้อความ"], "ad_pos_main_headline", "คำใหญ่เด่นสุด กระแทกตา AI จะเรนเดอร์ได้แม่นยำกว่าประโยคยาวๆ")
            render_custom_select("16. 🏷️ ป้ายโปร/ราคา (Sub-text):", ["🤖 ปล่อย AI คิดเอง", "ส่งฟรี!", "ซื้อ 1 แถม 1", "ราคาหลักสิบ", "คุ้มมากแม่!", "คิวยาวมาก", "รีวิว 5 ดาว", "ไม่มีข้อความ"], "ad_pos_sub_text", "ข้อความดึงดูดใจเพิ่มเติม หรือเว้นว่างได้ถ้าไม่ต้องการ")
        
        if st.button("🚀 เริ่มสร้าง Prompt โปสเตอร์ (Nano Banana 2)", type="primary", use_container_width=True):
            with st.spinner("🧠 AI กำลังแต่ง Prompt และแยกหน้าจอแปลภาษา..."):
                prompt = f"""คุณคือนักเขียน Prompt ระดับโลกสำหรับ AI สร้างภาพ 'Nano Banana 2'

ข้อมูลสำหรับการสร้างโฆษณาฉบับ Hard-Sell ยุคใหม่:
- บริบทสินค้า & บรีฟพิเศษ: {st.session_state.ad_product_text} | {st.session_state.ad_extra_note}
- สไตล์ปก: {st.session_state.get('ad_pos_style')}
- โทนสี & Vibe: {st.session_state.get('ad_pos_color')}
- มุมกล้อง: {st.session_state.get('ad_pos_cam')}
- แสงเงา: {st.session_state.get('ad_pos_light')}
- ฉากหลัง: {st.session_state.get('ad_pos_bg')}
- การจัดนำเสนอสินค้า (Interaction): {st.session_state.get('ad_pos_display')}
- กราฟิกนำสายตา/VFX: {st.session_state.get('ad_pos_graphics')}
- เลย์เอาต์เฉพาะทางโฆษณา (Composition): {st.session_state.get('ad_pos_ad_comp')}
- สไตล์ฟอนต์ (Typography): {st.session_state.get('ad_pos_typography')}
- เอฟเฟกต์ฟอนต์: {st.session_state.get('ad_pos_typo_effect')}
- ป้ายความน่าเชื่อถือ (Trust Badge): {st.session_state.get('ad_pos_trust')}
- สไตล์ป้ายโปร (Promo Badge): {st.session_state.get('ad_pos_badge_style')}
- ตำแหน่งข้อความ (Text Placement): {st.session_state.get('ad_pos_text_pos')}
- พาดหัวหลัก: "{st.session_state.get('ad_pos_main_headline')}"
- ป้ายโปร/ราคา: "{st.session_state.get('ad_pos_sub_text')}"

⚠️ กฎการตั้งค่าอัตโนมัติ (AI Auto-Decision): หากตัวเลือกใดถูกระบุว่า "🤖 ปล่อย AI คิดเอง" ให้คุณทำหน้าที่เป็น Art Director เลือกสไตล์ แสง สี หรือเลย์เอาต์ที่เหมาะสมที่สุดกับสินค้านั้นๆ แทนคำว่า "ปล่อย AI คิดเอง" ลงใน Prompt ภาษาอังกฤษ ห้ามคัดลอกคำว่า "ปล่อย AI คิดเอง" ไปใส่ตรงๆ เด็ดขาด

**กฎเหล็กในการแต่ง Prompt (STRICT RULES):**
1. **ห้ามแปลข้อความ (DO NOT TRANSLATE TEXT):** คำพาดหัวและป้ายโปร ต้องเก็บไว้เป็นภาษาไทยในเครื่องหมายคำพูดเป๊ะๆ (ถ้าผู้ใช้ไม่ได้ระบุเป็น 'ปล่อย AI คิดเอง')
2. โครงสร้าง Prompt ภาษาอังกฤษ: เขียนเป็น 1 ย่อหน้า อธิบายหน้าตาพรีเซนเตอร์ การจัดดิสเพลย์สินค้าอลังการ และต้องมีประโยคเกี่ยวกับการเรนเดอร์ข้อความและป้ายต่างๆ เช่น `The text "..." and "..." are clearly rendered using ... typography with ... effect, placed at ... within a prominent ... badge. Also, display the ... prominently. STRICTLY render ONLY the requested text. DO NOT render extra symbols or gibberish. Apply ... graphics.`

**รูปแบบการตอบกลับ (JSON FORMAT ONLY):**
{{
    "english_prompt": "Prompt สร้างภาพนิ่ง: [Prompt ภาษาอังกฤษฉบับ Hard-Sell จัดเต็ม]",
    "thai_translation": "[คำแปล Prompt และคำอธิบายภาษาไทยให้คนอ่านเข้าใจ]"
}}
"""
                try:
                    res = smart_generate(prompt)
                    json_str = re.search(r'\{.*\}', res, re.DOTALL).group(0)
                    prompt_data = json.loads(json_str)
                    
                    st.session_state.ad_poster_prompt = prompt_data.get("english_prompt", "")
                    st.session_state.ad_poster_prompt_th = prompt_data.get("thai_translation", "")
                except Exception as e:
                    st.error(f"❌ AI เกิดการขัดข้อง กรุณาลองใหม่อีกครั้ง ({e})")

        if st.session_state.ad_poster_prompt:
            st.markdown("---")
            st.markdown("### 📌 สรุปบรีฟงานหน้าปก (Summary Board)")
            st.info(f"**ดิสเพลย์:** {st.session_state.get('ad_pos_display')} | **เลย์เอาต์:** {st.session_state.get('ad_pos_ad_comp')} | **VFX:** {st.session_state.get('ad_pos_graphics')}\n\n**พาดหัว:** {st.session_state.get('ad_pos_main_headline')} | **ราคา:** {st.session_state.get('ad_pos_sub_text')} | **ความน่าเชื่อถือ:** {st.session_state.get('ad_pos_trust')}")
            
            c_eng, c_th = st.columns(2)
            with c_eng:
                st.success("🇬🇧 คำสั่งภาษาอังกฤษ (ส่งให้ระบบ Handoff/บอท)")
                st.text_area("📄 Prompt ภาษาอังกฤษฉบับ Hard-Sell:", value=st.session_state.ad_poster_prompt, height=200, key="ad_pos_eng_text_output")
            with c_th:
                st.info("🇹🇭 คำอธิบายภาษาไทย (สำหรับคุณเช็กความถูกต้อง)")
                st.markdown(f"*{st.session_state.ad_poster_prompt_th}*")

    with tab_run:
        active_refs = st.session_state.get('ad_presenter_img', []) if st.session_state.get('ad_presenter_img') else st.session_state.ad_imgs
        if st.session_state.ad_poster_prompt:
            st.markdown("#### 🖼️ รันโปสเตอร์ / หน้าปกคลิป")
            if st.button("⚙️ รันบอทสร้างโปสเตอร์", key="run_poster_ad"):
                run_bot_dialog(0, st.session_state.ad_poster_prompt, active_refs, True, is_poster_only=True)
            st.divider()
        if st.session_state.ad_video_prompt:
            st.markdown("#### 🎬 รันวิดีโอโฆษณา")
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.ad_video_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=False):
                    if st.button(f"⚙️ รันบอทสร้างวิดีโอฉาก {i+1}", key=f"run_vid_ad_{i}"):
                        run_bot_dialog(i+1, s_text, active_refs, i==0)

# =========================================================================================
# 🍰 โหมด 2: 🍰 รีวิวร้านตัวเอง (UGC Vlogger) 
# =========================================================================================
elif app_mode == "🍰 รีวิวร้านตัวเอง (UGC Vlogger)":
    st.markdown('<div class="main-header">🍰 สตูดิโอเจ้าของร้านรีวิวเอง (UGC Vlogger)</div>', unsafe_allow_html=True)
    if 'ugc_prompt' not in st.session_state: st.session_state.ugc_prompt = ""
    if 'ugc_poster_prompt' not in st.session_state: st.session_state.ugc_poster_prompt = ""
    if 'ugc_poster_prompt_th' not in st.session_state: st.session_state.ugc_poster_prompt_th = ""
    if 'ugc_imgs' not in st.session_state: st.session_state.ugc_imgs = []
    if 'ugc_presenter_img' not in st.session_state: st.session_state.ugc_presenter_img = []

    with st.expander("📸 0. อัปโหลดรูปภาพ (อาหาร/บรรยากาศ & คนรีวิว)", expanded=True):
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            st.markdown("**🍔 1. รูปอาหาร/บรรยากาศร้าน (จำเป็น)**")
            up_food = st.file_uploader("ลากรูปอาหาร/สินค้ามาวาง", type=['png', 'jpg'], accept_multiple_files=True, key="ugc_up_food")
            if up_food:
                st.session_state.ugc_imgs = []
                os.makedirs("temp_refs", exist_ok=True)
                for img_file in up_food:
                    path = os.path.join("temp_refs", img_file.name)
                    with open(path, "wb") as f: f.write(img_file.getbuffer())
                    st.session_state.ugc_imgs.append(path)
                st.image(up_food, width=150) 
        with col_up2:
            st.markdown("**👤 2. รูปคนรีวิว/เจ้าของร้าน (ทางเลือก)**")
            up_presenter = st.file_uploader("ใช้เป็น Reference หน้าตา", type=['png', 'jpg'], accept_multiple_files=False, key="ugc_up_pres")
            if up_presenter:
                st.session_state.ugc_presenter_img = []
                os.makedirs("temp_refs", exist_ok=True)
                path_pres = os.path.join("temp_refs", up_presenter.name)
                with open(path_pres, "wb") as f: f.write(up_presenter.getbuffer())
                st.session_state.ugc_presenter_img.append(path_pres)
                st.image(up_presenter, width=200)

    st.markdown("### 📝 ข้อมูลร้านและการรีวิว")
    c1, c2, c3 = st.columns(3)
    with c1: st.session_state.ugc_shop_name = st.text_input("🏠 ชื่อร้าน:", value=st.session_state.get('ugc_shop_name', ''), placeholder="ระบุชื่อร้าน...")
    with c2: st.session_state.ugc_menu = st.text_input("🍔 เมนูเด็ด/สินค้า:", value=st.session_state.get('ugc_menu', ''), placeholder="ระบุเมนู...")
    with c3: st.session_state.ugc_location = st.text_input("📍 พิกัด / ปิดการขาย:", value=st.session_state.get('ugc_location', ''), placeholder="ระบุพิกัด หรือช่องทาง...")
    
    st.session_state.ugc_extra_brief = st.text_area("📌 บรีฟพิเศษ / สิ่งที่ต้องพูดถึง (ทางเลือก):", value=st.session_state.get('ugc_extra_brief', ''), height=80, placeholder="เช่น ร้านมีที่จอดรถกว้าง, น้ำจิ้มทำสดใหม่ทุกวัน, ให้เยอะมากจนกินไม่หมด...")

    tab_vid, tab_poster, tab_run = st.tabs(["🎬 1. สร้างสคริปต์วิดีโอ", "🖼️ 2. สร้างโปสเตอร์/หน้าปก", "🚀 3. รันระบบ (Handoff)"])
    
    with tab_vid:
        st.markdown("##### 🎯 ล็อกเป้าหมายให้ AI (Pre-AI Controls)")
        ugc_ai_dir_len = st.selectbox("⏱️ ล็อกความยาวคลิป:", ["Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"], key="ugc_ai_dir_len")

        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าอัตโนมัติ (Auto-Fill)", key="ugc_ai", use_container_width=True):
                if not st.session_state.ugc_shop_name and not st.session_state.ugc_menu:
                    st.warning("⚠️ กรุณาระบุชื่อร้านหรือเมนูเด็ดก่อนครับ เพื่อให้ AI นำไปวิเคราะห์")
                else:
                    with st.spinner("🧠 AI กำลังสแกนรูปภาพและบริบทของร้าน..."):
                        ugc_context = f"ร้าน: {st.session_state.get('ugc_shop_name', '')} | เมนู: {st.session_state.get('ugc_menu', '')} | พิกัด: {st.session_state.get('ugc_location', '')} | บรีฟพิเศษ: {st.session_state.get('ugc_extra_brief', '')}"
                        prompt_contents = []
                        if st.session_state.ugc_imgs:
                            prompt_contents = [Image.open(img_file) for img_file in st.session_state.ugc_imgs]
                        
                        prompt_text = f"""คุณคือผู้กำกับคลิปไวรัลและ Vlogger ระดับโปร วิเคราะห์ข้อมูลร้านและเมนูต่อไปนี้: "{ugc_context}"
                        (และรูปภาพถ้ามี) แล้วเลือกตัวเลือกที่เหมาะสมที่สุดเพื่อสร้างคลิปรีวิวร้าน จากรายการด้านล่าง:
                        
                        - ugc_actor: ["เจ้าของร้านใจดี", "วัยรุ่นเทสดี (Cafe Hopper)", "สายกินจุ (Mukbang)", "นักวิจารณ์อาหาร", "เชฟทำอาหาร"]
                        - ugc_tone: ["ASMR (กระซิบ)", "Storytelling", "ตื่นเต้นอวยยศ (Hype)"]
                        - ugc_cam: ["ถือกล้องเซลฟี่เดินเข้าร้าน (Vlog POV)", "ตั้งกล้องกินโชว์", "มุมมองแทนสายตาตอนกิน (First-person POV)"]
                        - ugc_vibe: ["สตรีทฟู้ดริมทาง", "คาเฟ่มินิมอล", "หรูหราภัตตาคาร"]
                        - ugc_lang: ["ภาษาไทยกลาง", "อีสานมาตรฐาน", "ภาษาใต้", "ภาษาเหนือ"]
                        - ugc_music: ["เพลงฮิตTikTok", "Acoustic ชิลๆ", "ไม่มีเพลง (เน้นASMR)"]
                        - ugc_cta: ["ปักหมุดแผนที่ร้าน/ชวนมากิน", "แจกโปรโมชั่นหน้าร้าน"]
                        - ugc_pacing: ["ตัดฉับไว (Jump Cut)", "Beat Sync"]
                        - ugc_text_overlay: ["ซับไตเติ้ลคำต่อคำ", "ไม่มีข้อความ"]

                        ตอบกลับมาเป็น JSON Format เท่านั้น โดยใช้ Key ตามลิสต์ด้านบนและ Value ตรงกับตัวเลือกเป๊ะๆ
                        """
                        prompt_contents.append(prompt_text)

                        try:
                            res = smart_generate(prompt_contents)
                            json_str = re.search(r'\{.*\}', res, re.DOTALL).group(0)
                            ai_config = json.loads(json_str)
                            for k, v in ai_config.items(): st.session_state[k] = v
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ AI เกิดการขัดข้อง กรุณาลองใหม่อีกครั้ง ({e})")

        with col_res:
            if st.button("🔄 รีเซ็ต (Reset)", key="ugc_vid_res", use_container_width=True):
                st.session_state.ugc_prompt = ""
                vid_keys = ["ugc_actor", "ugc_tone", "ugc_cam", "ugc_vibe", "ugc_lang", "ugc_music", "ugc_cta", "ugc_pacing", "ugc_text_overlay"]
                for k in vid_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"ui_widget_{k}" in st.session_state: del st.session_state[f"ui_widget_{k}"]
                    if f"ui_custom_{k}" in st.session_state: del st.session_state[f"ui_custom_{k}"]
                st.rerun()
                
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("👤 ผู้รีวิว/คาแรคเตอร์:", ["เจ้าของร้านใจดี", "วัยรุ่นเทสดี (Cafe Hopper)", "สายกินจุ (Mukbang)", "นักวิจารณ์อาหาร", "เชฟทำอาหาร"], "ugc_actor")
            render_custom_select("🗣️ สไตล์น้ำเสียง:", ["ASMR (กระซิบ)", "Storytelling", "ตื่นเต้นอวยยศ (Hype)"], "ugc_tone")
            render_custom_select("🎥 มุมกล้อง/พร็อพ:", ["ถือกล้องเซลฟี่เดินเข้าร้าน (Vlog POV)", "ตั้งกล้องกินโชว์", "มุมมองแทนสายตาตอนกิน (First-person POV)"], "ugc_cam")
        with c2:
            render_custom_select("✨ บรรยากาศร้าน (Vibe):", ["สตรีทฟู้ดริมทาง", "คาเฟ่มินิมอล", "หรูหราภัตตาคาร"], "ugc_vibe")
            render_custom_select("🌐 ภาษาและสำเนียง:", ["ภาษาไทยกลาง", "อีสานมาตรฐาน", "ภาษาใต้", "ภาษาเหนือ"], "ugc_lang")
            render_custom_select("🎵 ดนตรีประกอบ (BGM):", ["เพลงฮิตTikTok", "Acoustic ชิลๆ", "ไม่มีเพลง (เน้นASMR)"], "ugc_music")
        with c3:
            render_custom_select("👉 ปิดการขาย (CTA):", ["ปักหมุดแผนที่ร้าน/ชวนมากิน", "แจกโปรโมชั่นหน้าร้าน"], "ugc_cta")
            render_custom_select("🎞️ จังหวะตัดต่อ:", ["ตัดฉับไว (Jump Cut)", "Beat Sync"], "ugc_pacing")
            render_custom_select("✍️ ข้อความบนจอ:", ["ซับไตเติ้ลคำต่อคำ", "ไม่มีข้อความ"], "ugc_text_overlay")

        if st.button("🚀 เริ่มเขียนสคริปต์รีวิวร้าน (UGC Vlogger)", type="primary", use_container_width=True):
            prompt = f"""คุณคือผู้กำกับและ Content Creator ระดับประเทศ เขียนสคริปต์คลิปรีวิวร้านอาหารแบบแบ่งฉาก (ฉากละ 8 วินาที) อ้างอิงจากการตั้งค่า:
ชื่อร้าน: {st.session_state.get('ugc_shop_name')}
เมนูเด็ด: {st.session_state.get('ugc_menu')}
พิกัด: {st.session_state.get('ugc_location')}
บรีฟพิเศษ: {st.session_state.get('ugc_extra_brief')}
ผู้รีวิว: {st.session_state.get('ugc_actor')}
เสียง (Tone): {st.session_state.get('ugc_tone')}
มุมกล้อง: {st.session_state.get('ugc_cam')}
บรรยากาศร้าน: {st.session_state.get('ugc_vibe')}
ภาษา: {st.session_state.get('ugc_lang')}
ดนตรี: {st.session_state.get('ugc_music')}
CTA: {st.session_state.get('ugc_cta')}
ความยาวคลิป: {ugc_ai_dir_len}

🎬 ฉากที่ 1: เปิดคลิปเรียกน้ำย่อย (The Hook - 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายภาพรวมว่าเกิดอะไรขึ้น (เช่น โชว์อาหารน่ากิน หรือคนรีวิวกำลังตื่นเต้น)
* ข้อความบนจอ: (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (เขียนตามสรรพนามเพศที่เหมาะสมกับคาแรคเตอร์)
* Prompt สร้างภาพนิ่ง: (ภาษาอังกฤษ - สำหรับ Nano Banana 2) อธิบายหน้าตาผู้รีวิว (ถ้ามี), อาหาร, ฉากหลัง, แสง, โทนสี และมุมกล้องอย่างละเอียดที่สุด เพื่อใช้เป็นภาพอ้างอิง
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ - สำหรับ Veo 3.1) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ ระบุจังหวะตัดกล้อง และลงท้ายด้วยคำว่า "Audio: [เสียง SFX/ดนตรี]"

🎬 ฉากที่ 2, 3, 4... : รีวิวและกินโชว์ (Review & Eat - ฉากละ 8 วินาที)
* (ห้ามเขียน Prompt สร้างภาพนิ่งในฉากที่ 2 เป็นต้นไปเด็ดขาด)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ เริ่มด้วย "Continuing from the previous frame..." ระบุจังหวะตัดกล้อง และลงท้ายด้วย "Audio: [เสียงประกอบที่สอดคล้อง]"

📱 ส่วนท้ายสุด: แคปชั่นดันคลิป 3 แพลตฟอร์ม
- TikTok, Facebook Reels, Shopee Video (Hard-sell กระชับ ห้ามเกิน 150 ตัวอักษรรวมแฮชแท็ก)
"""
            st.session_state.ugc_prompt = smart_generate(prompt)

        if st.session_state.ugc_prompt: st.text_area("📄 สคริปต์คลิปรีวิวฉบับเต็ม:", value=st.session_state.ugc_prompt, height=400, key="ugc_vid_text_output")

    with tab_poster:
        st.markdown("##### 🎯 ล็อกเป้าหมายให้ AI (Pre-AI Controls - Poster)")
        ugc_ai_dir_ratio_pos = st.selectbox("📏 ล็อกสัดส่วนภาพหน้าปก (Aspect Ratio):", ["🤖 ปล่อย AI คิดเอง", "16:9 (YouTube Vlog แนวนอน)", "4:3 (แนวนอนมาตรฐาน)", "1:1 (Facebook/IG จัตุรัส)", "3:4 (Portrait แมนยง)", "9:16 (TikTok/Reels แนวตั้ง)"], key="ugc_ai_dir_ratio_pos")

        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าโปสเตอร์อัตโนมัติ", key="ugc_pos_ai", use_container_width=True):
                if not st.session_state.ugc_shop_name and not st.session_state.ugc_menu:
                    st.warning("⚠️ กรุณาระบุชื่อร้านหรือเมนูเด็ดก่อนครับ")
                else:
                    with st.spinner("🧠 AI กำลังสแกนรูปภาพและออกแบบหน้าปก Vlog..."):
                        ratio_constraint_pos = ""
                        if "16:9" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกมุมกล้องให้เหมาะสมกับอัตราส่วนแนวนอนกว้าง 16:9 (YouTube Vlog)'
                        elif "1:1" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกมุมกล้องให้เหมาะสมกับสัดส่วนจัตุรัส 1:1 เน้นจุดสนใจตรงกลางอาหาร'
                        elif "9:16" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกมุมกล้อง และตำแหน่งข้อความให้เหมาะสมกับแนวตั้ง 9:16 โดยเว้น Safe Zone ให้มือถือเสมอ'

                        ugc_context = f"ร้าน: {st.session_state.get('ugc_shop_name', '')} | เมนู: {st.session_state.get('ugc_menu', '')} | พิกัด: {st.session_state.get('ugc_location', '')}"
                        prompt_contents = []
                        if st.session_state.ugc_imgs:
                            prompt_contents = [Image.open(img_file) for img_file in st.session_state.ugc_imgs]
                        
                        prompt_text = f"""วิเคราะห์ข้อมูลร้านและรูปภาพเหล่านี้: "{ugc_context}"
                        แล้วเลือกตัวเลือกที่เหมาะสมที่สุดเพื่อออกแบบโปสเตอร์/หน้าปก Vlog อาหาร ระดับมืออาชีพ จากรายการด้านล่าง:
                        
                        - ugc_pos_style: ["Vlog Thumbnail (ปกคลิปรีวิวไวรัล)", "Minimalist Cafe Cover (ปกมินิมอลคาเฟ่)", "Street Food Authentic (ปกสตรีทฟู้ดเรียลๆ)", "High-end E-commerce (แคตตาล็อก)", "Hyper-Realistic 3D Render (3D สมจริง)"]
                        - ugc_pos_color: ["Warm & Appetizing (สดใสอมส้ม)", "Vibrant Contrast (จัดจ้านตัดกัน)", "Bright & Clean (สว่างสว่างคลีนๆ)", "Japanese Film/Muted (โทนฟิล์มญี่ปุ่นละมุนๆ)"]
                        - ugc_pos_cam: ["ซูมใกล้เนื้ออาหารฉ่ำๆ (Macro Close-up)", "ระดับสายตาเห็นคนและอาหาร (Eye-level portrait)", "มุมมองแทนสายตาตอนกิน (First-Person POV)", "มุมสูงเจาะเต็มโต๊ะ (Top-down Flat Lay)"]
                        - ugc_pos_graphics: ["ประกายแสงวิบวับและออร่า (Sparkles &Glowing Aura)", "สายฟ้าและพลังงาน (Lightning Energy FX)", "ลูกศรนีออนชี้ไปที่สินค้า (Glowing Arrow Pointer)", "เส้นสปีดไลน์พุ่งเข้าหาตรงกลาง (Action Speed Lines)", "ชีสยืด/ควันพุ่ง (Hard-Sell Appetizing)"]
                        - ugc_pos_typography: ["ฟอนต์ตัวหนากระแทกตาแบบ Youtuber (Bold Impact with Stroke)", "ฟอนต์ลายมือดูเป็นมิตร (Friendly Handwritten)", "ฟอนต์คาเฟ่มินิมอล (Clean Sans-serif)"]
                        - ugc_pos_main_headline: ["อร่อยแสงออกปาก!", "ร้านลับต้องลอง!", "ให้เยอะจนจุก!", "ชื่อสินค้าโดดๆ", "ไม่มีข้อความ"]
                        - ugc_pos_sub_text: ["พิกัดลับ", "ราคาหลักสิบ", "คิวยาวมาก", "รีวิว 5 ดาว", "ไม่มีข้อความ"]

                        ⚠️ กฎพิเศษในการตั้งค่า:
                        {ratio_constraint_pos}

                        ตอบกลับมาเป็น JSON Format เท่านั้น
                        """
                        prompt_contents.append(prompt_text)
                        
                        try:
                            res = smart_generate(prompt_contents)
                            json_str = re.search(r'\{.*\}', res, re.DOTALL).group(0)
                            ai_config = json.loads(json_str)
                            for k, v in ai_config.items(): st.session_state[k] = v
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ AI เกิดการขัดข้อง กรุณาลองใหม่อีกครั้ง ({e})")

        with col_res:
            if st.button("🔄 รีเซ็ตหน้าปก", key="ugc_pos_res", use_container_width=True):
                st.session_state.ugc_poster_prompt = ""
                st.session_state.ugc_poster_prompt_th = ""
                pos_keys = ["ugc_pos_style", "ugc_pos_color", "ugc_pos_cam", "ugc_pos_graphics", "ugc_pos_typography", "ugc_pos_main_headline", "ugc_pos_sub_text"]
                for k in pos_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"ui_widget_{k}" in st.session_state: del st.session_state[f"ui_widget_{k}"]
                    if f"ui_custom_{k}" in st.session_state: del st.session_state[f"ui_custom_{k}"]
                st.rerun()

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 🎨 สไตล์หน้าปก (Style):", ["Vlog Thumbnail (ปกคลิปรีวิวไวรัล)", "Minimalist Cafe Cover (ปกมินิมอลคาเฟ่)", "Street Food Authentic (ปกสตรีทฟู้ดเรียลๆ)", "High-end E-commerce (แคตตาล็อก)", "Hyper-Realistic 3D Render (3D สมจริง)"], "ugc_pos_style")
            render_custom_select("2. 🌈 โทนสี (Color Grading):", ["Warm & Appetizing (สดใสอมส้ม)", "Vibrant Contrast (จัดจ้านตัดกัน)", "Bright & Clean (สว่างสว่างคลีนๆ)", "Japanese Film/Muted (โทนฟิล์มญี่ปุ่นละมุนๆ)"], "ugc_pos_color")
        with c2:
            render_custom_select("3. 📸 มุมกล้อง (Camera Angle):", ["ซูมใกล้เนื้ออาหารฉ่ำๆ (Macro Close-up)", "ระดับสายตาเห็นคนและอาหาร (Eye-level portrait)", "มุมมองแทนสายตาตอนกิน (First-Person POV)", "มุมสูงเจาะเต็มโต๊ะ (Top-down Flat Lay)"], "ugc_pos_cam")
            render_custom_select("4. ✨ VFX/กราฟิกน่ากิน:", ["ประกายแสงวิบวับและออร่า (Sparkles &Glowing Aura)", "สายฟ้าและพลังงาน (Lightning Energy FX)", "ลูกศรนีออนชี้ไปที่สินค้า (Glowing Arrow Pointer)", "เส้นสปีดไลน์พุ่งเข้าหาตรงกลาง (Action Speed Lines)", "ชีสยืด/ควันพุ่ง (Hard-Sell Appetizing)"], "ugc_pos_graphics", "ชีสยืด/ควันพุ่ง = Hard-Sell กระตุ้นความหิวชั้นดี")
        with c3:
            render_custom_select("5. 🔠 สไตล์ฟอนต์ (Typography):", ["ฟอนต์ตัวหนากระแทกตาแบบ Youtuber (Bold Impact with Stroke)", "ฟอนต์ลายมือดูเป็นมิตร (Friendly Handwritten)", "ฟอนต์คาเฟ่มินิมอล (Clean Sans-serif)"], "ugc_pos_typography")
            render_custom_select("6. 📢 พาดหัวหลัก (Headline):", ["อร่อยแสงออกปาก!", "ร้านลับต้องลอง!", "ให้เยอะจนจุก!", "ไม่กินคือพลาด!", "ชื่อสินค้าโดดๆ", "ไม่มีข้อความ"], "ugc_pos_main_headline")
            render_custom_select("7. 🏷️ ป้ายราคา/โปร (Sub-text):", ["พิกัดลับ", "ราคาหลักสิบ", "คิวยาวมาก", "รีวิว 5 ดาว", "ไม่มีข้อความ"], "ugc_pos_sub_text")

        if st.button("🚀 เริ่มสร้าง Prompt ปกคลิปรีวิว (Nano Banana 2)", type="primary", use_container_width=True):
            with st.spinner("🧠 AI กำลังแต่ง Prompt และแยกหน้าจอแปลภาษา..."):
                prompt = f"""คุณคือนักเขียน Prompt ระดับโลกสำหรับ AI สร้างภาพ 'Nano Banana 2'

ข้อมูลสำหรับปกคลิปรีวิวอาหาร:
- ร้าน/เมนู: {st.session_state.get('ugc_shop_name')} {st.session_state.get('ugc_menu')}
- สไตล์ปกคลิป: {st.session_state.get('ugc_pos_style')}
- โทนสี & Vibe: {st.session_state.get('ugc_pos_color')}
- มุมกล้อง: {st.session_state.get('ugc_pos_cam')}
- กราฟิกน่ากิน/VFX: {st.session_state.get('ugc_pos_graphics')}
- สไตล์ฟอนต์ (Typography): {st.session_state.get('ugc_pos_typography')}
- พาดหัวหลัก: "{st.session_state.get('ugc_pos_main_headline')}"
- ป้ายรอง: "{st.session_state.get('ugc_pos_sub_text')}"

**กฎเหล็กในการแต่ง Prompt (STRICT RULES):**
1. **ห้ามแปลข้อความ (DO NOT TRANSLATE TEXT):** คำว่า "{st.session_state.get('ugc_pos_main_headline')}" และ "{st.session_state.get('ugc_pos_sub_text')}" ต้องเก็บไว้เป็นภาษาไทยในเครื่องหมายคำพูดเป๊ะๆ
2. โครงสร้าง Prompt: 1 ย่อหน้า อธิบายความน่ากินของอาหารอย่างละเอียด และต้องมีประโยคเกี่ยวกับการเรนเดอร์ข้อความ เช่น `The text "{st.session_state.get('ugc_pos_main_headline')}" and "{st.session_state.get('ugc_pos_sub_text')}" are clearly rendered using {st.session_state.get('ugc_pos_typography')} typography. Apply prominent {st.session_state.get('ugc_pos_graphics')}. STRICTLY render ONLY the requested text. DO NOT render extra gibberish or symbols.

**รูปแบบการตอบกลับ (JSON FORMAT ONLY):**
{{
    "english_prompt": "Prompt สร้างภาพนิ่ง: [Prompt ภาษาอังกฤษทั้งหมด]",
    "thai_translation": "[คำแปล Prompt และคำอธิบายภาษาไทยให้คนอ่านเข้าใจ]"
}}
"""
                try:
                    res = smart_generate(prompt)
                    json_str = re.search(r'\{.*\}', res, re.DOTALL).group(0)
                    prompt_data = json.loads(json_str)
                    
                    st.session_state.ugc_poster_prompt = prompt_data.get("english_prompt", "")
                    st.session_state.ugc_poster_prompt_th = prompt_data.get("thai_translation", "")
                except Exception as e:
                    st.error(f"❌ AI เกิดการขัดข้อง กรุณาลองใหม่อีกครั้ง ({e})")

        if st.session_state.ugc_poster_prompt:
            st.markdown("---")
            st.markdown("### 📌 สรุปบรีฟงานหน้าปกคลิป (Summary Board)")
            st.info(f"**สไตล์:** {st.session_state.get('ugc_pos_style')} | **โทนสี:** {st.session_state.get('ugc_pos_color')} | **มุมกล้อง:** {st.session_state.get('ugc_pos_cam')}\n\n**พาดหัว:** {st.session_state.get('ugc_pos_main_headline')} | **ราคา:** {st.session_state.get('ugc_pos_sub_text')} | **VFX:** {st.session_state.get('ugc_pos_graphics')}")
            
            c_eng, c_th = st.columns(2)
            with c_eng:
                st.success("🇬🇧 คำสั่งภาษาอังกฤษ (ส่งให้ระบบ Handoff/บอท)")
                st.text_area("📄 Prompt ภาษาอังกฤษหน้าปก:", value=st.session_state.ugc_poster_prompt, height=200, key="ugc_pos_eng_text_output")
            with c_th:
                st.info("🇹🇭 คำอธิบายภาษาไทย (สำหรับคุณเช็กความถูกต้อง)")
                st.markdown(f"*{st.session_state.ugc_poster_prompt_th}*")

    with tab_run:
        active_refs_ugc = st.session_state.get('ugc_presenter_img', []) if st.session_state.get('ugc_presenter_img') else st.session_state.ugc_imgs
        if st.session_state.ugc_poster_prompt:
            st.markdown("#### 🖼️ รันโปสเตอร์ / หน้าปกคลิปรีวิว")
            if st.button("⚙️ รันบอทสร้างหน้าปกคลิป", key="run_poster_ugc"):
                run_bot_dialog(0, st.session_state.ugc_poster_prompt, active_refs_ugc, True, is_poster_only=True)
            st.divider()
        if st.session_state.ugc_prompt:
            st.markdown("#### 🎬 รันวิดีโอคลิปรีวิวร้าน")
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.ugc_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"ugc_btn_{i}"):
                        run_bot_dialog(i+1, s_text, active_refs_ugc, i==0)

# =========================================================================================
# 💼 โหมด 3: 🎤 วิทยากร AI (AI Spokesperson)
# =========================================================================================
elif app_mode == "🎤 วิทยากร AI (AI Spokesperson)":
    st.markdown('<div class="main-header">🎤 สตูดิโอวิทยากร AI</div>', unsafe_allow_html=True)
    if 'spk_prompt' not in st.session_state: st.session_state.spk_prompt = ""
    if 'spk_poster_prompt' not in st.session_state: st.session_state.spk_poster_prompt = ""
    if 'spk_raw_text' not in st.session_state: st.session_state.spk_raw_text = ""
    
    st.session_state.spk_raw_text = st.text_area("📝 บทพูดของคุณ (Script):", value=st.session_state.spk_raw_text, height=100)
    if st.button("🪄 ขัดเกลาข้อความให้ดูโปรขึ้น", type="secondary"):
        st.session_state.spk_raw_text = smart_generate(f"ขัดเกลาให้สละสลวยดูเป็นมืออาชีพ: {st.session_state.spk_raw_text}")
        st.rerun()

    tab_vid, tab_poster, tab_run = st.tabs(["⚙️ 1. ตั้งค่าวิทยากร", "🖼️ 2. สร้างโปสเตอร์ปกคลิป", "🚀 3. รันบอท (Handoff)"])
    with tab_vid:
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าอัตโนมัติ", key="spk_ai", use_container_width=True):
                st.info("ระบบจำลองการตั้งค่าออโต้...")
        with col_res:
            if st.button("🔄 รีเซ็ต", key="spk_res", use_container_width=True):
                st.session_state.spk_prompt = ""
                st.rerun()
        st.markdown("---")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("👤 วิทยากร:", ["CEO หนุ่ม", "นักธุรกิจหญิง"], "spk_actor")
            render_custom_select("👕 ชุด:", ["เสื้อยืดกางเกงยีนส์", "ชุดสูท"], "spk_costume")
        with c2:
            render_custom_select("🏡 ฉาก:", ["เวที TED Talk", "พอดแคสต์"], "spk_setting")
            render_custom_select("🎥 มุมกล้อง:", ["ครึ่งตัว", "ซูมใกล้"], "spk_camera")
        with c3:
            render_custom_select("🗣️ อารมณ์:", ["สร้างแรงบันดาลใจ", "ให้ความรู้จริงจัง"], "spk_tone")
        
        if st.button("🚀 เริ่มเขียนสคริปต์วิทยากร", type="primary", use_container_width=True):
            st.session_state.spk_prompt = smart_generate(f"สคริปต์ AI Spokesperson วิทยากร: {st.session_state.get('spk_actor')} ฉาก: {st.session_state.get('spk_setting')} กล้อง: {st.session_state.get('spk_camera')} บทพูด: {st.session_state.spk_raw_text}. แยก Prompt ภาพและวิดีโอ (ใส่ Audio Cues)")
                
        if st.session_state.spk_prompt: st.text_area("📄 สคริปต์วิทยากร AI:", value=st.session_state.spk_prompt, height=300, key="spk_text_output")
    
    with tab_poster:
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าหน้าปกอัตโนมัติ", key="spk_pos_ai", use_container_width=True):
                st.info("ระบบจำลองการตั้งค่าออโต้...")
        with col_res:
            if st.button("🔄 รีเซ็ตหน้าปก", key="spk_pos_res", use_container_width=True):
                st.session_state.spk_poster_prompt = ""
                st.rerun()
        st.markdown("---")
        render_custom_select("📝 คำโปรยบนปกคลิป (Topic Text):", ["แชร์ทริคความสำเร็จ", "ความลับที่ไม่มีใครบอกคุณ", "พิมพ์กำหนดเอง..."], "spk_poster_txt")
        if st.button("🎨 สร้าง Prompt หน้าปก", type="primary", use_container_width=True):
            st.session_state.spk_poster_prompt = smart_generate(f"Prompt สร้างภาพนิ่ง หน้าปก YouTube ของวิทยากร {st.session_state.get('spk_actor')} ฉาก {st.session_state.get('spk_setting')} ข้อความ: {st.session_state.get('spk_poster_txt')}")
        
        if st.session_state.spk_poster_prompt: st.text_area("📄 Prompt หน้าปกวิทยากร:", value=st.session_state.spk_poster_prompt, height=200, key="spk_pos_text_output")

    with tab_run:
        if st.session_state.spk_poster_prompt:
            if st.button("⚙️ รันบอทสร้างหน้าปกคลิป", key="run_poster_spk"):
                run_bot_dialog(0, st.session_state.spk_poster_prompt, [], True, is_poster_only=True)
            st.divider()
        if st.session_state.spk_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.spk_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"spk_btn_{i}"):
                        run_bot_dialog(i+1, s_text, [], i==0)

# =========================================================================================
# 🤣 โหมด 4: 🐾 สัตว์เลี้ยงไวรัล (Viral Pet)
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
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าอัตโนมัติ", key="pet_ai", use_container_width=True):
                st.info("ระบบจำลองการตั้งค่าออโต้...")
        with col_res:
            if st.button("🔄 รีเซ็ตวิดีโอ", key="pet_res", use_container_width=True):
                st.session_state.pet_prompt = ""
                st.rerun()
        st.markdown("---")
        
        c1, c2, c3 = st.columns(3)
        with c1: 
            render_custom_select("🐱 สัตว์เลี้ยง:", ["แมวสลิด", "หมาไซ"], "pet_actor")
            render_custom_select("👕 ชุด:", ["ใส่ผ้ากันเปื้อน", "ไม่ใส่ชุด"], "pet_costume")
        with c2: 
            render_custom_select("🔪 แอคชั่น:", ["ทำกับข้าว", "บ่นเจ้านาย"], "pet_act")
            render_custom_select("🏡 ฉาก:", ["แคร่ไม้ไผ่", "ห้องครัว"], "pet_set")
        with c3: 
            render_custom_select("💬 เสียงพูด:", ["เถียงกัน", "ASMR"], "pet_audio")
        
        if st.button("🚀 เริ่มเขียนสคริปต์มีม", type="primary", use_container_width=True):
            st.session_state.pet_prompt = smart_generate(f"สคริปต์มีมสัตว์เลี้ยง (Anthropomorphic) {st.session_state.get('pet_actor')} ชุด {st.session_state.get('pet_costume')} กำลัง {st.session_state.get('pet_act')} ฉาก {st.session_state.get('pet_set')} เสียง: {st.session_state.get('pet_audio')}. แยก Prompt ภาพและวิดีโอ (พร้อม Audio Cues)")

        if st.session_state.pet_prompt: st.text_area("📄 สคริปต์มีมสัตว์เลี้ยง:", value=st.session_state.pet_prompt, height=300, key="pet_text_output")
    
    with tab_poster:
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าหน้าปกอัตโนมัติ", key="petpos_ai", use_container_width=True):
                st.info("ระบบจำลองการตั้งค่าออโต้...")
        with col_res:
            if st.button("🔄 รีเซ็ตโปสเตอร์", key="petpos_res", use_container_width=True):
                st.session_state.pet_poster_prompt = ""
                st.rerun()
        st.markdown("---")
        
        render_custom_select("📝 คำโปรยบนปกคลิป:", ["POV: ทาสใช้ให้ทำกับข้าว", "เชฟสี่ขา"], "pet_poster_txt")
        if st.button("🚀 เริ่มสร้าง Prompt หน้าปก", type="primary", use_container_width=True):
            st.session_state.pet_poster_prompt = smart_generate(f"Prompt สร้างภาพนิ่ง หน้าปก YouTube ของ {st.session_state.get('pet_actor')} กำลัง {st.session_state.get('pet_act')} ข้อความ: {st.session_state.get('pet_poster_txt')}")

        if st.session_state.pet_poster_prompt: st.text_area("📄 Prompt หน้าปกมีม:", value=st.session_state.pet_poster_prompt, height=200, key="pet_pos_text_output")

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
# 🤣 โหมด 5: 🎭 คาแรคเตอร์สายฮา (Caricature)
# =========================================================================================
elif app_mode == "🎭 คาแรคเตอร์สายฮา (Caricature)":
    st.markdown('<div class="main-header">🎭 สตูดิโอปั้นมีมไทบ้าน (Caricature)</div>', unsafe_allow_html=True)
    if 'meme_prompt' not in st.session_state: st.session_state.meme_prompt = ""
    if 'meme_poster_prompt' not in st.session_state: st.session_state.meme_poster_prompt = ""

    tab_vid, tab_poster, tab_run = st.tabs(["⚙️ 1. ออกแบบคาแรคเตอร์", "🖼️ 2. สร้างโปสเตอร์ปกคลิป", "🚀 3. รันบอท (Handoff)"])
    with tab_vid:
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าอัตโนมัติ", key="meme_ai", use_container_width=True):
                st.info("ระบบจำลองการตั้งค่าออโต้...")
        with col_res:
            if st.button("🔄 รีเซ็ต", key="meme_res", use_container_width=True):
                st.session_state.meme_prompt = ""
                st.rerun()
        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("👥 จำนวน:", ["1 คน (Solo)", "2 คนนั่งคุยกัน"], "meme_count")
            render_custom_select("🤪 ลักษณะเด่น:", ["หน้าเหี่ยวย่น ฟันหลอ", "ผมฟูชี้ฟู"], "meme_feat")
        with c2:
            render_custom_select("👕 ชุด:", ["ไม่ใส่เสื้อ คาดผ้าขาวม้า", "เสื้อเก่าๆ มอซอ"], "meme_costume")
            render_custom_select("🏡 ฉาก:", ["เถียงนา", "วงเหล้า"], "meme_set")
        with c3:
            render_custom_select("🎨 สไตล์:", ["3D Pixar Animation", "3D Caricature"], "meme_style")
            render_custom_select("💬 เสียง:", ["คุยโวเรื่องถูกหวย", "บ่นเมียหนี"], "meme_dialogue")
        if st.button("🚀 สั่ง AI เขียนสคริปต์มีมไทบ้าน", type="primary", use_container_width=True):
            st.session_state.meme_prompt = smart_generate(f"สคริปต์วิดีโอล้อเลียน {st.session_state.get('meme_count')} คน ลักษณะ: {st.session_state.get('meme_feat')} ชุด: {st.session_state.get('meme_costume')} ฉาก: {st.session_state.get('meme_set')} สไตล์: {st.session_state.get('meme_style')} เสียง: {st.session_state.get('meme_dialogue')}. แยก Prompt ภาพนิ่งและวิดีโอ (พร้อม Audio cues)")
        
        if st.session_state.meme_prompt: st.text_area("📄 สคริปต์มีมไทบ้าน:", value=st.session_state.meme_prompt, height=300, key="meme_text_output")
    
    with tab_poster:
        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าหน้าปกอัตโนมัติ", key="memepos_ai", use_container_width=True):
                st.info("ระบบจำลองการตั้งค่าออโต้...")
        with col_res:
            if st.button("🔄 รีเซ็ตหน้าปก", key="memepos_res", use_container_width=True):
                st.session_state.meme_poster_prompt = ""
                st.rerun()
        st.markdown("---")
        render_custom_select("📝 คำโปรยบนปกคลิป (Clickbait Text):", ["ชีวิตมันเศร้าขอเหล้าเข้มๆ", "ถูกหวยรางวัลที่ 1", "พิมพ์กำหนดเอง..."], "meme_poster_txt")
        if st.button("🎨 สร้าง Prompt หน้าปก", type="primary", use_container_width=True):
            st.session_state.meme_poster_prompt = smart_generate(f"Prompt สร้างภาพนิ่ง หน้าปก YouTube มีมไทบ้าน สไตล์ {st.session_state.get('meme_style')} ฉาก {st.session_state.get('meme_set')} ข้อความ: {st.session_state.get('meme_poster_txt')}")
        
        if st.session_state.meme_poster_prompt: st.text_area("📄 Prompt หน้าปกไทบ้าน:", value=st.session_state.meme_poster_prompt, height=200, key="meme_pos_text_output")

    with tab_run:
        if st.session_state.meme_poster_prompt:
            if st.button("⚙️ รันบอทสร้างหน้าปกคลิป", key="run_poster_meme"):
                run_bot_dialog(0, st.session_state.meme_poster_prompt, [], True, is_poster_only=True)
            st.divider()
        if st.session_state.meme_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.meme_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"meme_btn_{i}"):
                        run_bot_dialog(i+1, s_text, [], i==0)

# =========================================================================================
# 🤣 โหมด 6: 🎙️ ทอล์คโชว์สายปั่น (Stand-up)
# =========================================================================================
elif app_mode == "🎙️ ทอล์คโชว์สายปั่น (Stand-up)":
    st.markdown('<div class="main-header">🎙️ สตูดิโอทอล์คโชว์ & ปราศรัยสายฮา</div>', unsafe_allow_html=True)
    if 'sat_prompt' not in st.session_state: st.session_state.sat_prompt = ""
    if 'sat_raw' not in st.session_state: st.session_state.sat_raw = ""

    st.session_state.sat_raw = st.text_area("📝 บทพูดบนเวที:", value=st.session_state.sat_raw, height=100)
    topic = st.text_input("📌 หรือพิมพ์หัวข้อให้ AI ร่างให้:", placeholder="เช่น ของแพง, ลอตเตอรี่...")
    if st.button("✨ ให้ AI ร่างบทสุดปั่น", type="secondary"):
        st.session_state.sat_raw = smart_generate(f"เขียนบทเดี่ยวไมโครโฟน/ปราศรัยฮาๆ หัวข้อ: '{topic}'")
        st.rerun()

    tab_vid, tab_run = st.tabs(["⚙️ 1. จัดเวทีและนักแสดง", "🚀 2. รันบอท (Handoff)"])
    with tab_vid:
        c1, c2 = st.columns(2)
        with c1:
            render_custom_select("🐒 ตัวละคร:", ["ลิงแสมหน้าตึง", "ตัวเงินตัวทองใส่สูท"], "sat_actor")
            render_custom_select("👕 ชุด:", ["คล้องพวงมาลัยดาวเรือง คาดผ้าขาวม้า", "ชุดสูทสีฉูดฉาด"], "sat_costume")
        with c2:
            render_custom_select("🏡 ฉาก:", ["เวทีปราศรัยมีป้ายไวนิล", "คลับมืดๆ มีสปอตไลท์"], "sat_setting")
            render_custom_select("🗣️ ท่าทาง:", ["ยกมือสองข้างขึ้น ชูไม้ชูมือ", "ยืนกอดอกหน้าตึง"], "sat_action")
        if st.button("🚀 สั่ง AI ปั้นสคริปต์ปราศรัย", type="primary"):
            st.session_state.sat_prompt = smart_generate(f"สคริปต์วิดีโอล้อเลียน ตัวละคร: {st.session_state.get('sat_actor')} ชุด: {st.session_state.get('sat_costume')} ฉาก: {st.session_state.get('sat_setting')} ท่าทาง: {st.session_state.get('sat_action')} บทพูด: {st.session_state.sat_raw}. แยก Prompt ภาพและวิดีโอ (ใส่ Audio cues)")
        
        if st.session_state.sat_prompt: st.text_area("📄 สคริปต์ปราศรัย:", value=st.session_state.sat_prompt, height=300, key="sat_text_output")
    with tab_run:
        if st.session_state.sat_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.sat_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"sat_btn_{i}"):
                        run_bot_dialog(i+1, s_text, [], i==0)

# =========================================================================================
# 🕶️ โหมด 7: 🕶️ ช่องคำคมสู้ชีวิต (Sigma Motivation)
# =========================================================================================
elif app_mode == "🕶️ ช่องคำคมสู้ชีวิต (Sigma Motivation)":
    st.markdown('<div class="main-header">🕶️ สตูดิโอช่องคำคมรวยเงียบ (Faceless Sigma)</div>', unsafe_allow_html=True)
    if 'sigma_prompt' not in st.session_state: st.session_state.sigma_prompt = ""

    tab_vid, tab_run = st.tabs(["⚙️ 1. ตั้งค่าคำคมและฉาก", "🚀 2. รันบอท (Handoff)"])
    with tab_vid:
        topic = st.text_input("📌 หัวข้อคำคม:", placeholder="เช่น ความพยายาม, การหาเงิน...")
        c1, c2 = st.columns(2)
        with c1: render_custom_select("🎥 ภาพพื้นหลัง:", ["ผู้ชายใส่สูทเดินฝ่าฝน", "รถสปอร์ตหรูจอดในที่มืด"], "sigma_bg")
        with c2: render_custom_select("🗣️ เสียงพากย์:", ["ทุ้มต่ำ ดุดัน", "สุขุมนุ่มลึก"], "sigma_voice")
        if st.button("🚀 ผลิตคลิปคำคม", type="primary"):
            st.session_state.sigma_prompt = smart_generate(f"สคริปต์คลิปสั้นคำคมสู้ชีวิต แนว: {topic} ภาพ: {st.session_state.get('sigma_bg')} เสียง: {st.session_state.get('sigma_voice')}. ข้อความขึ้นจอ 1 ประโยคเด็ดๆ แยก Prompt ภาพและวิดีโอ (พร้อม Audio Cues)")
        
        if st.session_state.sigma_prompt: st.text_area("📄 สคริปต์คำคม Sigma:", value=st.session_state.sigma_prompt, height=200, key="sigma_text_output")
    with tab_run:
        if st.session_state.sigma_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.sigma_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"sigma_btn_{i}"):
                        run_bot_dialog(i+1, s_text, [], i==0)

# =========================================================================================
# 🕶️ โหมด 8: 👻 ช่องเล่าเรื่องหลอน (Creepypasta)
# =========================================================================================
elif app_mode == "👻 ช่องเล่าเรื่องหลอน (Creepypasta)":
    st.markdown('<div class="main-header">👻 สตูดิโอนักเล่านิทานสยองขวัญ</div>', unsafe_allow_html=True)
    if 'creepy_prompt' not in st.session_state: st.session_state.creepy_prompt = ""

    tab_vid, tab_run = st.tabs(["⚙️ 1. พล็อตเรื่องและโทนภาพ", "🚀 2. รันบอท (Handoff)"])
    with tab_vid:
        story = st.text_area("📖 โครงเรื่องหลอน:", placeholder="พิมพ์พล็อตเรื่องสั้นๆ...")
        render_custom_select("🎨 สไตล์ภาพ:", ["Dark Fantasy หม่นๆ", "สมจริงน่ากลัว"], "creepy_style")
        if st.button("🚀 แบ่งฉากเรื่องหลอน", type="primary"):
            st.session_state.creepy_prompt = smart_generate(f"แบ่งฉากเล่าเรื่องผี โครงเรื่อง: {story} สไตล์: {st.session_state.get('creepy_style')}. แบ่ง 3 ฉาก แต่ละฉากมี Prompt สร้างภาพนิ่ง และ Prompt วิดีโอ (พร้อม Audio Cues เสียงคนเล่า)")
        
        if st.session_state.creepy_prompt: st.text_area("📄 สคริปต์เรื่องหลอน:", value=st.session_state.creepy_prompt, height=300, key="creepy_text_output")
    with tab_run:
        if st.session_state.creepy_prompt:
            scenes = [s for s in re.split(r'(?:\n|^)(?=\*?\*?\s*ฉากที่\s*\d+)', st.session_state.creepy_prompt) if "ฉากที่" in s]
            for i, s_text in enumerate(scenes):
                with st.expander(f"🎬 ฉากที่ {i+1}", expanded=True):
                    if st.button(f"⚙️ ตั้งค่าและรันบอท (ฉาก {i+1})", key=f"creepy_btn_{i}"):
                        run_bot_dialog(i+1, s_text, [], i==0)

# =========================================================================================
# 🎵 โหมด 9: 🕺 สายแดนซ์ชาเลนจ์ (Image Only)
# =========================================================================================
elif app_mode == "🕺 สายแดนซ์ชาเลนจ์ (Dance Character)":
    st.markdown('<div class="main-header">🕺 สตูดิโอปั้นนักเต้น AI (Motion Transfer)</div>', unsafe_allow_html=True)
    if 'dance_prompt' not in st.session_state: st.session_state.dance_prompt = ""

    tab_img, tab_run = st.tabs(["⚙️ 1. ปั้นนักเต้น", "🚀 2. รันหน้าปก/รูปนิ่ง"])
    with tab_img:
        c1, c2 = st.columns(2)
        with c1:
            render_custom_select("🐱 ตัวละคร:", ["แมวส้ม", "หมีแพนด้า"], "dance_actor")
            render_custom_select("👕 ชุดเต้น:", ["ชุดฮิปฮอป", "ชุดนักเรียน"], "dance_outfit")
        with c2:
            render_custom_select("🏡 ฉากหลัง:", ["สีขาวคลีนๆ", "ห้องสตูดิโอ"], "dance_bg")
            render_custom_select("🎨 สไตล์:", ["สมจริง 3D", "อนิเมะญี่ปุ่น"], "dance_style")
        if st.button("🚀 เจน Prompt นักเต้น", type="primary"):
            st.session_state.dance_prompt = smart_generate(f"Prompt สร้างภาพนิ่งภาษาอังกฤษ: {st.session_state.get('dance_actor')} ชุด {st.session_state.get('dance_outfit')} ฉาก {st.session_state.get('dance_bg')} สไตล์ {st.session_state.get('dance_style')}. (ต้องเป็นหน้าตรง Full body shot ท่ายืนนิ่งๆ เพื่อไปทำ AI Dance ต่อ)")
        
        if st.session_state.dance_prompt: st.text_area("📄 Prompt รูปนิ่งนักเต้น:", value=st.session_state.dance_prompt, height=200, key="dance_pos_text_output")
    with tab_run:
        if st.session_state.dance_prompt:
            if st.button("⚙️ รันบอทสร้างรูปนักเต้น", key="run_img_dance"):
                run_bot_dialog(0, st.session_state.dance_prompt, [], True, is_poster_only=True)

# =========================================================================================
# 🎵 โหมด 10: 🎶 ห้องอัดเสียงเพลงแปลง (Text Only)
# =========================================================================================
elif app_mode == "🎶 ห้องอัดเสียงเพลงแปลง (Parody Music)":
    st.markdown('<div class="main-header">🎶 ห้องอัดเสียงเพลงแปลง (AI Music Studio)</div>', unsafe_allow_html=True)
    topic = st.text_input("📌 หัวข้อ/เรื่องที่จะบ่นในเพลง:", placeholder="เช่น ราคายางตก...")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("อารมณ์:", ["ตลกร้าย/ประชดประชัน", "กวนโอ๊ย"], "music_mood")
        render_custom_select("แนวดนตรี:", ["ลูกทุ่งโจ๊ะๆ", "หมอลำซิ่ง", "แร็ปฮิปฮอป"], "music_genre")
    with c2:
        render_custom_select("เครื่องดนตรีเด่น:", ["กีตาร์โปร่ง", "เบสหนักๆ"], "music_inst")
    with c3:
        render_custom_select("นักร้อง:", ["ผู้ชายเสียงแหบสู้ชีวิต", "แร็ปเปอร์"], "music_vocal")
    if st.button("🚀 สั่ง AI แต่งเนื้อเพลง", type="primary"):
        res = smart_generate(f"แต่งเนื้อเพลงล้อเลียน หัวข้อ: {topic} แนว: {st.session_state.get('music_genre')} ดนตรี: {st.session_state.get('music_inst')} นักร้อง: {st.session_state.get('music_vocal')}. สร้าง 1. Prompt ดนตรีภาษาอังกฤษ 2. เนื้อเพลงภาษาไทยพร้อมโครงสร้าง [Intro, Chorus, Verse]")
        
        st.text_area("📄 ผลลัพธ์เนื้อเพลงแปลง:", value=res, height=400, key="music_parody_text_output")