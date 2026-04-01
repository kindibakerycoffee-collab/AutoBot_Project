import streamlit as st
import time
from google import genai
from PIL import Image
import json
import subprocess
import os
import re

# ==========================================
# 🚨 1. ตั้งค่าหน้าเว็บ (ต้องอยู่บนสุดเสมอ)
# ==========================================
try:
    logo_img = Image.open("logo.png") 
except FileNotFoundError:
    logo_img = "🤖" 

st.set_page_config(
    page_title="AutoBot Director | NextGen Ai STORE",
    page_icon=logo_img,
    layout="wide"
)

# ==========================================
# 📡 ดึงกองกำลัง API Key จากตู้เซฟ
# ==========================================
api_keys_list = []
if "GEMINI_API_KEYS" in st.secrets:
    api_keys_list = st.secrets["GEMINI_API_KEYS"]
elif "GEMINI_API_KEY" in st.secrets:
    api_keys_list = [st.secrets["GEMINI_API_KEY"]]

# ==========================================
# 🧠 0. ตั้งค่าระบบความจำ (Session State) 
# ==========================================
if 'product_text' not in st.session_state: st.session_state.product_text = ""
if 'generated_video_prompt' not in st.session_state: st.session_state.generated_video_prompt = ""
if 'generated_captions' not in st.session_state: st.session_state.generated_captions = ""
if 'uploaded_img_paths' not in st.session_state: st.session_state.uploaded_img_paths = []

if 'v_presenter' not in st.session_state: st.session_state.v_presenter = "หญิงสาว (Young Female)"
if 'v_tone' not in st.session_state: st.session_state.v_tone = "เพื่อนป้ายยา (เป็นกันเอง)"
if 'v_ratio' not in st.session_state: st.session_state.v_ratio = "แนวตั้ง 9:16 (Story / Reels / TikTok)"
if 'v_lang' not in st.session_state: st.session_state.v_lang = "ไทยภาคใต้ (สำเนียงคนใต้แท้ๆ)"
if 'v_style' not in st.session_state: st.session_state.v_style = "UGC (รีวิวบ้านๆ จริงใจ)"
if 'v_story' not in st.session_state: st.session_state.v_story = "PAS (ขยี้ปัญหาแล้วเสนอทางแก้)"
if 'v_duration' not in st.session_state: st.session_state.v_duration = "มาตรฐานกำลังดี (30 วินาที)"
if 'v_text_overlay' not in st.session_state: st.session_state.v_text_overlay = "ข้อความภาษาไทย (ตัวใหญ่กระแทกตา)"
if 'v_visual' not in st.session_state: st.session_state.v_visual = "สมจริงเหมือนถ่ายทำจริง (Photorealistic)"
if 'v_target' not in st.session_state: st.session_state.v_target = "ทั่วไป (Mass)"
if 'v_cta' not in st.session_state: st.session_state.v_cta = "กดตะกร้าสีเหลือง"
if 'v_platform' not in st.session_state: st.session_state.v_platform = "TikTok (เน้นไวรัล ฮุกไวใน 3 วิ)"
if 'v_camera' not in st.session_state: st.session_state.v_camera = "มาตรฐาน (Smooth & Steady)"
if 'v_music' not in st.session_state: st.session_state.v_music = "เพลงป๊อปสนุกสนาน (Upbeat Pop)"

if 'p_style' not in st.session_state: st.session_state.p_style = "Hard Sale / โปรแรง (ตะโกนขาย)"
if 'p_ratio' not in st.session_state: st.session_state.p_ratio = "แนวตั้ง 9:16 (Story / Reels / TikTok)"
if 'p_color' not in st.session_state: st.session_state.p_color = "สีแบรนด์ตามรูปสินค้า (อิงจากภาพอ้างอิง)"
if 'p_composition' not in st.session_state: st.session_state.p_composition = "สินค้าอยู่ตรงกลางเด่นๆ (Center Focus)"
if 'p_typography' not in st.session_state: st.session_state.p_typography = "ฟอนต์ตัวหนาตะโกนขาย (Bold & Impactful)"
if 'generated_poster_prompt' not in st.session_state: st.session_state.generated_poster_prompt = ""

