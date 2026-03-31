import streamlit as st
import time
from google import genai 
from PIL import Image
import json
import subprocess
import os

# 🚨 ตั้งค่าหน้าจอ (ต้องอยู่บนสุด)
st.set_page_config(layout="wide", page_title="AutoBot Director", page_icon="🎬")

# ==========================================
# 🔑 ตั้งค่า API Key ถาวร (ฝังในโค้ด)
# ==========================================
MY_API_KEY = "AIzaSyBVwfDhiN1BfFfgrbvjD865CCPv2o38H5o"

if MY_API_KEY != "ใส่_API_KEY_ของคุณที่นี่":
    client = genai.Client(api_key=MY_API_KEY)

# ==========================================
# 🧠 0. ตั้งค่าระบบความจำ (Session State) 
# ==========================================
if 'product_text' not in st.session_state: st.session_state.product_text = ""
if 'generated_video_prompt' not in st.session_state: st.session_state.generated_video_prompt = ""
if 'generated_poster_prompt' not in st.session_state: st.session_state.generated_poster_prompt = ""
if 'generated_captions' not in st.session_state: st.session_state.generated_captions = ""
if 'uploaded_img_paths' not in st.session_state: st.session_state.uploaded_img_paths = []

# ค่าเริ่มต้นสำหรับ Dropdown ทั้ง 11 ตัว
if 'v_presenter' not in st.session_state: st.session_state.v_presenter = "ชาย (Male)"
if 'v_tone' not in st.session_state: st.session_state.v_tone = "เพื่อนป้ายยา (เป็นกันเอง)"
if 'v_ratio' not in st.session_state: st.session_state.v_ratio = "แนวตั้ง 9:16 (Story / Reels / TikTok)"
if 'v_lang' not in st.session_state: st.session_state.v_lang = "ไทยมาตรฐาน"
if 'v_style' not in st.session_state: st.session_state.v_style = "UGC (รีวิวบ้านๆ จริงใจ)"
if 'v_story' not in st.session_state: st.session_state.v_story = "PAS (ขยี้ปัญหาแล้วเสนอทางแก้)"
if 'v_duration' not in st.session_state: st.session_state.v_duration = "มาตรฐานกำลังดี (30 วินาที)"
if 'v_text_overlay' not in st.session_state: st.session_state.v_text_overlay = "ข้อความภาษาไทย"
if 'v_visual' not in st.session_state: st.session_state.v_visual = "สมจริง (Photorealistic)"
if 'v_target' not in st.session_state: st.session_state.v_target = "ทั่วไป (Mass)"
if 'v_cta' not in st.session_state: st.session_state.v_cta = "กดตะกร้าสีเหลือง"

# ==========================================
# 🎨 UI Header
# ==========================================
st.markdown("<h1>😀 ระบบผู้กำกับโฆษณา AI (AutoBot_Project)</h1>", unsafe_allow_html=True)
st.markdown("**1. อัปโหลดรูป -> 2. ดึงข้อความ -> 3. เลือกแท็บ -> 4. กดเจน Prompt**")

# ==========================================
# 📸 1. ส่วนดึงข้อความและบันทึกรูปภาพ (พร้อมระบบแก้บั๊ก Error 429)
# ==========================================
with st.expander("➕ อัปโหลดรูปภาพอ้างอิง (สินค้า, พรีเซนเตอร์)", expanded=True):
    uploaded_files = st.file_uploader("Drag and drop files here", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    if uploaded_files:
        st.session_state.uploaded_img_paths = []
        if not os.path.exists("temp_refs"): 
            os.makedirs("temp_refs")
        for img_file in uploaded_files:
            file_path = os.path.abspath(os.path.join("temp_refs", img_file.name))
            with open(file_path, "wb") as f:
                f.write(img_file.getbuffer())
            st.session_state.uploaded_img_paths.append(file_path)

    if st.button("🔍 ดึงข้อความและจุดขายจากรูปภาพ", type="secondary", use_container_width=True):
        if not uploaded_files:
            st.warning("⚠️ กรุณาอัปโหลดรูปภาพก่อนครับ")
        elif MY_API_KEY == "ใส่_API_KEY_ของคุณที่นี่":
            st.error("🛑 กรุณาใส่ API Key ในโค้ดบรรทัดที่ 15 ก่อนครับ")
        else:
            with st.spinner("กำลังให้ AI สแกนข้อความจากรูปภาพ (พักหายใจทีละใบเพื่อความเสถียร)..."):
                try:
                    extracted_info = ""
                    for i, img_file in enumerate(uploaded_files):
                        img = Image.open(img_file)
                        prompt = "ดึงข้อความทั้งหมดที่เห็นในภาพนี้ออกมาให้ละเอียดที่สุด พร้อมสรุปจุดเด่นและโปรโมชันที่น่าสนใจ"
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=[img, prompt])
                        extracted_info += f"**ข้อมูลจากรูป {img_file.name}:**\n{response.text}\n\n"
                        
                        # ⏱️ แก้บั๊ก Error 429: พักหายใจ 4 วินาที ก่อนสแกนรูปถัดไป
                        if i < len(uploaded_files) - 1:
                            time.sleep(4)
                    
                    st.session_state.product_text = extracted_info
                    st.success("✅ ดึงข้อความและบันทึกรูปต้นฉบับสำเร็จ!")
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดจาก AI: {e}")

