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

# เพิ่มพารามิเตอร์ help_text เพื่อใช้ไฮไลท์คำแนะนำ
def render_custom_select(label, options, key, help_text=None):
    opt_list = options + ["พิมพ์กำหนดเอง..."]
    current_val = st.session_state.get(key, options[0])
    idx = options.index(current_val) if current_val in options else len(opt_list) - 1
    selected = st.selectbox(label, opt_list, index=idx, key=f"select_{key}", help=help_text)
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
# 💼 โหมด 1: 🎬 โฆษณาสินค้า (Ad Director) - [LOCKED - DO NOT MODIFY]
# =========================================================================================
elif app_mode == "🎬 โฆษณาสินค้า (Ad Director)":
    st.markdown('<div class="main-header">🎬 ระบบผู้กำกับโฆษณา AI</div>', unsafe_allow_html=True)
    if 'ad_product_text' not in st.session_state: st.session_state.ad_product_text = ""
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
                    st.warning("⚠️ กรุณาระบุหรือสกัดข้อมูลสินค้าในช่อง '📝 ข้อมูลสินค้า' ก่อนครับ เพื่อให้ AI นำไปวิเคราะห์")
                else:
                    with st.spinner("🧠 AI กำลังวิเคราะห์สินค้าและจับคู่ตัวเลือกที่เหมาะสม..."):
                        dur_options = '["Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"]'
                        if "6 วิ" in ai_dir_len: dur_options = '["Bumper Ads (6 วิ)"]'
                        elif "15-30" in ai_dir_len: dur_options = '["Shorts/Reels (15-30 วิ)"]'
                        elif "1 นาที" in ai_dir_len: dur_options = '["มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"]'
                        
                        plat_options = '["TikTok / Shopee Video", "Facebook Reels", "YouTube In-stream", "IG Story (เน้นภาพสวย)"]'
                        if "9:16" in ai_dir_ratio: plat_options = '["TikTok / Shopee Video", "IG Story (เน้นภาพสวย)"]'
                        elif "16:9" in ai_dir_ratio: plat_options = '["YouTube In-stream"]'
                        elif "1:1" in ai_dir_ratio: plat_options = '["Facebook Reels"]'

                        prompt = f"""คุณคือผู้กำกับโฆษณามืออาชีพ วิเคราะห์ข้อมูลสินค้าต่อไปนี้: "{st.session_state.ad_product_text}"
                        แล้วเลือกตัวเลือกที่เหมาะสมที่สุดเพื่อสร้างวิดีโอโปรโมท จากรายการด้านล่าง:
                        - ad_pres: ["ไม่มีพรีเซนเตอร์", "KOL / Influencer", "ผู้เชี่ยวชาญ / หมอ", "ผู้ใช้งานจริง (User)", "มาสคอตแบรนด์", "หญิงสาว", "ชายหนุ่ม"]
                        - ad_tone: ["เพื่อนป้ายยา", "ตื่นเต้นขายเก่ง", "พรีเมียม / หรูหรา", "ASMR (กระซิบ)", "เล่าเรื่องน่าติดตาม (Storytelling)", "ดุดันจริงจัง", "ตลกขบขัน"]
                        - ad_target: ["วัยรุ่น Gen Z", "คนทำงาน / มนุษย์เงินเดือน", "แม่และเด็ก", "สายรักษ์สุขภาพ", "ผู้สูงอายุ"]
                        - ad_lang: ["ภาษาไทยกลาง", "อีสานมาตรฐาน (ขอนแก่น/อุดรฯ)", "อีสานโคราช", "อีสานใต้ (สุรินทร์/บุรีรัมย์)", "ใต้ลึก (นครศรีธรรมราช)", "ใต้ตอนล่าง (สงขลา/หาดใหญ่)", "ใต้ฝั่งอันดามัน (ภูเก็ต)", "เหนือล้านนา (เชียงใหม่)", "เหนือตะวันออก (แพร่/น่าน)", "กลางเหน่อ (สุพรรณบุรี)", "ตะวันออก (ระยอง/จันทบุรี)", "อังกฤษ US Native", "อังกฤษ UK (บริติช)", "อังกฤษ Aussie (ออสเตรเลีย)"]
                        - ad_dur: {dur_options}
                        - ad_style: ["UGC (User Generated Content)", "Cinematic (สวยงามเหมือนภาพยนตร์)", "Vlog เที่ยว/กิน", "ซิทคอมสั้นตลกๆ", "Stop Motion", "3D Animation"]
                        - ad_story: ["PAS (ปัญหา-ทางแก้)", "Before / After", "AIDA (ดึงดูด-สนใจ-ต้องการ-ซื้อ)", "ขยี้ Pain Point", "สาธิตวิธีใช้ (How-to)"]
                        - ad_cta: ["กดตะกร้าด้านซ้ายล่าง", "ทักแชท", "แจกโค้ดส่วนลด", "ให้รีบซื้อก่อนหมด (FOMO)", "คลิกลิงก์หน้าโปรไฟล์", "สมัครสมาชิก"]
                        - ad_plat: {plat_options}
                        - ad_music: ["Pop สนุกสนาน", "Epic อลังการ", "Lofi (ชิลๆสบายๆ)", "EDM (ตื่นเต้นเร้าใจ)", "ดนตรีประกอบระทึกขวัญ", "ไม่มีเพลงเน้นเสียงพูด"]
                        - ad_color: ["สดใสสว่างคลีนๆ", "พาสเทลละมุนตา", "โทนดาร์กเท่ๆ (Dark/Moody)", "ขาวดำคลาสสิก", "นีออนไซเบอร์พังก์"]
                        - ad_cam: ["ระดับสายตา (Eye Level)", "ซูมใกล้ (Macro/Close-up)", "POV (มุมมองบุคคลที่ 1)", "มุมสูง (Drone/Top-down)", "มุมเอียง (Dutch Angle)"]
                        - ad_light: ["แสงธรรมชาติ (Daylight)", "แสงสตูดิโอ", "Golden Hour (แสงเย็น/พระอาทิตย์ตก)", "Cinematic Rim Light (แสงขอบ)", "แสงจัดจ้านสไตล์ป๊อป"]
                        - ad_text: ["โปรโมชั่นพิเศษ/ราคา", "ซับไตเติ้ลคำต่อคำ", "ไฮไลท์เฉพาะคำสำคัญ", "ป้ายราคาเด้งกระแทกตา", "ไม่มีข้อความ"]
                        - ad_pacing: ["ตัดฉับไว (Jump Cut)", "สมูทและสโลว์โมชั่น", "ตัดตามจังหวะเพลง (Beat Sync)", "Long Take (แช่กล้องนาน)"]
                        - ad_vfx: ["ไม่มีเอฟเฟกต์ (เน้นสมจริง)", "โทนฟิล์มเก่า (Retro/VHS)", "เทคนิคกลิทช์ (Cyberpunk Glitch)", "แสงแฟลร์ (Lens Flare)"]

                        ⚠️ กฎพิเศษในการตั้งค่า (Hard Constraints):
                        - เลือกตัวเลือกจากรายการที่กำหนดไว้เท่านั้น ห้ามคิดคำขึ้นมาเอง
                        - พิจารณาความยาวคลิป (ad_dur) และ แพลตฟอร์ม (ad_plat) จากตัวเลือกที่มีให้จำกัดอย่างเคร่งครัด

                        ตอบกลับมาเป็น JSON Format เท่านั้น
                        """
                        try:
                            res = smart_generate(prompt)
                            json_str = re.search(r'\{.*\}', res, re.DOTALL).group(0)
                            ai_config = json.loads(json_str)
                            for k, v in ai_config.items(): st.session_state[k] = v
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ AI เกิดการขัดข้อง กรุณาลองใหม่อีกครั้ง ({e})")

        with col_res:
            if st.button("🔄 รีเซ็ตการตั้งค่าวิดีโอ (Reset)", key="ad_vid_res", use_container_width=True):
                st.session_state.ad_video_prompt = ""
                vid_keys = ["ad_pres", "ad_tone", "ad_target", "ad_lang", "ad_dur", "ad_style", "ad_story", "ad_cta", "ad_plat", "ad_music", "ad_color", "ad_cam", "ad_light", "ad_text", "ad_pacing", "ad_vfx"]
                for k in vid_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"select_{k}" in st.session_state: del st.session_state[f"select_{k}"]
                    if f"custom_{k}" in st.session_state: del st.session_state[f"custom_{k}"]
                st.rerun()
                
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 👤 พรีเซนเตอร์:", ["ไม่มีพรีเซนเตอร์", "KOL / Influencer", "ผู้เชี่ยวชาญ / หมอ", "ผู้ใช้งานจริง (User)", "มาสคอตแบรนด์", "หญิงสาว", "ชายหนุ่ม"], "ad_pres", "ผู้เชี่ยวชาญ=อาหารเสริม/สกินแคร์, ผู้ใช้งานจริง=ของใช้ทั่วไป")
            render_custom_select("2. 🗣️ น้ำเสียง:", ["เพื่อนป้ายยา", "ตื่นเต้นขายเก่ง", "พรีเมียม / หรูหรา", "ASMR (กระซิบ)", "เล่าเรื่องน่าติดตาม (Storytelling)", "ดุดันจริงจัง", "ตลกขบขัน"], "ad_tone", "ASMR=สินค้าของกิน/สกินแคร์, ตลก=เพิ่มการแชร์")
            render_custom_select("3. 🎯 กลุ่มเป้าหมาย:", ["วัยรุ่น Gen Z", "คนทำงาน / มนุษย์เงินเดือน", "แม่และเด็ก", "สายรักษ์สุขภาพ", "ผู้สูงอายุ"], "ad_target", "ช่วยให้ AI เลือกใช้ศัพท์ให้ตรงกับวัยของลูกค้า")
            render_custom_select("4. 🌐 ภาษาและสำเนียง:", ["ภาษาไทยกลาง", "อีสานมาตรฐาน (ขอนแก่น/อุดรฯ)", "อีสานโคราช", "อีสานใต้ (สุรินทร์/บุรีรัมย์)", "ใต้ลึก (นครศรีธรรมราช)", "ใต้ตอนล่าง (สงขลา/หาดใหญ่)", "ใต้ฝั่งอันดามัน (ภูเก็ต)", "เหนือล้านนา (เชียงใหม่)", "เหนือตะวันออก (แพร่/น่าน)", "กลางเหน่อ (สุพรรณบุรี)", "ตะวันออก (ระยอง/จันทบุรี)", "อังกฤษ US Native", "อังกฤษ UK (บริติช)", "อังกฤษ Aussie (ออสเตรเลีย)"], "ad_lang", "เลือกภาษาให้ตรงกับถิ่นฐานกลุ่มเป้าหมายเพื่อความเนียน")
            render_custom_select("5. ⏳ ความยาวคลิป:", ["Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"], "ad_dur", "Shorts/Reels=ดันยอดวิวการเข้าถึง, Long-form=เน้นข้อมูลแน่น")
            render_custom_select("6. 🎥 สไตล์โฆษณา:", ["UGC (User Generated Content)", "Cinematic (สวยงามเหมือนภาพยนตร์)", "Vlog เที่ยว/กิน", "ซิทคอมสั้นตลกๆ", "Stop Motion", "3D Animation"], "ad_style", "UGC=เน้นความจริงใจ/รีวิว, Cinematic=สร้างแบรนด์หรู")
        with c2:
            render_custom_select("7. 📖 การเล่าเรื่อง:", ["PAS (ปัญหา-ทางแก้)", "Before / After", "AIDA (ดึงดูด-สนใจ-ต้องการ-ซื้อ)", "ขยี้ Pain Point", "สาธิตวิธีใช้ (How-to)"], "ad_story", "PAS และ Pain Point เหมาะกับสินค้าแก้ปัญหา (สิว/ปวดเมื่อย)")
            render_custom_select("8. 👉 ปิดการขาย (CTA):", ["กดตะกร้าด้านซ้ายล่าง", "ทักแชท", "แจกโค้ดส่วนลด", "ให้รีบซื้อก่อนหมด (FOMO)", "คลิกลิงก์หน้าโปรไฟล์", "สมัครสมาชิก"], "ad_cta", "FOMO=กระตุ้นการตัดสินใจทันที")
            render_custom_select("9. 📱 แพลตฟอร์ม:", ["TikTok / Shopee Video", "Facebook Reels", "YouTube In-stream", "IG Story (เน้นภาพสวย)"], "ad_plat", "กำหนดสัดส่วนภาพและพฤติกรรมคนดูบนแพลตฟอร์ม")
            render_custom_select("10. 🎵 ดนตรี:", ["Pop สนุกสนาน", "Epic อลังการ", "Lofi (ชิลๆสบายๆ)", "EDM (ตื่นเต้นเร้าใจ)", "ดนตรีประกอบระทึกขวัญ", "ไม่มีเพลงเน้นเสียงพูด"], "ad_music", "Lofi=คลิป ASMR/สโลว์ไลฟ์, EDM=โปรโมชั่น/ของเซลล์")
            render_custom_select("11. 🎨 โทนสี:", ["สดใสสว่างคลีนๆ", "พาสเทลละมุนตา", "โทนดาร์กเท่ๆ (Dark/Moody)", "ขาวดำคลาสสิก", "นีออนไซเบอร์พังก์"], "ad_color", "พาสเทล=บิวตี้, นีออน/ดาร์ก=แก็ดเจ็ต/เกมมิ่ง")
        with c3:
            render_custom_select("12. 🎥 มุมกล้อง:", ["ระดับสายตา (Eye Level)", "ซูมใกล้ (Macro/Close-up)", "POV (มุมมองบุคคลที่ 1)", "มุมสูง (Drone/Top-down)", "มุมเอียง (Dutch Angle)"], "ad_cam", "POV=ทำให้คนดูรู้สึกเหมือนใช้งานเอง, มุมเอียง=ฉากแอคชั่น/ตื่นเต้น")
            render_custom_select("13. 💡 แสงและบรรยากาศ:", ["แสงธรรมชาติ (Daylight)", "แสงสตูดิโอ", "Golden Hour (แสงเย็น/พระอาทิตย์ตก)", "Cinematic Rim Light (แสงขอบ)", "แสงจัดจ้านสไตล์ป๊อป"], "ad_light", "Golden hour=ฟีลลิ่งอบอุ่น/สกินแคร์")
            render_custom_select("14. ✍️ ข้อความบนจอ:", ["โปรโมชั่นพิเศษ/ราคา", "ซับไตเติ้ลคำต่อคำ", "ไฮไลท์เฉพาะคำสำคัญ", "ป้ายราคาเด้งกระแทกตา", "ไม่มีข้อความ"], "ad_text", "TikTok/Reels ขาดไม่ได้คือซับไตเติ้ลเพื่อหยุดนิ้วคนดู")
            render_custom_select("15. 🎞️ จังหวะการตัดต่อ:", ["ตัดฉับไว (Jump Cut)", "สมูทและสโลว์โมชั่น", "ตัดตามจังหวะเพลง (Beat Sync)", "Long Take (แช่กล้องนาน)"], "ad_pacing", "Jump cut=วัยรุ่น/สั้นกระชับ, สโลว์โมชั่น=โชว์ดีเทล/สินค้าหรู")
            render_custom_select("16. ✨ เอฟเฟกต์ (VFX):", ["ไม่มีเอฟเฟกต์ (เน้นสมจริง)", "โทนฟิล์มเก่า (Retro/VHS)", "เทคนิคกลิทช์ (Cyberpunk Glitch)", "แสงแฟลร์ (Lens Flare)"], "ad_vfx", "VHS=วินเทจ/Y2K, Glitch=สินค้าเทคโนโลยี/แฟชั่น")

        if st.button("🚀 เริ่มเขียนสคริปต์วิดีโอ & แคปชั่นป้ายยา", type="primary", use_container_width=True):
            prompt = f"""คุณคือผู้กำกับโฆษณาระดับโลก (Commercial Director) หน้าที่ของคุณคือการเขียนสคริปต์โฆษณาสินค้าแบบแบ่งฉาก (ฉากละ 8 วินาที) เพื่อนำไปเจนภาพและวิดีโอบน AI (Veo 3.1) โดยอ้างอิงจากการตั้งค่าต่อไปนี้:
สินค้า: {st.session_state.ad_product_text}
พรีเซนเตอร์: {st.session_state.get('ad_pres')}
เสียง: {st.session_state.get('ad_tone')}
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

⚠️ กฎเหล็กในการสร้างฉาก (สำคัญมาก ต้องทำตามโครงสร้างนี้เป๊ะๆ):
- กฎเรื่องสรรพนามและน้ำเสียง (Gender & Pronoun Rule): ตรวจสอบ "พรีเซนเตอร์", "กลุ่มเป้าหมาย" และ "สินค้า" หากเป็นผู้ชายหรือสินค้าผู้ชาย ให้ใช้คำพูดและคำสร้อยแบบผู้ชายแท้ๆ (เช่น ผม, ครับ, โคตรเท่, จัดเลยพี่, หวัดดีพวก) ห้ามใช้คำศัพท์ผู้หญิง (เช่น เห้ยแก, ดีย์, สิคะ, คร้า) เด็ดขาด หากเป็นผู้หญิงหรือสินค้าผู้หญิงให้ใช้คำพูดผู้หญิง หากไม่ระบุให้ใช้ภาษากลางๆที่เข้าถึงได้ทุกคน

🎬 ฉากที่ 1: เปิดตัวดึงดูดสายตา (The Hook - 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายภาพรวมว่าเกิดอะไรขึ้น
* ข้อความบนจอ (Text on Screen): (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (เขียนตามสำเนียง ภาษา และกฎสรรพนามเพศที่กำหนด)
* Prompt สร้างภาพนิ่ง: (ภาษาอังกฤษ - สำหรับ Nano Banana 2) อธิบายหน้าตาพรีเซนเตอร์, เสื้อผ้า, สถานที่, แสง, โทนสี และมุมกล้องตั้งต้นอย่างละเอียดที่สุด เพื่อใช้เป็นภาพอ้างอิง (เขียนแบบบรรทัดเดียวห้ามขึ้นบรรทัดใหม่)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ - สำหรับ Veo 3.1) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ โดยระบุจังหวะตัดกล้อง (เช่น 0-4s: [แอคชั่น], 4-8s: Quick cut to [แอคชั่นใหม่]) และลงท้ายด้วยคำว่า "Audio: [เสียง SFX/ดนตรี]"

🎬 ฉากที่ 2, 3, 4... : ต่อเนื่องเนื้อหา (Extend Scene - ฉากละ 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายแอคชั่นที่สานต่อจากฉากที่แล้ว เพื่อเดินเรื่องไปสู่การปิดการขาย
* ข้อความบนจอ (Text on Screen): (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (ขยี้ Pain Point หรือ Call to Action ตามกฎสรรพนามเพศ)
* (ห้ามเขียน Prompt สร้างภาพนิ่งในฉากที่ 2 เป็นต้นไปเด็ดขาด)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ เริ่มด้วย "Continuing from the previous frame..." ระบุจังหวะตัดกล้อง และลงท้ายด้วย "Audio: [เสียงประกอบที่สอดคล้อง]"

📱 ส่วนท้ายสุด: แคปชั่นป้ายยา 3 แพลตฟอร์ม
- TikTok: เน้นฮุกกระแส + แฮชแท็กมาแรง (ความยาวปกติ)
- Facebook (Shopee Affiliate): เน้นสตอรี่เทลลิ่งโน้มน้าวให้กดลิงก์ (ความยาวปกติ)
- Shopee Video/Feed: ฮาร์ดเซลล์กระชับ *(กฎเหล็ก: เฉพาะข้อ Shopee นี้เท่านั้น ที่ตัวอักษรของข้อความและแฮชแท็กบวกกันแล้วต้องไม่เกิน 150 ตัวอักษร ห้ามเกินเด็ดขาด)*
"""
            st.session_state.ad_video_prompt = smart_generate(prompt)

        if st.session_state.ad_video_prompt: st.code(st.session_state.ad_video_prompt, language="markdown")

    with tab_poster:
        st.markdown("##### 🎯 ล็อกเป้าหมายให้ AI (Pre-AI Controls - Poster)")
        ai_dir_ratio_pos = st.selectbox("📏 ล็อกสัดส่วนภาพหน้าปก (Aspect Ratio):", ["🤖 ปล่อย AI คิดเอง (Free Style)", "16:9 (YouTube/TV)", "4:3 (หน้าจอมาตรฐาน)", "1:1 (Facebook/IG Post)", "3:4 (Portrait Feed)", "9:16 (TikTok/Reels/Shorts)"], key="ai_dir_ratio_pos")

        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าโปสเตอร์อัตโนมัติ", key="pos_ai", use_container_width=True):
                if not st.session_state.ad_product_text:
                    st.warning("⚠️ กรุณาระบุหรือสกัดข้อมูลสินค้าในช่อง '📝 ข้อมูลสินค้า' ก่อนครับ")
                else:
                    with st.spinner("🧠 AI กำลังสแกนรูปภาพและเลือกดีไซน์โปสเตอร์ที่เป๊ะที่สุด..."):
                        ratio_constraint_pos = ""
                        if "16:9" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (pos_comp) และมุมกล้องให้เหมาะสมกับอัตราส่วนแนวนอนกว้าง 16:9'
                        elif "4:3" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (pos_comp) ให้เหมาะสมกับแนวนอนมาตรฐาน 4:3'
                        elif "1:1" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (pos_comp) ให้เหมาะสมกับสัดส่วนจัตุรัส 1:1 เน้นจุดสนใจตรงกลาง'
                        elif "3:4" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (pos_comp) ให้เหมาะสมกับแนวตั้ง 3:4'
                        elif "9:16" in ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบ (pos_comp) และตำแหน่งข้อความ (pos_text_pos) ให้เหมาะสมกับแนวตั้ง 9:16 โดยเว้น Safe Zone ให้มือถือเสมอ'

                        prompt_contents = []
                        if st.session_state.ad_imgs:
                            prompt_contents = [Image.open(img_file) for img_file in st.session_state.ad_imgs]
                        
                        prompt_text = f"""วิเคราะห์ข้อมูลสินค้าและภาพเหล่านี้: "{st.session_state.ad_product_text}"
                        แล้วเลือกตัวเลือกที่เหมาะสมที่สุดเพื่อออกแบบโปสเตอร์/หน้าปกโฆษณา ระดับ Art Director จากรายการด้านล่าง:
                        - pos_style: ["High-end E-commerce Catalog (หรูหราแคตตาล็อก)", "Social Media Clickbait Ad (หน้าปกไวรัลดึงดูดตา)", "Minimalist Lifestyle (คลีนๆ มินิมอล)", "Cyberpunk / Neon Product (ล้ำสมัย นีออน)", "Vintage / Retro Film (วินเทจ ฟิล์มคลาสสิก)", "Hyper-Realistic 3D Render (3D สมจริงขั้นสุด)"]
                        - pos_color: ["สว่างสดใสคลีนๆ (Clean & Bright)", "โทนเข้มดุดันพรีเมียม (Dark & Moody)", "พาสเทลละมุนตา (Soft Pastel)", "สีสันจัดจ้านตัดกัน (Vibrant & Contrast)", "คุมโทนสีเดียว (Monochromatic)", "หรูหรา ดำ-ทอง (Black & Gold)"]
                        - pos_cam: ["ระดับสายตา (Eye-level)", "มุมสูง (Top-down / Flat Lay)", "ซูมใกล้เจาะดีเทล (Macro Close-up)", "มุมเสยดูยิ่งใหญ่ (Low Angle)", "มุมกว้างเห็นบรรยากาศ (Wide Angle)"]
                        - pos_light: ["แสงธรรมชาติริมหน้าต่าง (Soft Daylight)", "แสงสตูดิโอเคลียร์ชัด (Studio Lighting)", "แสงแข็งเงาชัด (Hard Light & Bold Shadows)", "แสงนีออนสะท้อน (Neon Reflections)", "แสงพระอาทิตย์ตก (Golden Hour)"]
                        - pos_bg: ["ฉากสตูดิโอสีพื้นฐาน (Solid Studio Color)", "แท่นโชว์สินค้า (Minimalist Podium)", "บรรยากาศใช้งานจริง (Lifestyle Context)", "ธรรมชาติ (Nature/Outdoors)", "ฉากหลังเบลอ (Bokeh/Depth of Field)"]
                        - pos_comp: ["กฎสามส่วน (Rule of Thirds)", "สมมาตรตรงกลางเป๊ะ (Symmetrical)", "สไตล์หน้าปกนิตยสาร (Magazine Layout)", "พื้นที่ว่างเยอะ (Negative Space)"]
                        - pos_tex: ["คลีนและเงางาม (Glossy/Clean)", "ภาพฟิล์มมีเกรน (Film Grain)", "หยดน้ำเกาะสดชื่น (Water Drops)", "ควันหรือหมอกบางๆ (Fog/Mist)", "สะท้อนพื้นกระจก (Mirror Reflection)"]
                        - pos_font: ["ฟอนต์ตัวหนากระแทกตา (Bold/Impact)", "ฟอนต์มินิมอลเรียบหรู (Minimalist/Sans-serif)", "ฟอนต์สไตล์สตรีท (Streetwear/Graffiti)", "ฟอนต์ลายมือดูเป็นกันเอง (Handwritten)", "ฟอนต์อาร์ตๆ มีสไตล์ (Artistic/Serif)"]
                        - pos_text_pos: ["บนซ้าย (Top-Left)", "บนขวา (Top-Right)", "พาดกลางภาพ (Center Bold)", "ล่างซ้าย (Bottom-Left)", "ล่างขวา (Bottom-Right)", "เว้นขวาไว้ (Safe Zone มือถือ)"]
                        - pos_text_main: ["โปรโมชั่นพิเศษ/Sale", "ป้าย Flash Sale", "ข้อความรีวิวจากลูกค้า", "คำโปรยสั้นๆ กระแทกใจ", "ชื่อสินค้าโดดๆ", "ไม่มีข้อความ"]
                        - pos_text_sub: ["ส่งฟรี!", "ซื้อ 1 แถม 1", "ของแท้ 100%", "รีวิว 5 ดาว", "ไม่มีข้อความ"]

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
            if st.button("🔄 รีเซ็ตการตั้งค่าโปสเตอร์", key="pos_res", use_container_width=True):
                st.session_state.ad_poster_prompt = ""
                st.session_state.ad_poster_prompt_th = ""
                pos_keys = ["pos_style", "pos_color", "pos_cam", "pos_light", "pos_bg", "pos_comp", "pos_tex", "pos_font", "pos_text_pos", "pos_text_main", "pos_text_sub"]
                for k in pos_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"select_{k}" in st.session_state: del st.session_state[f"select_{k}"]
                    if f"custom_{k}" in st.session_state: del st.session_state[f"custom_{k}"]
                st.rerun()

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 🎨 สไตล์ภาพ (Style):", ["High-end E-commerce Catalog (หรูหราแคตตาล็อก)", "Social Media Clickbait Ad (หน้าปกไวรัลดึงดูดตา)", "Minimalist Lifestyle (คลีนๆ มินิมอล)", "Cyberpunk / Neon Product (ล้ำสมัย นีออน)", "Vintage / Retro Film (วินเทจ ฟิล์มคลาสสิก)", "Hyper-Realistic 3D Render (3D สมจริงขั้นสุด)"], "pos_style", "High-end=แบรนด์เนม/สกินแคร์, Clickbait=คลิปขายของไวรัล, 3D Render=แกดเจ็ต")
            render_custom_select("2. 🌈 โทนสี (Color):", ["สว่างสดใสคลีนๆ (Clean & Bright)", "โทนเข้มดุดันพรีเมียม (Dark & Moody)", "พาสเทลละมุนตา (Soft Pastel)", "สีสันจัดจ้านตัดกัน (Vibrant & Contrast)", "คุมโทนสีเดียว (Monochromatic)", "หรูหรา ดำ-ทอง (Black & Gold)"], "pos_color", "Contrast=ดึงดูดสายตาเวลาไถฟีด, Black & Gold=อัปราคาดูแพง")
            render_custom_select("3. 📸 มุมกล้อง (Camera):", ["ระดับสายตา (Eye-level)", "มุมสูง (Top-down / Flat Lay)", "ซูมใกล้เจาะดีเทล (Macro Close-up)", "มุมเสยดูยิ่งใหญ่ (Low Angle)", "มุมกว้างเห็นบรรยากาศ (Wide Angle)"], "pos_cam", "Flat Lay=จัดวางของหลายชิ้นแบบเก๋ๆ, Macro=โชว์เนื้อครีมหรือวัสดุ")
            render_custom_select("4. 💡 แสงเงา (Lighting):", ["แสงธรรมชาติริมหน้าต่าง (Soft Daylight)", "แสงสตูดิโอเคลียร์ชัด (Studio Lighting)", "แสงแข็งเงาชัด (Hard Light & Bold Shadows)", "แสงนีออนสะท้อน (Neon Reflections)", "แสงพระอาทิตย์ตก (Golden Hour)"], "pos_light", "Hard Light=แฟชั่นจ๋า/สตรีท, Golden Hour=อบอุ่น/สกินแคร์ออร์แกนิก")
        with c2:
            render_custom_select("5. 🏞️ พื้นหลัง (Background):", ["ฉากสตูดิโอสีพื้นฐาน (Solid Studio Color)", "แท่นโชว์สินค้า (Minimalist Podium)", "บรรยากาศใช้งานจริง (Lifestyle Context)", "ธรรมชาติ (Nature/Outdoors)", "ฉากหลังเบลอ (Bokeh/Depth of Field)"], "pos_bg", "Podium=ทำให้สินค้าเด่นเด้งขึ้นมาทันที")
            render_custom_select("6. 📐 การจัดองค์ประกอบ (Composition):", ["กฎสามส่วน (Rule of Thirds)", "สมมาตรตรงกลางเป๊ะ (Symmetrical)", "สไตล์หน้าปกนิตยสาร (Magazine Layout)", "พื้นที่ว่างเยอะ (Negative Space)"], "pos_comp", "Magazine Layout=เผื่อที่ให้ AI ใส่ข้อความแบบลงตัว")
            render_custom_select("7. 🌟 พื้นผิวและเอฟเฟกต์ (Texture):", ["คลีนและเงางาม (Glossy/Clean)", "ภาพฟิล์มมีเกรน (Film Grain)", "หยดน้ำเกาะสดชื่น (Water Drops)", "ควันหรือหมอกบางๆ (Fog/Mist)", "สะท้อนพื้นกระจก (Mirror Reflection)"], "pos_tex", "Water Drops=เครื่องดื่ม/น้ำหอม, Film Grain=เสื้อผ้าวินเทจ")
        with c3:
            render_custom_select("8. 🔠 สไตล์ฟอนต์ (Typography):", ["ฟอนต์ตัวหนากระแทกตา (Bold/Impact)", "ฟอนต์มินิมอลเรียบหรู (Minimalist/Sans-serif)", "ฟอนต์สไตล์สตรีท (Streetwear/Graffiti)", "ฟอนต์ลายมือดูเป็นกันเอง (Handwritten)", "ฟอนต์อาร์ตๆ มีสไตล์ (Artistic/Serif)"], "pos_font", "Bold=สายกระตุ้นยอดขาย, Sans-serif=สายคลีนดูแพง")
            render_custom_select("9. 📍 ตำแหน่งข้อความ (Text Placement):", ["บนซ้าย (Top-Left)", "บนขวา (Top-Right)", "พาดกลางภาพ (Center Bold)", "ล่างซ้าย (Bottom-Left)", "ล่างขวา (Bottom-Right)", "เว้นขวาไว้ (Safe Zone มือถือ)"], "pos_text_pos", "Safe Zone=สำหรับแนวตั้ง 9:16 หลบปุ่ม Like/Share ของ TikTok")
            render_custom_select("10. 📢 พาดหัวหลัก (Main Headline):", ["โปรโมชั่นพิเศษ/Sale", "ป้าย Flash Sale", "ข้อความรีวิวจากลูกค้า", "คำโปรยสั้นๆ กระแทกใจ", "ชื่อสินค้าโดดๆ", "ไม่มีข้อความ"], "pos_text_main", "คำใหญ่เด่นสุด กระแทกตา AI จะเรนเดอร์ได้แม่นยำกว่าประโยคยาวๆ")
            render_custom_select("11. 🏷️ ป้ายโปรโมชั่น (Sub-text):", ["ส่งฟรี!", "ซื้อ 1 แถม 1", "ของแท้ 100%", "รีวิว 5 ดาว", "ไม่มีข้อความ"], "pos_text_sub", "ข้อความรอง/ป้ายเล็กๆ (เว้นว่างได้ถ้าไม่ต้องการ)")
        
        if st.button("🚀 เริ่มสร้าง Prompt โปสเตอร์ (Nano Banana 2)", type="primary", use_container_width=True):
            with st.spinner("🧠 AI กำลังแต่ง Prompt และแยกหน้าจอแปลภาษา..."):
                prompt = f"""คุณคือนักเขียน Prompt (Prompt Engineer) ระดับโลกสำหรับ AI สร้างภาพ 'Nano Banana 2' (Gemini 3 Flash Image)