if 'current_key_idx' not in st.session_state: st.session_state.current_key_idx = 0
if 'key_status' not in st.session_state: 
    st.session_state.key_status = {i: "⏳ สแตนด์บาย" for i in range(len(api_keys_list))}
    if api_keys_list: st.session_state.key_status[0] = "🟢 กำลังใช้งาน"

# ==========================================
# 🧠 ฟังก์ชันผู้จัดการคีย์อัจฉริยะ
# ==========================================
def smart_generate(prompt_contents):
    if not api_keys_list: raise Exception("ไม่พบ API Key ในระบบเลยครับ กรุณาตั้งค่าก่อน")
    last_error = ""
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
                if j != idx and st.session_state.key_status.get(j) != "🔴 ติดลิมิต (รอ 1 นาที)":
                    st.session_state.key_status[j] = "⏳ สแตนด์บาย"
            return response.text 
        except Exception as e:
            last_error = str(e)
            st.session_state.key_status[idx] = "🔴 ติดลิมิต (รอ 1 นาที)"
            continue
    raise Exception(f"กองกำลัง API Key ติดลิมิตหมดแล้วครับ! กรุณารอประมาณ 1 นาที")

# ==========================================
# 🎨 UI Header & Sidebar
# ==========================================
if logo_img != "🤖": st.sidebar.image(logo_img, width=150)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 สถานะ API Key")
if st.sidebar.button("🔄 รีเซ็ตสถานะคีย์ทั้งหมด", use_container_width=True):
    st.session_state.current_key_idx = 0
    st.session_state.key_status = {i: "⏳ สแตนด์บาย" for i in range(len(api_keys_list))}
    if api_keys_list: st.session_state.key_status[0] = "🟢 กำลังใช้งาน"

if not api_keys_list: st.sidebar.error("❌ ยังไม่ได้ใส่ API Key")
else:
    for i in range(len(api_keys_list)):
        status = st.session_state.key_status.get(i, "⏳ สแตนด์บาย")
        st.sidebar.markdown(f"**หมายเลข {i+1}:** {status}")
st.sidebar.caption("💡 ทริค: ปุ่มรีเซ็ตจะล้างสถานะ 🔴 ให้กลับมาพร้อมใช้งานใหม่ทันที")
st.sidebar.markdown("---")

st.markdown("<h1>😀 ระบบผู้กำกับโฆษณา AI (AutoBot_Project)</h1>", unsafe_allow_html=True)