st.markdown("### 📝 รายละเอียดสินค้าสำหรับแต่งสคริปต์")
product_input = st.text_area("ข้อความที่สแกนได้:", value=st.session_state.product_text, height=200)
st.session_state.product_text = product_input 
st.divider()

# ==========================================
# 🎛️ 3. เลือกโหมดการทำงานหลัก
# ==========================================
st.markdown("### 🎛️ เลือกโหมดการทำงานหลัก")
tab_video, tab_poster = st.tabs(["🎬 โหมดสร้างคลิปวิดีโอ (Pipeline)", "🖼️ โหมดสร้างโปสเตอร์โฆษณา"])

with tab_video:
    head_col, ai_col = st.columns([4, 1])
    with head_col:
        st.markdown("#### 🎬 แผงควบคุมวิดีโอ (Video Settings)")
    with ai_col:
        if st.button("✨ ให้ AI ช่วยตั้งค่าวิดีโอ", use_container_width=True):
            if not st.session_state.product_text.strip():
                st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            else:
                with st.spinner("🧠 AI กำลังคิด..."):
                    time.sleep(1) 
                    text = st.session_state.product_text.lower()
                    if any(w in text for w in ["หญิง", "สวย", "สกินแคร์", "ลิป", "กระโปรง"]): st.session_state.v_presenter = "หญิง (Female)"
                    elif any(w in text for w in ["น่ารัก", "สัตว์", "หมา", "แมว"]): st.session_state.v_presenter = "มาสคอตสัตว์น่ารัก (Mascot)"
                    else: st.session_state.v_presenter = "ชาย (Male)"
                    if any(w in text for w in ["พรีเมียม", "หรู", "แพง", "อสังหา"]): 
                        st.session_state.v_style = "Cinematic (พรีเมียม)"
                        st.session_state.v_tone = "หรูหรา / พรีเมียม"
                    else:
                        st.session_state.v_style = "UGC (รีวิวบ้านๆ จริงใจ)"
                        st.session_state.v_tone = "เพื่อนป้ายยา (เป็นกันเอง)"
                    st.rerun()

    # แผงควบคุม 11 โหมด พร้อมคำแนะนำ (Tooltip)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("👤 ผู้พูด/พรีเซนเตอร์:", ["ชาย (Male)", "หญิง (Female)", "ไม่ระบุเพศ / LGBTQ+", "มาสคอตสัตว์น่ารัก (Mascot)", "ไม่มีพรีเซนเตอร์ (เน้นสินค้า)"], key="v_presenter", help="เลือกตามกลุ่มเป้าหมาย")
        st.selectbox("🗣️ น้ำเสียง:", ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "ผู้เชี่ยวชาญ / น่าเชื่อถือ", "หรูหรา / พรีเมียม", "กวนๆ / ขี้เล่น"], key="v_tone", help="อารมณ์การพูด")
        st.selectbox("📱 สัดส่วนวิดีโอ:", ["แนวตั้ง 9:16 (Story / Reels / TikTok)", "แนวนอน 16:9 (YouTube / TV)"], key="v_ratio")
        st.selectbox("🌐 ภาษาของคลิป:", ["ไทยมาตรฐาน", "อังกฤษ (English)", "ไม่มีเสียงพูด"], key="v_lang")
    with col2:
        st.selectbox("🎥 สไตล์วิดีโอ:", ["UGC (รีวิวบ้านๆ จริงใจ)", "Cinematic (พรีเมียม)", "Unboxing / ASMR"], key="v_style")
        st.selectbox("📖 การเล่าเรื่อง:", ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "FOMO (กระตุ้นความกลัวพลาดโปร)"], key="v_story")
        st.selectbox("⏳ ความยาวคลิปรวม:", ["สั้นกระชับฮุกคนดู (15 วินาที)", "มาตรฐานกำลังดี (30 วินาที)"], key="v_duration")
        st.selectbox("💬 สไตล์ข้อความบนจอ:", ["ข้อความภาษาไทย (ตัวใหญ่เน้นๆ)", "ข้อความภาษาอังกฤษ", "ไม่มีข้อความบนจอ"], key="v_text_overlay")
    with col3:
        st.selectbox("🎨 สไตล์ภาพ (Visual):", ["สมจริง (Photorealistic)", "การ์ตูน 3D (Pixar Style)", "อนิเมะญี่ปุ่น (Anime)"], key="v_visual")
        st.selectbox("🎯 กลุ่มเป้าหมาย:", ["ทั่วไป (Mass)", "วัยรุ่น Gen Z", "พนักงานออฟฟิศ", "แม่บ้าน / คนมีครอบครัว"], key="v_target")
        st.selectbox("👉 ปิดการขาย (CTA):", ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ", "คลิกลิงก์หน้าโปรไฟล์", "เก็บคูปองส่วนลด"], key="v_cta")

    st.write("")
    
    if st.button("🚀 เจน Prompt วิดีโอ", type="primary", use_container_width=True):
        if not st.session_state.product_text.strip():
            st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
        else:
            with st.spinner("🎬 ผู้กำกับ AI กำลังเขียนสคริปต์ Full Storyboard..."):
                try:
                    prompt_cmd = f"""คุณคือผู้กำกับโฆษณามืออาชีพ จงเขียนสคริปต์จากข้อมูล:
                    สินค้า: {st.session_state.product_text}
                    สไตล์: {st.session_state.v_style} | ความยาวรวม: {st.session_state.v_duration} | CTA: {st.session_state.v_cta}
                    
                    🚨 กฎเหล็ก:
                    1. ห้ามเกริ่นนำ ให้เริ่มบรรทัดแรกด้วย "ฉากที่ 1" ทันที
                    2. แต่ละฉากต้องมี: ความยาว, มุมกล้อง, ภาพที่เห็น, ข้อความบนจอ, เสียง, บทพูด, Prompt สร้างภาพนิ่ง(Eng), Prompt สร้างวิดีโอ(Eng)"""
                    
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_cmd)
                    st.session_state.generated_video_prompt = response.text
                    st.success("✅ สร้างสคริปต์สำเร็จ!")
                except Exception as e:
                    st.error(f"❌ โหมดเจนวิดีโอล้มเหลว: {e}")

    # แผงควบคุมโรงงาน (Pipeline)
    if st.session_state.generated_video_prompt:
        st.divider()
        raw_text = st.session_state.generated_video_prompt
        scenes = raw_text.split("ฉากที่")
        valid_scenes = [s for s in scenes if len(s.strip()) > 5]

        for i, scene_text in enumerate(valid_scenes):
            scene_num = i + 1
            with st.expander(f"🎬 คิวถ่ายทำ: ฉากที่ {scene_num}", expanded=True):
                edited_prompt = st.text_area(f"สคริปต์ฉากที่ {scene_num}", value="ฉากที่" + scene_text, height=300, key=f"text_{i}")
                terminal_box = st.empty()
                if st.button(f"🚀 สั่งบอทลุยฉากที่ {scene_num}", key=f"btn_{i}"):
                    # (ส่วนเรียกใช้บอท test_bot.py ตามโค้ดเดิม)
                    pass

with tab_poster:
    st.info("โหมดโปสเตอร์ซ่อนไว้เพื่อโฟกัสวิดีโอ")