ข้อมูลสำหรับการสร้างหน้าปก:
- สินค้า: {st.session_state.ad_product_text}
- สไตล์ภาพ: {st.session_state.get('pos_style')}
- โทนสี: {st.session_state.get('pos_color')}
- มุมกล้อง: {st.session_state.get('pos_cam')}
- แสงเงา: {st.session_state.get('pos_light')}
- พื้นหลัง: {st.session_state.get('pos_bg')}
- องค์ประกอบ: {st.session_state.get('pos_comp')}
- พื้นผิว/VFX: {st.session_state.get('pos_tex')}
- ฟอนต์: {st.session_state.get('pos_font')}
- ตำแหน่งข้อความ: {st.session_state.get('pos_text_pos')}
- พาดหัวหลัก: "{st.session_state.get('pos_text_main')}"
- ข้อความรอง: "{st.session_state.get('pos_text_sub')}"

**กฎเหล็กในการแต่ง Prompt (STRICT RULES):**
1. **ห้ามแปลข้อความ (DO NOT TRANSLATE TEXT):** คำว่า "{st.session_state.get('pos_text_main')}" และ "{st.session_state.get('pos_text_sub')}" ต้องถูกเก็บไว้เป็นภาษาไทยในเครื่องหมายคำพูดแบบเป๊ะๆ ห้ามแปลเป็นภาษาอังกฤษเด็ดขาด! (ยกเว้นผู้ใช้พิมพ์คำว่า "ไม่มีข้อความ" ให้เว้นไว้ไม่ต้องเขียน)
2. โครงสร้าง Prompt ภาษาอังกฤษ: เขียนเป็น 1 ย่อหน้า อธิบายรายละเอียดให้ครบถ้วน ต้องมีประโยคเกี่ยวกับการเรนเดอร์ข้อความ เช่น `The text "{st.session_state.get('pos_text_main')}" is clearly rendered using {st.session_state.get('pos_font')} typography placed at {st.session_state.get('pos_text_pos')}.`
3. ห้ามมั่ว (Anti-Hallucination): เขียนทิ้งท้ายใน Prompt ภาษาอังกฤษด้วยคำว่า `STRICTLY render ONLY the requested text. DO NOT add extra icons, stars, shopping carts, or random text. DO NOT hallucinate gibberish text on the packaging.`
4. คำอธิบายภาษาไทย (Thai Translation): แปลเนื้อหาของ Prompt อธิบายให้ผู้ใช้คนไทยอ่านเข้าใจ ว่าคุณสั่ง AI จัดแสง มุมกล้อง และวางข้อความไว้ตรงไหนบ้าง