# ==========================================
# 📸 1. ส่วนดึงข้อความ
# ==========================================
with st.expander("➕ อัปโหลดรูปภาพอ้างอิง (สินค้า, พรีเซนเตอร์)", expanded=True):
    uploaded_files = st.file_uploader("Drag and drop files here", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_img_paths = []
        if not os.path.exists("temp_refs"): os.makedirs("temp_refs")
        for img_file in uploaded_files:
            file_path = os.path.abspath(os.path.join("temp_refs", img_file.name))
            with open(file_path, "wb") as f: f.write(img_file.getbuffer())
            st.session_state.uploaded_img_paths.append(file_path)

    if st.button("🔍 ดึงข้อความและจุดขายจากรูปภาพ", type="secondary", use_container_width=True):
        if not uploaded_files: st.warning("⚠️ กรุณาอัปโหลดรูปภาพก่อนครับ")
        elif not api_keys_list: st.error("🛑 กรุณาตั้งค่า API Key ก่อนครับ")
        else:
            with st.spinner("กำลังให้ AI สแกนข้อความจากรูปภาพ..."):
                try:
                    extracted_info = ""
                    for i, img_file in enumerate(uploaded_files):
                        img = Image.open(img_file)
                        prompt = "ดึงข้อความทั้งหมดที่เห็นในภาพนี้ออกมาให้ละเอียดที่สุด พร้อมสรุปจุดเด่นและโปรโมชันที่น่าสนใจ **และที่สำคัญที่สุด: จงบรรยายรูปร่าง ลักษณะ สี วัสดุ และรูปทรงของตัวสินค้าในภาพอย่างละเอียด (Physical appearance description) เพื่อให้นำไปใช้สร้างรูปต่อได้ตรงปกที่สุด**"
                        result_text = smart_generate([img, prompt]) 
                        extracted_info += f"**ข้อมูลจากรูป {img_file.name}:**\n{result_text}\n\n"
                        if i < len(uploaded_files) - 1: time.sleep(4)
                    st.session_state.product_text = extracted_info
                    st.success("✅ ดึงข้อความและบันทึกรูปต้นฉบับสำเร็จ!")
                except Exception as e: st.error(f"❌ เกิดข้อผิดพลาดจาก AI: {e}")

st.markdown("### 📝 รายละเอียดสินค้าสำหรับแต่งสคริปต์")
product_input = st.text_area("ข้อความที่สแกนได้:", value=st.session_state.product_text, height=200)
st.session_state.product_text = product_input 
st.divider()

# ==========================================
# 🎛️ 3. เลือกโหมดการทำงานหลัก
# ==========================================
tab_video, tab_poster = st.tabs(["🎬 โหมดสร้างคลิปวิดีโอ (Pipeline)", "🖼️ โหมดสร้างโปสเตอร์โฆษณา"])

with tab_video:
    head_col, ai_col = st.columns([4, 1])
    with head_col: st.markdown("#### 🎬 แผงควบคุมวิดีโอ (Video Settings)")
    with ai_col:
        if st.button("✨ ให้ AI ช่วยตั้งค่าวิดีโอ", use_container_width=True):
            if not st.session_state.product_text.strip(): st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            else:
                with st.spinner("🧠 AI กำลังคิด..."):
                    time.sleep(1) 
                    text = st.session_state.product_text.lower()
                    if any(w in text for w in ["หญิง", "สวย", "สกินแคร์", "ลิป", "กระโปรง"]): st.session_state.v_presenter = "หญิงสาว (Young Female)"
                    elif any(w in text for w in ["น่ารัก", "สัตว์", "หมา", "แมว"]): st.session_state.v_presenter = "มาสคอตสัตว์ (Animal Mascot)"
                    else: st.session_state.v_presenter = "ชายหนุ่ม (Young Male)"
                    if any(w in text for w in ["พรีเมียม", "หรู", "แพง", "อสังหา"]): 
                        st.session_state.v_style = "โทนภาพยนตร์ (Cinematic)"
                        st.session_state.v_tone = "หรูหรา / พรีเมียม"
                        st.session_state.v_camera = "สมูทช้าๆ แบบหนัง (Slow Pan & Cinematic Dolly)"
                    else:
                        st.session_state.v_style = "UGC (รีวิวบ้านๆ จริงใจ)"
                        st.session_state.v_tone = "เพื่อนป้ายยา (เป็นกันเอง)"
                        st.session_state.v_camera = "ถือกล้องถ่ายเองสมจริง (Handheld Camera)"
                    st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("👤 ผู้พูด/พรีเซนเตอร์:", ["ชายหนุ่ม (Young Male)", "หญิงสาว (Young Female)", "ชายวัยกลางคน (Middle-aged Male)", "หญิงวัยกลางคน (Middle-aged Female)", "คุณตา/คุณปู่ (Elderly Male)", "คุณยาย/คุณย่า (Elderly Female)", "เด็กผู้ชาย (Boy)", "เด็กผู้หญิง (Girl)", "ไม่ระบุเพศ / LGBTQ+", "มาสคอตสัตว์ (Animal Mascot)", "หุ่นยนต์ AI (AI Robot)", "ไม่มีพรีเซนเตอร์ (เน้นสินค้า)"], key="v_presenter")
        st.selectbox("🗣️ น้ำเสียง:", ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "ผู้เชี่ยวชาญ / น่าเชื่อถือ", "หรูหรา / พรีเมียม", "กวนๆ / ขี้เล่น"], key="v_tone")
        st.selectbox("🎯 กลุ่มเป้าหมาย:", ["ทั่วไป (Mass)", "วัยรุ่น Gen Z", "พนักงานออฟฟิศ", "แม่บ้าน / คนมีครอบครัว", "ผู้สูงอายุ"], key="v_target")
        st.selectbox("📱 สัดส่วนวิดีโอ:", ["แนวตั้ง 9:16 (Story / Reels / TikTok)", "แนวนอน 16:9 (YouTube / TV)"], key="v_ratio")
        st.selectbox("🌐 ภาษาของคลิป:", ["ไทยภาคกลาง (มาตรฐาน)", "ไทยภาคเหนือ (สำเนียงคนเมืองแท้ๆ)", "ไทยภาคอีสาน (สำเนียงคนอีสานแท้ๆ)", "ไทยภาคใต้ (สำเนียงคนใต้แท้ๆ)", "ผสมไทย-อังกฤษ (Tinglish)", "อังกฤษ (English)", "ไม่มีเสียงพูด (เน้นดนตรี/เอฟเฟกต์)"], key="v_lang")
        
    with col2:
        st.selectbox("🎥 สไตล์วิดีโอ:", ["UGC (รีวิวบ้านๆ จริงใจ)", "โทนภาพยนตร์ (Cinematic)", "Unboxing / ASMR", "โฆษณาทีวี (TV Commercial)", "มิวสิควิดีโอ (MV Style)"], key="v_style")
        st.selectbox("📖 การเล่าเรื่อง:", ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "FOMO (กระตุ้นความกลัวพลาดโปร)", "Storytelling (เล่าเรื่องชวนติดตาม)"], key="v_story")
        st.selectbox("👉 ปิดการขาย (CTA):", ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ", "คลิกลิงก์หน้าโปรไฟล์", "เก็บคูปองส่วนลด"], key="v_cta")
        st.selectbox("⏳ ความยาวคลิปรวม:", ["สั้นกระชับฮุกคนดู (15 วินาที)", "มาตรฐานกำลังดี (30 วินาที)", "เล่าเรื่องจัดเต็ม (60 วินาที)"], key="v_duration")
        st.selectbox("💬 สไตล์ข้อความบนจอ:", ["ข้อความภาษาไทย (ตัวใหญ่กระแทกตา)", "ข้อความภาษาอังกฤษ (อินเตอร์)", "เน้นสัญลักษณ์/Emoji แทนข้อความ", "ป๊อปอัปข้อความสั้นๆ (Pop-up Text)", "ซับไตเติ้ลบรรยาย (Subtitle)", "ไม่มีข้อความบนจอ"], key="v_text_overlay")
        
    with col3:
        st.selectbox("📱 แพลตฟอร์มปลายทาง:", ["TikTok (เน้นไวรัล ฮุกไวใน 3 วิ)", "Shopee / Lazada (เน้นขายของ โชว์โปรโมชั่น ตะกร้า)", "Facebook Affiliate / Reels (เน้นเล่าเรื่อง แก้ปัญหา แปะลิงก์)", "YouTube Shorts (เน้นเอนเตอร์เทน ภาพสวย)", "ทั่วไป (ใช้ได้ทุกที่)"], key="v_platform")
        st.selectbox("🎨 สไตล์ภาพ (Visual):", ["สมจริงเหมือนถ่ายทำจริง (Photorealistic)", "การ์ตูน 3D น่ารัก (Pixar/Disney Style)", "อนิเมะญี่ปุ่น (Anime)", "ลายเส้นมินิมอลคลีนๆ (Minimalist)", "สีน้ำละมุนๆ (Watercolor)", "สดใสป๊อปอาร์ต (Pop-Art)", "แสงสีไซไฟ (Cyberpunk)"], key="v_visual")
        st.selectbox("🎥 การเคลื่อนกล้อง (Camera):", ["มาตรฐาน (Smooth & Steady)", "ซูมเข้าช้าๆ (Slow Zoom in)", "ถือกล้องถ่ายเองสมจริง (Handheld Camera)", "ซูมฉวัดเฉวียนแบบวัยรุ่น (Fast Dynamic Zoom)", "สมูทช้าๆ แบบหนัง (Slow Pan & Cinematic Dolly)"], key="v_camera")
        st.selectbox("🎵 ดนตรีประกอบ (BGM):", ["เพลงป๊อปสนุกสนาน (Upbeat Pop)", "ดนตรีตื่นเต้นเร้าใจ (Energetic/Epic)", "ดนตรีชิลๆ สบายๆ (Lo-Fi/Chill)", "หรูหราคลาสสิก (Elegant/Orchestral)", "ตลกขบขัน (Funny/Quirky)", "ไม่มีดนตรี เน้น ASMR"], key="v_music")

    st.write("")
    
    btn_vid1, btn_vid2 = st.columns(2)
    with btn_vid1:
        if st.button("🚀 เจน Prompt วิดีโอ", type="primary", use_container_width=True):
            if not st.session_state.product_text.strip(): st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            elif not api_keys_list: st.error("🛑 กรุณาตั้งค่า API Key ก่อนครับ")
            else:
                with st.spinner("🎬 ผู้กำกับ AI กำลังเขียนสคริปต์..."):
                    try:
                        prompt_cmd = f"""คุณคือผู้กำกับโฆษณามืออาชีพ จงเขียนสคริปต์และ Prompt สร้างภาพและวิดีโอจากข้อมูล:
                        สินค้า: {st.session_state.product_text}
                        แพลตฟอร์มเป้าหมาย: {st.session_state.v_platform}
                        พรีเซนเตอร์: {st.session_state.v_presenter} | น้ำเสียง: {st.session_state.v_tone} | ภาษา: {st.session_state.v_lang}
                        สไตล์ภาพ: {st.session_state.v_visual} | การเคลื่อนกล้อง: {st.session_state.v_camera}
                        การเล่าเรื่อง: {st.session_state.v_story} | ดนตรีประกอบ: {st.session_state.v_music}
                        ความยาวรวม: {st.session_state.v_duration} | ข้อความบนจอ: {st.session_state.v_text_overlay}
                        กลุ่มเป้าหมาย: {st.session_state.v_target} | ปิดการขาย: {st.session_state.v_cta}
                        
                        🚨 กฎเหล็ก:
                        1. บรรทัดแรกสุด ให้ขึ้นต้นด้วยคำว่า "💡 สคริปต์นี้เหมาะสำหรับแพลตฟอร์ม:" แล้ววิเคราะห์สั้นๆ
                        2. บรรทัดถัดมา ให้เริ่มเข้าสคริปต์ด้วยคำว่า "ฉากที่ 1" ทันที
                        3. จังหวะและการเล่าเรื่องต้องอิงตาม "แพลตฟอร์มเป้าหมาย" และ "การเคลื่อนกล้อง" ที่กำหนด
                        4. ความต่อเนื่อง (Seamless Flow): ภาพแต่ละฉากต้องเล่าเรื่องต่อกันอย่างสมูท
                        5. 🚨 รูปแบบฉากต้องครบถ้วน โดยเฉพาะบรรทัด "-🖼️ Prompt สร้างภาพนิ่ง:" ให้เขียนเป็นภาษาอังกฤษล้วน และ **ต้องใส่คำบรรยายรูปร่างหน้าตาและสีของสินค้าลงไปใน Prompt อย่างละเอียดทุกฉาก ห้ามใช้คำกว้างๆ**
                        6. โครงสร้างแต่ละฉาก: ฉากที่, ความยาว, มุมกล้อง, ภาพที่เห็น, ข้อความบนจอ, เสียง, บทพูด, Prompt สร้างภาพนิ่ง, Prompt สร้างวิดีโอ
                        7. 🚨 เรื่องภาษาและสำเนียง (สำคัญมาก): เนื่องจากคุณเลือกภาษาเป็น "{st.session_state.v_lang}" หากเป็นภาษาถิ่น จงเขียนบทพูด (🗣️ บทพูด) ด้วยคำศัพท์ท้องถิ่นแท้ๆ และสะกดคำตามเสียงอ่านสำเนียงถิ่น (Phonetic spelling) แบบจัดเต็ม เพื่อบังคับให้ AI Voice อ่านออกเสียงได้ใกล้เคียงคนท้องถิ่นที่สุด"""
                        result_text = smart_generate(prompt_cmd)
                        st.session_state.generated_video_prompt = result_text
                        st.success("✅ สร้าง Prompt วิดีโอสำเร็จ!")
                    except Exception as e: st.error(f"❌ โหมดเจนวิดีโอล้มเหลว: {e}")
                        
    with btn_vid2:
        if st.button("✍️ AI คิดแคปชั่นป้ายยา", type="secondary", use_container_width=True):
            if not st.session_state.product_text.strip(): st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            elif not api_keys_list: st.error("🛑 กรุณาตั้งค่า API Key ก่อนครับ")
            else:
                with st.spinner("✍️ นักก็อปปี้ไรท์เตอร์ AI กำลังปั่นแคปชั่น..."):
                    try:
                        prompt_cmd = f"ข้อมูลสินค้า: {st.session_state.product_text}\nน้ำเสียง: {st.session_state.v_tone}\nจงเขียนแคปชั่นแยก 3 แพลตฟอร์ม (Facebook, TikTok, Shopee)\n🚨 สำหรับ Shopee ต้องไม่เกิน 150 ตัวอักษร"
                        st.session_state.generated_captions = smart_generate(prompt_cmd)
                        st.success("✅ คิดแคปชั่นสำเร็จ!")
                    except Exception as e: st.error(f"❌ ล้มเหลว: {e}")

    if st.session_state.generated_captions:
        st.markdown("---")
        st.info(st.session_state.generated_captions)

    if st.session_state.generated_video_prompt:
        st.markdown("---")
        view_mode = st.radio("🖥️ เลือกรูปแบบการใช้งาน:", ["💻 ใช้บนคอมพิวเตอร์", "📱 ใช้บนมือถือ"], horizontal=True)
        raw_text = st.session_state.generated_video_prompt
        if "ฉากที่ 1" in raw_text:
            header_text, scenes_text = raw_text.split("ฉากที่ 1", 1)
            if header_text.strip(): st.success(header_text.strip())
            scenes = re.split(r'(?:\n|^)(?=ฉากที่\s*\d+)', "ฉากที่ 1" + scenes_text)
        else: 
            scenes = re.split(r'(?:\n|^)(?=ฉากที่\s*\d+)', raw_text)
            
        valid_scenes = [s for s in scenes if len(s.strip()) > 5]

        if "คอมพิวเตอร์" in view_mode:
            bot_credit = st.radio("เลือกระบบเครดิต:", ["Lower Priority (ฟรี)", "Fast (10 เครดิต)"], horizontal=True)
            credit_val = "Lower Priority" if "ฟรี" in bot_credit else "Fast"
            for i, scene_text in enumerate(valid_scenes):
                scene_num = i + 1
                full_scene_text = scene_text.strip() 
                with st.expander(f"🎬 ฉากที่ {scene_num}", expanded=True):
                    edited_prompt = st.text_area(f"สคริปต์ฉากที่ {scene_num}", value=full_scene_text, height=350, key=f"text_{i}")
                    terminal_box = st.empty()
                    if st.button(f"🚀 สั่งบอทลุยฉาก {scene_num}", type="primary", key=f"btn_scene_{i}"):
                        if not st.session_state.uploaded_img_paths: st.error("🛑 อัปโหลดรูปภาพก่อน!")
                        else:
                            is_first = True if scene_num == 1 else False
                            ref_img_path = st.session_state.uploaded_img_paths[0] 
                            extracted_img_prompt = edited_prompt
                            if "🖼️ Prompt สร้างภาพนิ่ง:" in edited_prompt:
                                extracted_img_prompt = edited_prompt.split("🖼️ Prompt สร้างภาพนิ่ง:")[1].split("-🎞️")[0].strip()
                            
                            task_payload = {
                                "type": "scene_pipeline", 
                                "prompt": extracted_img_prompt, 
                                "credit_mode": credit_val, 
                                "ref_image": ref_img_path,
                                "scene_num": scene_num,
                                "is_first_scene": is_first
                            }
                            with open("bot_task.json", "w", encoding="utf-8") as f: 
                                json.dump(task_payload, f, ensure_ascii=False)
                            
                            log_text = f"> เริ่มรันบอทฉาก {scene_num}...\n"
                            terminal_box.code(log_text, language="bash")
                            try:
                                # ✨ จุดแก้บั๊ก: เพิ่ม env ให้บังคับส่งท่อ UTF-8 และใส่ errors="replace" ✨
                                custom_env = os.environ.copy()
                                custom_env["PYTHONIOENCODING"] = "utf-8"
                                
                                process = subprocess.Popen(
                                    ["python", "-u", "test_bot.py"], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT, 
                                    text=True, 
                                    encoding="utf-8",
                                    errors="replace", # ป้องกันระบบแครชถ้าอ่านอักษรไทยไม่ได้
                                    env=custom_env
                                )
                                for line in process.stdout: 
                                    log_text += line
                                    terminal_box.code(log_text, language="bash")
                                process.wait() 
                                if process.returncode == 0: st.success(f"✅ บอททำงานสำเร็จ!")
                                else: st.error("❌ บอทขัดข้อง ดูใน Terminal")
                            except Exception as e: st.error(f"❌ เรียกบอทล้มเหลว: {e}")
        else:
            st.info("📱 กดปุ่ม Copy ที่มุมขวากล่องข้อความด้านล่าง เพื่อนำไปใช้ในมือถือ")
            st.code(st.session_state.generated_video_prompt, language="markdown")

with tab_poster:
    p_head_col, p_ai_col = st.columns([4, 1])
    with p_head_col: st.markdown("### 🖼️ แผงควบคุมโปสเตอร์ (Poster Settings)")
    with p_ai_col:
        if st.button("✨ ให้ AI ช่วยตั้งค่าโปสเตอร์", use_container_width=True):
            if not st.session_state.product_text.strip(): st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            else:
                with st.spinner("🎨 AI กำลังวิเคราะห์สไตล์โปสเตอร์..."):
                    time.sleep(1)
                    text = st.session_state.product_text.lower()
                    if any(w in text for w in ["โปร", "ลด", "แถม", "ถูก", "sale"]): 
                        st.session_state.p_style = "Hard Sale / โปรแรง (ตะโกนขาย)"
                        st.session_state.p_color = "สีแดง/เหลือง/ส้ม (ร้อนแรง กระตุ้น)"
                        st.session_state.p_typography = "ฟอนต์ตัวหนาตะโกนขาย (Bold & Impactful)"
                    elif any(w in text for w in ["พรีเมียม", "หรู", "แพง", "บำรุง"]): 
                        st.session_state.p_style = "Minimalist / มินิมอล (คลีนๆ)"
                        st.session_state.p_color = "สีขาวดำ/เทา (หรูหรา มินิมอล)"
                        st.session_state.p_typography = "ฟอนต์เรียบหรูมินิมอล (Elegant & Clean)"
                    else:
                        st.session_state.p_style = "Soft Sell / อารมณ์ไลฟ์สไตล์"
                        st.session_state.p_typography = "ฟอนต์ร่วมสมัยอ่านง่าย (Modern Sans-serif)"
                    st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("📄 สไตล์โปสเตอร์:", ["Hard Sale / โปรแรง (ตะโกนขาย)", "Soft Sell / อารมณ์ไลฟ์สไตล์", "Minimalist / มินิมอล (คลีนๆ)", "Infographic / อธิบายจุดขาย", "Magazine Cover / ปกนิตยสาร", "Pop-Art / Y2K", "Meme / มีมไวรัล"], key="p_style")
        st.selectbox("📌 การจัดวางองค์ประกอบ (Composition):", ["สินค้าอยู่ตรงกลางเด่นๆ (Center Focus)", "สินค้าอยู่มุมขวา เว้นซ้ายใส่ข้อความ (Right Align)", "สินค้าอยู่มุมซ้าย เว้นขวาใส่ข้อความ (Left Align)", "ถ่ายจากมุมบนลงล่าง (Top-down Flatlay)", "ซูมเจาะดีเทลสินค้า (Macro Detail Shot)"], key="p_composition")
    with col2:
        st.selectbox("📏 สัดส่วนภาพ:", ["แนวนอน 16:9", "แนวนอน 4:3", "จัตุรัส 1:1", "แนวตั้ง 3:4", "แนวตั้ง 9:16"], key="p_ratio")
        st.selectbox("🎨 โทนสีหลัก:", ["สีแบรนด์ตามรูปสินค้า", "สีแดง/เหลือง/ส้ม (ร้อนแรง กระตุ้น)", "สีพาสเทล (น่ารัก ละมุน)", "สีขาวดำ/เทา (หรูหรา มินิมอล)", "สีนีออนสะท้อนแสง"], key="p_color")
    st.selectbox("🅰️ สไตล์ตัวอักษร (Typography Mood):", ["ฟอนต์ตัวหนาตะโกนขาย (Bold & Impactful)", "ฟอนต์เรียบหรูมินิมอล (Elegant & Clean)", "ฟอนต์ลายมือเป็นกันเอง (Handwritten/Friendly)", "ฟอนต์ล้ำยุคไซไฟ (Futuristic/Tech)"], key="p_typography")
    
    if st.button("🚀 เจน Prompt โปสเตอร์", type="primary", use_container_width=True):
        if not st.session_state.product_text.strip(): st.warning("⚠️ ใส่ข้อมูลสินค้าก่อน!")
        elif not api_keys_list: st.error("🛑 ตั้งค่าคีย์ก่อน!")
        else:
            with st.spinner("🧠 ออกแบบโปสเตอร์..."):
                try:
                    prompt_cmd = f"""คุณคืออาร์ตไดเรกเตอร์มืออาชีพ จงเขียน Prompt บรรยายภาพเพื่อใช้สำหรับ AI สร้างภาพ เพื่อสร้างโปสเตอร์โฆษณาที่ดึงดูดที่สุด โดยใช้ข้อมูลดังนี้:
                    สินค้า: {st.session_state.product_text}
                    สไตล์: {st.session_state.p_style} | สัดส่วน: {st.session_state.p_ratio}
                    โทนสี: {st.session_state.p_color} | การจัดวาง: {st.session_state.p_composition}
                    สไตล์ตัวอักษร: {st.session_state.p_typography}
                    🚨 กฎเหล็ก:
                    1. ตัว Prompt โครงสร้างหลักให้เขียนเป็น "ภาษาอังกฤษ"
                    2. การใส่ตัวหนังสือ (Typography): ให้คัดลอกคำโฆษณาภาษาไทยเด็ดๆ จากข้อมูลสินค้า ไปวางใน Prompt ตามตำแหน่งที่เหมาะสม โดย **ต้องครอบด้วยเครื่องหมายคำพูด ("...") เสมอ**"""
                    st.session_state.generated_poster_prompt = smart_generate(prompt_cmd)
                    st.success("✅ สร้าง Prompt โปสเตอร์สำเร็จ!")
                except Exception as e: st.error(f"❌ ล้มเหลว: {e}")
    if st.session_state.generated_poster_prompt:
        st.markdown("---")
        st.code(st.session_state.generated_poster_prompt, language="markdown")