**รูปแบบการตอบกลับ (JSON FORMAT ONLY):**
ตอบกลับมาเป็น JSON ตามโครงสร้างนี้เท่านั้น ห้ามมีข้อความอื่นปน
{{
    "english_prompt": "Prompt สร้างภาพนิ่ง: [Prompt ภาษาอังกฤษทั้งหมดตามกฎ]",
    "thai_translation": "[คำแปล Prompt และคำอธิบายเป็นภาษาไทย เพื่อให้คนอ่านเข้าใจ]"
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
            st.info(f"**สไตล์:** {st.session_state.get('pos_style')} | **โทนสี:** {st.session_state.get('pos_color')} | **ฟอนต์:** {st.session_state.get('pos_font')}\n\n**พาดหัวหลัก:** {st.session_state.get('pos_text_main')} | **ป้ายรอง:** {st.session_state.get('pos_text_sub')}")
            
            c_eng, c_th = st.columns(2)
            with c_eng:
                st.success("🇬🇧 คำสั่งภาษาอังกฤษ (ส่งให้ระบบ Handoff/บอท)")
                st.code(st.session_state.ad_poster_prompt, language="markdown")
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
# 🍰 โหมด 2: 🍰 รีวิวร้านตัวเอง (UGC Vlogger) - [UPGRADED POSTER TAB]
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
        col_ai_dir1, col_ai_dir2 = st.columns(2)
        with col_ai_dir1:
            ugc_ai_dir_len = st.selectbox("⏱️ ล็อกความยาวคลิป:", ["🤖 ปล่อย AI คิดเอง (Free Style)", "⚡ บังคับสั้นกระแทกตา (Bumper 6 วิ)", "📱 บังคับคลิปกระแส (Shorts/Reels 15-30 วิ)", "🎬 บังคับคลิปเล่าเรื่อง (1 นาทีขึ้นไป)"], key="ugc_ai_dir_len")
        with col_ai_dir2:
            ugc_ai_dir_ratio = st.selectbox("📏 ล็อกสัดส่วนภาพ:", ["🤖 ปล่อย AI คิดเอง (Free Style)", "📱 แนวตั้ง (9:16) - เหมาะกับมือถือ", "📺 แนวนอน (16:9) - เหมาะกับ YouTube/TV", "⬛ จัตุรัส (1:1) - เหมาะกับ Facebook/IG Feed"], key="ugc_ai_dir_ratio")

        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าอัตโนมัติ (Auto-Fill)", key="ugc_ai", use_container_width=True):
                if not st.session_state.ugc_shop_name and not st.session_state.ugc_menu:
                    st.warning("⚠️ กรุณาระบุชื่อร้านหรือเมนูเด็ดก่อนครับ เพื่อให้ AI นำไปวิเคราะห์")
                else:
                    with st.spinner("🧠 AI กำลังสแกนรูปภาพและบริบทของร้าน..."):
                        dur_options = '["Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"]'
                        if "6 วิ" in ugc_ai_dir_len: dur_options = '["Bumper Ads (6 วิ)"]'
                        elif "15-30" in ugc_ai_dir_len: dur_options = '["Shorts/Reels (15-30 วิ)"]'
                        elif "1 นาที" in ugc_ai_dir_len: dur_options = '["มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"]'

                        ugc_context = f"ร้าน: {st.session_state.get('ugc_shop_name', '')} | เมนู: {st.session_state.get('ugc_menu', '')} | พิกัด: {st.session_state.get('ugc_location', '')} | บรีฟพิเศษ: {st.session_state.get('ugc_extra_brief', '')}"
                        prompt_contents = []
                        if st.session_state.ugc_imgs:
                            prompt_contents = [Image.open(img_file) for img_file in st.session_state.ugc_imgs]
                        
                        prompt_text = f"""คุณคือผู้กำกับคลิปไวรัลและ Vlogger ระดับโปร วิเคราะห์ข้อมูลร้านและเมนูต่อไปนี้: "{ugc_context}"
                        (และรูปภาพถ้ามี) แล้วเลือกตัวเลือกที่เหมาะสมที่สุดเพื่อสร้างคลิปรีวิวร้าน จากรายการด้านล่าง:
                        
                        - ugc_actor: ["เจ้าของร้านใจดี/เป็นกันเอง", "วัยรุ่นเทสดี (Cafe Hopper)", "สายกินจุ (Mukbang)", "นักวิจารณ์อาหาร (ด่าไปกินไป/เรียลๆ)", "เชฟทำอาหาร/ผู้เชี่ยวชาญ", "พนักงานเสิร์ฟสายฮา", "ไม่มีคน (เน้นอาหาร/บรรยากาศ)"]
                        - ugc_tone: ["ASMR (เน้นเสียงเคี้ยว/ทำอาหาร)", "เล่าสตอรี่สู้ชีวิต (Storytelling)", "ตื่นเต้นอวยยศ (Hype)", "รีวิวตามจริงไม่อวย (Honest Review)", "ตลกขบขัน/ซิทคอม", "ดุดันจริงจัง (Hardcore)"]
                        - ugc_cam: ["ถือกล้องเซลฟี่เดินเข้าร้าน (Vlog POV)", "ตั้งกล้องกินโชว์ (Static/Tabletop)", "มุมมองแทนสายตาตอนกิน (First-person POV)", "ตากล้องแอบถ่าย (Third-person/Candid)", "ซูมเจาะอาหารยั่วๆ (Macro/B-roll)"]
                        - ugc_vibe: ["สตรีทฟู้ดริมทาง (Street Food/Local)", "คาเฟ่มินิมอล (Minimalist/Clean)", "หรูหราภัตตาคาร (Fine Dining)", "ร้านลับในซอย (Hidden Gem/Cozy)", "โฮมมี่ทำกินเองที่บ้าน (Home-cooked)"]
                        - ugc_lang: ["ภาษาไทยกลาง", "อีสานมาตรฐาน", "ภาษาใต้", "ภาษาเหนือ", "อังกฤษ (English)"]
                        - ugc_music: ["เพลงฮิตแผ่นเสียงรันเวย์ (Trendy TikTok)", "Acoustic ชิลๆ (Cafe Vibe)", "โจ๊ะๆ รถแห่ (Fun Thai Local)", "Lo-fi สบายๆ", "Epic ยิ่งใหญ่อลังการ", "ไม่มีเพลง (เน้นเสียง ASMR/เสียงบรรยากาศ)"]
                        - ugc_cta: ["ปักหมุดแผนที่ร้าน/ชวนมากิน", "แจกโปรโมชั่นหน้าร้าน", "สั่งผ่านแอปเดลิเวอรี่ (Grab/Lineman)", "กดตะกร้าสั่งซื้อ (ขายอาหารแห้ง/สำเร็จรูป)", "กดติดตามรอคลิปหน้า"]
                        - ugc_pacing: ["ตัดฉับไว (Jump Cut)", "สมูทและสโลว์โมชั่นยั่วๆ", "ตัดตามจังหวะเพลง (Beat Sync)", "Long Take (แช่กล้องนานให้เห็นความเรียล)"]
                        - ugc_text_overlay: ["บรรยายความอร่อยคำต่อคำ", "ซับไตเติ้ล", "ป้ายราคาเด้งกระแทกตา", "คะแนนรีวิวดาว", "ไม่มีข้อความ"]
                        - ugc_dur: {dur_options}

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
                vid_keys = ["ugc_actor", "ugc_tone", "ugc_cam", "ugc_vibe", "ugc_lang", "ugc_music", "ugc_cta", "ugc_pacing", "ugc_text_overlay", "ugc_dur"]
                for k in vid_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"select_{k}" in st.session_state: del st.session_state[f"select_{k}"]
                    if f"custom_{k}" in st.session_state: del st.session_state[f"custom_{k}"]
                st.rerun()
                
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 👤 คาแรคเตอร์ผู้รีวิว:", ["เจ้าของร้านใจดี/เป็นกันเอง", "วัยรุ่นเทสดี (Cafe Hopper)", "สายกินจุ (Mukbang)", "นักวิจารณ์อาหาร (ด่าไปกินไป/เรียลๆ)", "เชฟทำอาหาร/ผู้เชี่ยวชาญ", "พนักงานเสิร์ฟสายฮา", "ไม่มีคน (เน้นอาหาร/บรรยากาศ)"], "ugc_actor", "สายด่าไปกินไป=สตรีทฟู้ดสร้างความเรียล, เชฟ=ภัตตาคาร/โอมากาเสะ")
            render_custom_select("2. 🗣️ สไตล์การเล่าเรื่อง:", ["ASMR (เน้นเสียงเคี้ยว/ทำอาหาร)", "เล่าสตอรี่สู้ชีวิต (Storytelling)", "ตื่นเต้นอวยยศ (Hype)", "รีวิวตามจริงไม่อวย (Honest Review)", "ตลกขบขัน/ซิทคอม", "ดุดันจริงจัง (Hardcore)"], "ugc_tone", "ASMR=เหมาะกับของทอด/ย่าง, Storytelling=สร้างความผูกพันกับร้าน")
            render_custom_select("3. 🎥 มุมกล้องและพร็อพ:", ["ถือกล้องเซลฟี่เดินเข้าร้าน (Vlog POV)", "ตั้งกล้องกินโชว์ (Static/Tabletop)", "มุมมองแทนสายตาตอนกิน (First-person POV)", "ตากล้องแอบถ่าย (Third-person/Candid)", "ซูมเจาะอาหารยั่วๆ (Macro/B-roll)"], "ugc_cam", "เซลฟี่=ความเป็นกันเอง (UGC แท้ๆ), ซูมเจาะ=เน้นความน่ากิน")
            render_custom_select("4. ✨ บรรยากาศร้าน (Vibe):", ["สตรีทฟู้ดริมทาง (Street Food/Local)", "คาเฟ่มินิมอล (Minimalist/Clean)", "หรูหราภัตตาคาร (Fine Dining)", "ร้านลับในซอย (Hidden Gem/Cozy)", "โฮมมี่ทำกินเองที่บ้าน (Home-cooked)"], "ugc_vibe", "ช่วยให้ AI กำหนดฉากหลังและจัดแสงได้ตรงปก")
        with c2:
            render_custom_select("5. 🌐 ภาษาและสำเนียง:", ["ภาษาไทยกลาง", "อีสานมาตรฐาน", "ภาษาใต้", "ภาษาเหนือ", "อังกฤษ (English)"], "ugc_lang", "เพิ่มความ Local และความน่าเชื่อถือให้กับร้านพื้นถิ่น")
            render_custom_select("6. 🎵 ดนตรีประกอบ (BGM):", ["เพลงฮิตแผ่นเสียงรันเวย์ (Trendy TikTok)", "Acoustic ชิลๆ (Cafe Vibe)", "โจ๊ะๆ รถแห่ (Fun Thai Local)", "Lo-fi สบายๆ", "Epic ยิ่งใหญ่อลังการ", "ไม่มีเพลง (เน้นเสียง ASMR/เสียงบรรยากาศ)"], "ugc_music", "ถ้าเลือกแนว ASMR ด้านบน แนะนำให้เลือก 'ไม่มีเพลง' ครับ")
            render_custom_select("7. 👉 จุดปิดการขาย (CTA):", ["ปักหมุดแผนที่ร้าน/ชวนมากิน", "แจกโปรโมชั่นหน้าร้าน", "สั่งผ่านแอปเดลิเวอรี่ (Grab/Lineman)", "กดตะกร้าสั่งซื้อ (ขายอาหารแห้ง/สำเร็จรูป)", "กดติดตามรอคลิปหน้า"], "ugc_cta", "เป้าหมายหลักของคลิปนี้คือให้คนดูทำอะไรต่อ")
        with c3:
            render_custom_select("8. 🎞️ จังหวะการตัดต่อ:", ["ตัดฉับไว (Jump Cut)", "สมูทและสโลว์โมชั่นยั่วๆ", "ตัดตามจังหวะเพลง (Beat Sync)", "Long Take (แช่กล้องนานให้เห็นความเรียล)"], "ugc_pacing", "สโลว์โมชั่น=เวลายกชีสยืดๆ หรือเทน้ำจิ้ม")
            render_custom_select("9. ✍️ ข้อความบนจอ:", ["บรรยายความอร่อยคำต่อคำ", "ซับไตเติ้ล", "ป้ายราคาเด้งกระแทกตา", "คะแนนรีวิวดาว", "ไม่มีข้อความ"], "ugc_text_overlay", "ป้ายราคา=ดึงดูดสายประหยัด, บรรยายคำต่อคำ=วัยรุ่นฮิตมาก")
            render_custom_select("10. ⏳ ความยาวคลิป:", ["Bumper Ads (6 วิ)", "Shorts/Reels (15-30 วิ)", "มาตรฐาน (1 นาที)", "Long-form (เกิน 1 นาที)"], "ugc_dur", "Shorts/Reels (15-30 วิ) เหมาะกับการดันอัลกอริทึมมากที่สุด")

        if st.button("🚀 เริ่มเขียนสคริปต์รีวิวร้าน (UGC Vlogger)", type="primary", use_container_width=True):
            prompt = f"""คุณคือผู้กำกับและ Content Creator ระดับประเทศ หน้าที่ของคุณคือการเขียนสคริปต์คลิปรีวิวร้านอาหารแบบแบ่งฉาก (ฉากละ 8 วินาที) เพื่อนำไปเจนวิดีโอบน AI (Veo 3.1) โดยอ้างอิงจากการตั้งค่าต่อไปนี้:
ชื่อร้าน: {st.session_state.get('ugc_shop_name')}
เมนูเด็ด: {st.session_state.get('ugc_menu')}
พิกัด: {st.session_state.get('ugc_location')}
บรีฟพิเศษที่ต้องมี: {st.session_state.get('ugc_extra_brief')}
ผู้รีวิว: {st.session_state.get('ugc_actor')}
โทนการเล่าเรื่อง: {st.session_state.get('ugc_tone')}
มุมกล้อง: {st.session_state.get('ugc_cam')}
บรรยากาศร้าน: {st.session_state.get('ugc_vibe')}
ภาษา: {st.session_state.get('ugc_lang')}
ดนตรี: {st.session_state.get('ugc_music')}
CTA: {st.session_state.get('ugc_cta')}
การตัดต่อ: {st.session_state.get('ugc_pacing')}
ความยาวคลิป: {st.session_state.get('ugc_dur')}

⚠️ กฎเหล็กในการสร้างฉาก:
- กฎเรื่องสรรพนามและเพศ (Gender & Pronoun Rule): ตรวจสอบ "คาแรคเตอร์ผู้รีวิว" เพื่อกำหนดเพศและสรรพนามให้ถูกต้อง หากเป็นวัยรุ่นใช้ศัพท์แสลงวัยรุ่น (เช่น แก, จึ้ง, แสงออกปาก) หากเป็นเชฟ/เจ้าของร้านใช้ภาษาที่ดูเชี่ยวชาญ/เป็นกันเอง 
- ข้อมูลจากบรีฟพิเศษ: คุณต้องนำข้อมูลใน "บรีฟพิเศษที่ต้องมี" แทรกเข้าไปในบทพูดของฉากใดฉากหนึ่งอย่างเป็นธรรมชาติ

🎬 ฉากที่ 1: เปิดคลิปเรียกน้ำย่อย (The Hook - 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายภาพรวมว่าเกิดอะไรขึ้น (เช่น โชว์อาหารน่ากิน หรือคนรีวิวกำลังตื่นเต้น)
* ข้อความบนจอ (Text on Screen): (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (เขียนตามสำเนียง ภาษา และกฎสรรพนามเพศที่กำหนด)
* Prompt สร้างภาพนิ่ง: (ภาษาอังกฤษ - สำหรับ Nano Banana 2) อธิบายหน้าตาผู้รีวิว (ถ้ามี), อาหาร, ฉากหลัง, แสง, โทนสี และมุมกล้องอย่างละเอียดที่สุด เพื่อใช้เป็นภาพอ้างอิง (เขียนแบบบรรทัดเดียวห้ามขึ้นบรรทัดใหม่)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ - สำหรับ Veo 3.1) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ โดยระบุจังหวะตัดกล้อง และลงท้ายด้วยคำว่า "Audio: [เสียง SFX/ดนตรี]"

🎬 ฉากที่ 2, 3, 4... : รีวิวและกินโชว์ (Review & Eat - ฉากละ 8 วินาที)
* รายละเอียดฉาก (ภาษาไทย): อธิบายแอคชั่นการกิน การตักอาหาร หรือพาดูบรรยากาศร้าน
* ข้อความบนจอ (Text on Screen): (ถ้ามี)
* บทพูดตัวละคร/เสียงพากย์ (Voiceover): (ขยี้ความอร่อย บรรยากาศ หรือใส่บรีฟพิเศษลงไป)
* (ห้ามเขียน Prompt สร้างภาพนิ่งในฉากที่ 2 เป็นต้นไปเด็ดขาด)
* Prompt สร้างวิดีโอ: (ภาษาอังกฤษ) เขียนต่อเนื่องกัน ห้ามขึ้นบรรทัดใหม่ เริ่มด้วย "Continuing from the previous frame..." ระบุจังหวะตัดกล้อง และลงท้ายด้วย "Audio: [เสียงประกอบที่สอดคล้อง]"

📱 ส่วนท้ายสุด: แคปชั่นดันคลิป 3 แพลตฟอร์ม
- TikTok: เน้นฮุกกระแส + พิกัดร้าน + แฮชแท็กสายกิน (ความยาวปกติ)
- Facebook Reels: เน้นสตอรี่ความน่ากิน โน้มน้าวให้แท็กเพื่อนมา (ความยาวปกติ)
- Shopee Video/Feed: ฮาร์ดเซลล์กระชับ *(กฎเหล็ก: ห้ามเกิน 150 ตัวอักษรรวมแฮชแท็ก)*
"""
            st.session_state.ugc_prompt = smart_generate(prompt)

        if st.session_state.ugc_prompt: st.code(st.session_state.ugc_prompt, language="markdown")

    with tab_poster:
        st.markdown("##### 🎯 ล็อกเป้าหมายให้ AI (Pre-AI Controls - Poster)")
        ugc_ai_dir_ratio_pos = st.selectbox("📏 ล็อกสัดส่วนภาพหน้าปก (Aspect Ratio):", ["🤖 ปล่อย AI คิดเอง (Free Style)", "16:9 (YouTube Vlog)", "4:3 (หน้าจอมาตรฐาน)", "1:1 (Facebook/IG Post)", "3:4 (Portrait Menu)", "9:16 (TikTok/Reels/Shorts)"], key="ugc_ai_dir_ratio_pos")

        col_ai, col_res = st.columns(2)
        with col_ai:
            if st.button("✨ ให้ AI ตั้งค่าโปสเตอร์อัตโนมัติ", key="ugc_pos_ai", use_container_width=True):
                if not st.session_state.ugc_shop_name and not st.session_state.ugc_menu:
                    st.warning("⚠️ กรุณาระบุชื่อร้านหรือเมนูเด็ดก่อนครับ")
                else:
                    with st.spinner("🧠 AI กำลังสแกนรูปภาพและออกแบบหน้าปก Vlog..."):
                        ratio_constraint_pos = ""
                        if "16:9" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (ugc_pos_comp) และมุมกล้องให้เหมาะสมกับอัตราส่วนแนวนอนกว้าง 16:9 (YouTube Vlog)'
                        elif "4:3" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (ugc_pos_comp) ให้เหมาะสมกับแนวนอนมาตรฐาน 4:3'
                        elif "1:1" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (ugc_pos_comp) ให้เหมาะสมกับสัดส่วนจัตุรัส 1:1 เน้นจุดสนใจตรงกลาง'
                        elif "3:4" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบภาพ (ugc_pos_comp) ให้เหมาะสมกับแนวตั้ง 3:4'
                        elif "9:16" in ugc_ai_dir_ratio_pos: ratio_constraint_pos = '- บังคับเลือกการจัดองค์ประกอบ (ugc_pos_comp) และตำแหน่งข้อความ (ugc_pos_text_pos) ให้เหมาะสมกับแนวตั้ง 9:16 โดยเว้น Safe Zone ให้มือถือเสมอ'

                        ugc_context = f"ร้าน: {st.session_state.get('ugc_shop_name', '')} | เมนู: {st.session_state.get('ugc_menu', '')} | พิกัด: {st.session_state.get('ugc_location', '')}"
                        prompt_contents = []
                        if st.session_state.ugc_imgs:
                            prompt_contents = [Image.open(img_file) for img_file in st.session_state.ugc_imgs]
                        
                        prompt_text = f"""วิเคราะห์ข้อมูลร้านและรูปภาพเหล่านี้: "{ugc_context}"
                        แล้วเลือกตัวเลือกที่เหมาะสมที่สุดเพื่อออกแบบโปสเตอร์/หน้าปก Vlog อาหาร ระดับผู้กำกับศิลป์ จากรายการด้านล่าง:
                        
                        - ugc_pos_actor_act: ["ไม่มีคน (โฟกัสอาหารเต็มๆ)", "อ้าปากค้างตกใจชามยักษ์ (Shocked Face)", "คีบเส้น/ตักอาหารโชว์กล้อง (Food Lift)", "ถือจานส่งยิ้มหวาน (Friendly Smile)", "ชี้ไปที่อาหารพร้อมทำตาโต (Pointing)", "ทำหน้าฟินหลับตาพริ้ม (Satisfied Face)"]
                        - ugc_pos_food_fx: ["ชีสยืดเยิ้มๆ (Melty Cheese)", "ควันพุ่งร้อนๆ (Steaming Hot)", "น้ำจิ้มราดฉ่ำๆ (Juicy Sauce Drop)", "เนื้อสัตว์ย่างเกรียมๆ (Sizzling Grill)", "หยดน้ำเกาะแก้วเย็นจัด (Ice Cold Condensation)", "จัดจานเนี้ยบสไตล์ Fine Dining (Perfectly Plated)", "ล้นชามดูคุ้มค่าจุกๆ (Overflowing/Massive)"]
                        - ugc_pos_style: ["Vlog Thumbnail สายกิน (Clickbait Youtuber)", "Minimalist Cafe Cover (ปกมินิมอลคาเฟ่)", "Street Food Authentic (ปกสตรีทฟู้ดเรียลๆ)", "Premium Dining (ปกหรูหราภัตตาคาร)", "Home-cooked Cozy (ปกทำอาหารที่บ้านอบอุ่น)", "Food Delivery App Cover (ปกแอปสั่งอาหารคลีนๆ)"]
                        - ugc_pos_color: ["สดใสอมส้มกระตุ้นความหิว (Warm & Appetizing)", "คลีนสว่างสบายตา (Bright & Clean)", "จัดจ้านตัดกันดึงดูดสายตา (Vibrant Contrast)", "โทนฟิล์มญี่ปุ่นละมุนๆ (Japanese Film/Muted)", "ดาร์กพรีเมียม (Dark & Moody)", "นีออนกลางคืน (Night Neon Cyber)"]
                        - ugc_pos_cam: ["ซูมใกล้เนื้ออาหารฉ่ำๆ (Macro Close-up)", "ระดับสายตาเห็นคนและอาหาร (Eye-level Portrait)", "มุมมองคนกิน (First-Person POV)", "มุมสูงถ่ายเจาะเต็มโต๊ะ (Top-down Flat Lay)", "มุมกว้างเห็นบรรยากาศร้าน (Wide Angle)"]
                        - ugc_pos_light: ["แสงธรรมชาติริมหน้าต่าง (Soft Window Light)", "สาดแฟลชตรงๆ สไตล์วัยรุ่น (Hard Flash/Y2K)", "แสงไฟคาเฟ่อบอุ่น (Warm Bistro Light)", "แสงสตูดิโอเคลียร์ชัด (Studio Ring Light)", "แสงนีออนสตรีทฟู้ด (Street Neon Light)", "แสงแดดตอนเย็น (Golden Hour)"]
                        - ugc_pos_bg: ["บรรยากาศในร้านเบลอๆ (Blurred Restaurant Vibe)", "โต๊ะไม้สุดคลาสสิก (Rustic Wooden Table)", "โต๊ะหินอ่อนหรูหรา (Marble Countertop)", "ริมถนนสตรีทฟู้ด (Street Food Cart)", "วิวธรรมชาติ/สวนคาเฟ่ (Outdoor Garden)", "ฉากสตูดิโอสีพื้น (Solid Studio Color)"]
                        - ugc_pos_comp: ["แบ่งครึ่งจอคนกับอาหาร (Split-screen)", "จัดวางอาหารตรงกลางเป๊ะ (Center Focus)", "กฎสามส่วน (Rule of Thirds)", "พื้นที่ว่างด้านซ้ายเยอะๆ (Left Negative Space)", "พื้นที่ว่างด้านขวาเยอะๆ (Right Negative Space)"]
                        - ugc_pos_font: ["ฟอนต์ตัวหนาขอบดำสไตล์ Youtuber (Bold Impact with Stroke)", "ฟอนต์ลายมือดูเป็นมิตร (Friendly Handwritten)", "ฟอนต์คาเฟ่มินิมอล (Clean Sans-serif)", "ฟอนต์อาร์ตๆ สไตล์นิตยสาร (Elegant Serif)", "ฟอนต์สไตล์รายการทีวี (TV Show Variety)"]
                        - ugc_pos_text_pos: ["บนซ้าย (Top-Left)", "บนขวา (Top-Right)", "พาดกลางภาพ (Center Bold)", "ล่างซ้าย (Bottom-Left)", "ล่างขวา (Bottom-Right)", "เว้นขวาไว้หลบปุ่มกด (Safe Zone มือถือ)"]
                        - ugc_pos_text_main: ["อร่อยแสงออกปาก!", "ร้านลับต้องลอง!", "ให้เยอะจนจุก!", "ไม่กินคือพลาด!", "ถูกและดีมีอยู่จริง!", "สูตรต้นตำรับ!", "ไม่มีข้อความ"]
                        - ugc_pos_text_sub: ["พิกัดลับ", "ราคาหลักสิบ", "คิวยาวมาก", "รีวิว 5 ดาว", "เปิดยันเช้า", "ขายวันละ 100 ชาม", "ไม่มีข้อความ"]

                        ⚠️ กฎพิเศษในการตั้งค่า:
                        {ratio_constraint_pos}

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
            if st.button("🔄 รีเซ็ตหน้าปก", key="ugc_pos_res", use_container_width=True):
                st.session_state.ugc_poster_prompt = ""
                st.session_state.ugc_poster_prompt_th = ""
                pos_keys = ["ugc_pos_actor_act", "ugc_pos_food_fx", "ugc_pos_style", "ugc_pos_color", "ugc_pos_cam", "ugc_pos_light", "ugc_pos_bg", "ugc_pos_comp", "ugc_pos_font", "ugc_pos_text_pos", "ugc_pos_text_main", "ugc_pos_text_sub"]
                for k in pos_keys:
                    if k in st.session_state: del st.session_state[k]
                    if f"select_{k}" in st.session_state: del st.session_state[f"select_{k}"]
                    if f"custom_{k}" in st.session_state: del st.session_state[f"custom_{k}"]
                st.rerun()

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            render_custom_select("1. 🏃‍♂️ ท่าทางผู้รีวิว (Action):", ["ไม่มีคน (โฟกัสอาหารเต็มๆ)", "อ้าปากค้างตกใจชามยักษ์ (Shocked Face)", "คีบเส้น/ตักอาหารโชว์กล้อง (Food Lift)", "ถือจานส่งยิ้มหวาน (Friendly Smile)", "ชี้ไปที่อาหารพร้อมทำตาโต (Pointing)", "ทำหน้าฟินหลับตาพริ้ม (Satisfied Face)"], "ugc_pos_actor_act", "หน้าตกใจ/คีบอาหาร = Clickbait ดึงยอดวิวชั้นดีบน YouTube")
            render_custom_select("2. 🍝 สภาพอาหาร (Food FX):", ["ชีสยืดเยิ้มๆ (Melty Cheese)", "ควันพุ่งร้อนๆ (Steaming Hot)", "น้ำจิ้มราดฉ่ำๆ (Juicy Sauce Drop)", "เนื้อสัตว์ย่างเกรียมๆ (Sizzling Grill)", "หยดน้ำเกาะแก้วเย็นจัด (Ice Cold Condensation)", "จัดจานเนี้ยบสไตล์ Fine Dining (Perfectly Plated)", "ล้นชามดูคุ้มค่าจุกๆ (Overflowing/Massive)"], "ugc_pos_food_fx", "ชีสยืด/ควันพุ่ง ช่วยหยุดนิ้วคนดูได้ 100%")
            render_custom_select("3. 🎨 สไตล์ปกคลิป (Style):", ["Vlog Thumbnail สายกิน (Clickbait Youtuber)", "Minimalist Cafe Cover (ปกมินิมอลคาเฟ่)", "Street Food Authentic (ปกสตรีทฟู้ดเรียลๆ)", "Premium Dining (ปกหรูหราภัตตาคาร)", "Home-cooked Cozy (ปกทำอาหารที่บ้านอบอุ่น)", "Food Delivery App Cover (ปกแอปสั่งอาหารคลีนๆ)"], "ugc_pos_style", "กำหนดอารมณ์และ Positioning ของช่องคุณ")
            render_custom_select("4. 🌈 โทนสี (Color Grading):", ["สดใสอมส้มกระตุ้นความหิว (Warm & Appetizing)", "คลีนสว่างสบายตา (Bright & Clean)", "จัดจ้านตัดกันดึงดูดสายตา (Vibrant Contrast)", "โทนฟิล์มญี่ปุ่นละมุนๆ (Japanese Film/Muted)", "ดาร์กพรีเมียม (Dark & Moody)", "นีออนกลางคืน (Night Neon Cyber)"], "ugc_pos_color", "โทนอมส้ม/จัดจ้าน กระตุ้นความหิวได้ดีที่สุด")
        with c2:
            render_custom_select("5. 📸 มุมกล้อง (Camera Angle):", ["ซูมใกล้เนื้ออาหารฉ่ำๆ (Macro Close-up)", "ระดับสายตาเห็นคนและอาหาร (Eye-level Portrait)", "มุมมองคนกิน (First-Person POV)", "มุมสูงถ่ายเจาะเต็มโต๊ะ (Top-down Flat Lay)", "มุมกว้างเห็นบรรยากาศร้าน (Wide Angle)"], "ugc_pos_cam", "Macro Close-up ทำให้คนดูรู้สึกเหมือนได้กลิ่นอาหาร")
            render_custom_select("6. 💡 แสงและบรรยากาศ (Lighting):", ["แสงธรรมชาติริมหน้าต่าง (Soft Window Light)", "สาดแฟลชตรงๆ สไตล์วัยรุ่น (Hard Flash/Y2K)", "แสงไฟคาเฟ่อบอุ่น (Warm Bistro Light)", "แสงสตูดิโอเคลียร์ชัด (Studio Ring Light)", "แสงนีออนสตรีทฟู้ด (Street Neon Light)", "แสงแดดตอนเย็น (Golden Hour)"], "ugc_pos_light", "สาดแฟลช (Hard Flash) กำลังฮิตมากในวัยรุ่น Y2K/สตรีทฟู้ด")
            render_custom_select("7. 🏞️ ฉากหลัง (Background):", ["บรรยากาศในร้านเบลอๆ (Blurred Restaurant Vibe)", "โต๊ะไม้สุดคลาสสิก (Rustic Wooden Table)", "โต๊ะหินอ่อนหรูหรา (Marble Countertop)", "ริมถนนสตรีทฟู้ด (Street Food Cart)", "วิวธรรมชาติ/สวนคาเฟ่ (Outdoor Garden)", "ฉากสตูดิโอสีพื้น (Solid Studio Color)"], "ugc_pos_bg", "ฉากหลังเบลอๆ (Bokeh) จะช่วยให้อาหารดูโดดเด่นลอยออกมา")
            render_custom_select("8. 📐 การจัดองค์ประกอบ (Comp):", ["แบ่งครึ่งจอคนกับอาหาร (Split-screen)", "จัดวางอาหารตรงกลางเป๊ะ (Center Focus)", "กฎสามส่วน (Rule of Thirds)", "พื้นที่ว่างด้านซ้ายเยอะๆ (Left Negative Space)", "พื้นที่ว่างด้านขวาเยอะๆ (Right Negative Space)"], "ugc_pos_comp", "Split-screen เล่าเรื่องคนกินและอาหารพร้อมกันได้ดีมาก")
        with c3:
            render_custom_select("9. 🔠 สไตล์ฟอนต์ (Typography):", ["ฟอนต์ตัวหนาขอบดำสไตล์ Youtuber (Bold Impact with Stroke)", "ฟอนต์ลายมือดูเป็นมิตร (Friendly Handwritten)", "ฟอนต์คาเฟ่มินิมอล (Clean Sans-serif)", "ฟอนต์อาร์ตๆ สไตล์นิตยสาร (Elegant Serif)", "ฟอนต์สไตล์รายการทีวี (TV Show Variety)"], "ugc_pos_font", "ขอบดำสไตล์ Youtuber ทำให้อ่านง่ายบนทุกสภาพพื้นหลัง")
            render_custom_select("10. 📍 ตำแหน่งข้อความ (Text Pos):", ["บนซ้าย (Top-Left)", "บนขวา (Top-Right)", "พาดกลางภาพ (Center Bold)", "ล่างซ้าย (Bottom-Left)", "ล่างขวา (Bottom-Right)", "เว้นขวาไว้หลบปุ่มกด (Safe Zone มือถือ)"], "ugc_pos_text_pos", "ลงคลิปแนวตั้ง (TikTok/Reels) ควรเลือกหลบปุ่มกดเสมอ")
            render_custom_select("11. 📢 พาดหัวหลัก (Headline):", ["อร่อยแสงออกปาก!", "ร้านลับต้องลอง!", "ให้เยอะจนจุก!", "ไม่กินคือพลาด!", "ถูกและดีมีอยู่จริง!", "สูตรต้นตำรับ!", "ไม่มีข้อความ"], "ugc_pos_text_main", "คำสั้นๆ โดนใจ AI จะเรนเดอร์ได้แม่นยำกว่าประโยคยาวๆ")
            render_custom_select("12. 🏷️ ป้ายรอง (Sub-text):", ["พิกัดลับ", "ราคาหลักสิบ", "คิวยาวมาก", "รีวิว 5 ดาว", "เปิดยันเช้า", "ขายวันละ 100 ชาม", "ไม่มีข้อความ"], "ugc_pos_text_sub", "ข้อความดึงดูดใจเพิ่มเติม หรือเว้นว่างไว้ถ้าไม่ต้องการ")

        if st.button("🚀 เริ่มสร้าง Prompt ปกคลิปรีวิว (Nano Banana 2)", type="primary", use_container_width=True):
            with st.spinner("🧠 AI กำลังแต่ง Prompt และแยกหน้าจอแปลภาษา..."):
                prompt = f"""คุณคือนักเขียน Prompt ระดับโลกสำหรับ AI สร้างภาพ 'Nano Banana 2' (Gemini 3 Flash Image)

ข้อมูลสำหรับปกคลิปรีวิวอาหาร:
- ร้าน/เมนู: {st.session_state.get('ugc_shop_name')} {st.session_state.get('ugc_menu')}
- ท่าทางคนรีวิว: {st.session_state.get('ugc_pos_actor_act')}
- สภาพอาหาร: {st.session_state.get('ugc_pos_food_fx')}
- สไตล์ปกคลิป: {st.session_state.get('ugc_pos_style')}
- โทนสี: {st.session_state.get('ugc_pos_color')}
- มุมกล้อง: {st.session_state.get('ugc_pos_cam')}
- แสงเงา: {st.session_state.get('ugc_pos_light')}
- ฉากหลัง: {st.session_state.get('ugc_pos_bg')}
- องค์ประกอบ: {st.session_state.get('ugc_pos_comp')}
- ฟอนต์: {st.session_state.get('ugc_pos_font')}
- ตำแหน่งข้อความ: {st.session_state.get('ugc_pos_text_pos')}
- พาดหัวหลัก: "{st.session_state.get('ugc_pos_text_main')}"
- ป้ายรอง: "{st.session_state.get('ugc_pos_text_sub')}"

**กฎเหล็กในการแต่ง Prompt (STRICT RULES):**
1. **ห้ามแปลข้อความ (DO NOT TRANSLATE TEXT):** คำว่า "{st.session_state.get('ugc_pos_text_main')}" และ "{st.session_state.get('ugc_pos_text_sub')}" ต้องเก็บไว้เป็นภาษาไทยในเครื่องหมายคำพูดเป๊ะๆ ห้ามแปลเป็นอังกฤษ!
2. โครงสร้าง Prompt: 1 ย่อหน้า อธิบายท่าทางคนรีวิว ความน่ากินของอาหาร ต้องมีประโยคเกี่ยวกับการเรนเดอร์ข้อความ เช่น `The text "{st.session_state.get('ugc_pos_text_main')}" is clearly rendered using {st.session_state.get('ugc_pos_font')} typography placed at {st.session_state.get('ugc_pos_text_pos')}.`
3. ห้ามมั่ว (Anti-Hallucination): `STRICTLY render ONLY the requested text. DO NOT add extra icons, stars, or random text.`

**รูปแบบการตอบกลับ (JSON FORMAT ONLY):**
ตอบกลับมาเป็น JSON โครงสร้างนี้เท่านั้น
{{
    "english_prompt": "Prompt สร้างภาพนิ่ง: [Prompt ภาษาอังกฤษทั้งหมด]",
    "thai_translation": "[คำแปล Prompt อธิบายให้คนอ่านเข้าใจ]"
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
            st.markdown("### 📌 สรุปบรีฟปกคลิปรีวิว (Summary Board)")
            st.info(f"**แอคชั่น:** {st.session_state.get('ugc_pos_actor_act')} | **สไตล์อาหาร:** {st.session_state.get('ugc_pos_food_fx')} | **มุมกล้อง:** {st.session_state.get('ugc_pos_cam')}\n\n**พาดหัวหลัก:** {st.session_state.get('ugc_pos_text_main')} | **ป้ายรอง:** {st.session_state.get('ugc_pos_text_sub')}")
            
            c_eng, c_th = st.columns(2)
            with c_eng:
                st.success("🇬🇧 คำสั่งภาษาอังกฤษ (ส่งให้ระบบ Handoff/บอท)")
                st.code(st.session_state.ugc_poster_prompt, language="markdown")
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
                
        if st.session_state.spk_prompt: st.code(st.session_state.spk_prompt, language="markdown")
    
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
        if st.session_state.spk_poster_prompt: st.code(st.session_state.spk_poster_prompt, language="markdown")

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

        if st.session_state.pet_prompt: st.code(st.session_state.pet_prompt, language="markdown")
    
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
        if st.session_state.meme_prompt: st.code(st.session_state.meme_prompt, language="markdown")
    
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
        if st.session_state.meme_poster_prompt: st.code(st.session_state.meme_poster_prompt, language="markdown")

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
        if st.session_state.sat_prompt: st.code(st.session_state.sat_prompt, language="markdown")
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
        if st.session_state.sigma_prompt: st.code(st.session_state.sigma_prompt, language="markdown")
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
        if st.session_state.creepy_prompt: st.code(st.session_state.creepy_prompt, language="markdown")
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
        if st.session_state.dance_prompt: st.code(st.session_state.dance_prompt, language="markdown")
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
        st.code(res, language="markdown")