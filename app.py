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
MY_API_KEY = "AIzaSyCOQezcD-Rbxk9sy0e-HBJ9CMBO5dvUapc"

if MY_API_KEY != "ใส่_API_KEY_ของคุณที่นี่":
    client = genai.Client(api_key=MY_API_KEY)

# ==========================================
# 🧠 0. ตั้งค่าระบบความจำ (Session State) 
# ==========================================
if 'product_text' not in st.session_state: st.session_state.product_text = ""
if 'generated_video_prompt' not in st.session_state: st.session_state.generated_video_prompt = ""
if 'generated_poster_prompt' not in st.session_state: st.session_state.generated_poster_prompt = ""
if 'generated_captions' not in st.session_state: st.session_state.generated_captions = "" # คืนชีพแคปชั่น
if 'uploaded_img_paths' not in st.session_state: st.session_state.uploaded_img_paths = []

# ค่าเริ่มต้นสำหรับ Dropdown
if 'v_presenter' not in st.session_state: st.session_state.v_presenter = "ชาย (Male)"
if 'v_tone' not in st.session_state: st.session_state.v_tone = "เพื่อนป้ายยา (เป็นกันเอง)"
if 'v_ratio' not in st.session_state: st.session_state.v_ratio = "แนวตั้ง 9:16 (Story / Reels / TikTok)"
if 'v_text_overlay' not in st.session_state: st.session_state.v_text_overlay = "ข้อความภาษาไทย"
if 'v_style' not in st.session_state: st.session_state.v_style = "UGC (รีวิวบ้านๆ จริงใจ)"
if 'v_story' not in st.session_state: st.session_state.v_story = "PAS (ขยี้ปัญหาแล้วเสนอทางแก้)"
if 'v_cta' not in st.session_state: st.session_state.v_cta = "กดตะกร้าสีเหลือง"
if 'v_duration' not in st.session_state: st.session_state.v_duration = "มาตรฐานกำลังดี (30 วินาที)"
if 'v_visual' not in st.session_state: st.session_state.v_visual = "สมจริง (Photorealistic)"
if 'v_target' not in st.session_state: st.session_state.v_target = "ทั่วไป (Mass)"
if 'v_lang' not in st.session_state: st.session_state.v_lang = "ไทยมาตรฐาน"

if 'p_style' not in st.session_state: st.session_state.p_style = "Hard Sale / โปรแรง (ตะโกนขาย)"
if 'p_ratio' not in st.session_state: st.session_state.p_ratio = "แนวตั้ง 9:16 (Story / Reels / TikTok)"
if 'p_text_focus' not in st.session_state: st.session_state.p_text_focus = "เน้นราคา (Shopee/Lazada/TikTok)"
if 'p_color' not in st.session_state: st.session_state.p_color = "สีแบรนด์ตามรูปสินค้า (อิงจากภาพอ้างอิง)"

# ==========================================
# 🎨 UI Header
# ==========================================
st.markdown("<h1>😀 ระบบผู้กำกับโฆษณา AI (AutoBot_Project)</h1>", unsafe_allow_html=True)
st.markdown("**1. อัปโหลดรูป -> 2. ดึงข้อความ -> 3. เลือกแท็บ -> 4. กดเจน Prompt**")

# ==========================================
# 📸 1. ส่วนดึงข้อความและบันทึกรูปภาพ
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
            with st.spinner("กำลังให้ AI สแกนข้อความและจุดขายจากรูปภาพ..."):
                try:
                    extracted_info = ""
                    for img_file in uploaded_files:
                        img = Image.open(img_file)
                        prompt = "ดึงข้อความทั้งหมดที่เห็นในภาพนี้ออกมาให้ละเอียดที่สุด พร้อมสรุปจุดเด่นและโปรโมชันที่น่าสนใจ"
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=[img, prompt])
                        extracted_info += f"**ข้อมูลจากรูป {img_file.name}:**\n{response.text}\n\n"
                    
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

# ------------------------------------------
# 🎬 TAB 1: VIDEO MODE (Pipeline แบบโรงงาน)
# ------------------------------------------
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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("👤 ผู้พูด/พรีเซนเตอร์:", ["ชาย (Male)", "หญิง (Female)", "ไม่ระบุเพศ / LGBTQ+", "มาสคอตสัตว์น่ารัก (Mascot)", "ไม่มีพรีเซนเตอร์ (เน้นสินค้า)"], key="v_presenter")
        st.selectbox("🗣️ น้ำเสียง:", ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "ผู้เชี่ยวชาญ / น่าเชื่อถือ", "หรูหรา / พรีเมียม", "กวนๆ / ขี้เล่น"], key="v_tone")
        st.selectbox("📱 สัดส่วนวิดีโอ:", ["แนวตั้ง 9:16 (Story / Reels / TikTok)", "แนวนอน 16:9 (YouTube / TV)"], key="v_ratio")
    with col2:
        st.selectbox("🎥 สไตล์วิดีโอ:", ["UGC (รีวิวบ้านๆ จริงใจ)", "Cinematic (พรีเมียม)", "Unboxing / ASMR"], key="v_style")
        st.selectbox("📖 การเล่าเรื่อง:", ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "FOMO (กระตุ้นความกลัวพลาดโปร)"], key="v_story")
        st.selectbox("⏳ ความยาวคลิปรวม:", ["สั้นกระชับฮุกคนดู (15 วินาที)", "มาตรฐานกำลังดี (30 วินาที)"], key="v_duration")
    with col3:
        st.selectbox("🎨 สไตล์ภาพ (Visual):", ["สมจริง (Photorealistic)", "การ์ตูน 3D (Pixar Style)", "อนิเมะญี่ปุ่น (Anime)"], key="v_visual")
        st.selectbox("🎯 กลุ่มเป้าหมาย:", ["ทั่วไป (Mass)", "วัยรุ่น Gen Z", "พนักงานออฟฟิศ"], key="v_target")
        
    st.write("")
    
    # 🌟 นำปุ่มแคปชั่นกลับมาใส่คู่กับปุ่มเจนวิดีโอ
    btn_vid1, btn_vid2 = st.columns(2)
    with btn_vid1:
        if st.button("🚀 เจน Prompt วิดีโอ", type="primary", use_container_width=True):
            if not st.session_state.product_text.strip():
                st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            else:
                with st.spinner("🎬 ผู้กำกับ AI กำลังเขียนสคริปต์และ Prompt ภาพ..."):
                    try:
                        prompt_cmd = f"""คุณคือผู้กำกับโฆษณามืออาชีพ จงเขียนสคริปต์และ Prompt สร้างภาพวิดีโอจากข้อมูล:
                        สินค้า: {st.session_state.product_text}
                        พรีเซนเตอร์: {st.session_state.v_presenter} | สไตล์: {st.session_state.v_style} | งานภาพ: {st.session_state.v_visual}
                        ให้ตอบกลับมาเป็นฉากๆ ตามรูปแบบนี้เป๊ะๆ:
                        ฉากที่ [หมายเลข]
                        -บทพูด: [ข้อความบทพูด]
                        -การสร้างรูปภาพแต่ละคลิป: (ภาษาอังกฤษล้วนบรรยายภาพ {st.session_state.v_visual})"""
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_cmd)
                        st.session_state.generated_video_prompt = response.text
                        st.success("✅ สร้าง Prompt วิดีโอสำเร็จ! เลื่อนลงไปดูคิวถ่ายทำด้านล่างได้เลย")
                    except Exception as e:
                        st.error(f"❌ โหมดเจนวิดีโอล้มเหลว: {e}")
                        
    with btn_vid2:
        if st.button("✍️ AI คิดแคปชั่นป้ายยา (3 แพลตฟอร์ม)", type="secondary", use_container_width=True):
            if not st.session_state.product_text.strip():
                st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            elif MY_API_KEY == "ใส่_API_KEY_ของคุณที่นี่":
                st.error("🛑 กรุณาใส่ API Key ในโค้ดก่อนครับ")
            else:
                with st.spinner("✍️ นักก็อปปี้ไรท์เตอร์ AI กำลังปั่นแคปชั่น..."):
                    try:
                        prompt_cmd = f"""ข้อมูลสินค้า: {st.session_state.product_text}
                        น้ำเสียงแบรนด์: {st.session_state.v_tone}
                        จงเขียนแคปชั่นขายของแยกเป็น 3 แพลตฟอร์ม (Facebook, TikTok, Shopee)"""
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_cmd)
                        st.session_state.generated_captions = response.text
                        st.success("✅ คิดแคปชั่นสำเร็จ!")
                    except Exception as e:
                        st.error(f"❌ โหมดคิดแคปชั่นล้มเหลว: {e}")

    # แสดงผลแคปชั่น
    if st.session_state.generated_captions:
        st.markdown("---")
        st.markdown("##### ✍️ แคปชั่นสำหรับนำไปโพสต์ (Copy ได้เลย)")
        st.info(st.session_state.generated_captions)

    # ==========================================
    # ✂️ แผงควบคุมแบบแยกฉาก (Pipeline)
    # ==========================================
    if st.session_state.generated_video_prompt:
        st.markdown("---")
        st.markdown("### 🏭 แผงควบคุมโรงงานผลิตโฆษณา (คิวถ่ายทำทีละฉาก)")
        st.info("💡 ระบบจะดึงรูปที่คุณอัปโหลดไว้รูปแรกสุด ไปเป็น 'รูปอ้างอิง' ในการสร้างภาพนิ่งให้โดยอัตโนมัติ")
        
        st.markdown("⚙️ **ตั้งค่าเครดิตสำหรับบอท (ใช้กับทุกฉาก):**")
        bot_credit = st.radio("เลือกระบบเครดิต (Veo 3.1):", ["Lower Priority (ฟรี 0 เครดิต)", "Fast (ใช้ 10 เครดิต)"], horizontal=True)
        credit_val = "Lower Priority" if "ฟรี" in bot_credit else "Fast"

        # หั่นข้อความด้วยคำว่า "ฉากที่"
        raw_text = st.session_state.generated_video_prompt
        scenes = raw_text.split("ฉากที่")
        valid_scenes = [s for s in scenes if len(s.strip()) > 5]

        for i, scene_text in enumerate(valid_scenes):
            scene_num = i + 1
            full_scene_text = "ฉากที่" + scene_text
            
            with st.expander(f"🎬 คิวถ่ายทำ: ฉากที่ {scene_num}", expanded=True):
                # ให้ CEO แก้ไข Prompt ก่อนส่งได้
                edited_prompt = st.text_area(f"สคริปต์ฉากที่ {scene_num}", value=full_scene_text, height=150, key=f"text_{i}")
                
                # กล่อง Live Terminal ประจำฉาก
                terminal_box = st.empty()

                if st.button(f"🚀 สั่งบอทลุย 'ฉากที่ {scene_num}' (อัปโหลดรูปต้นฉบับ ➡️ เจนภาพนิ่งพื้นฐาน)", type="primary", key=f"btn_scene_{i}"):
                    if not st.session_state.uploaded_img_paths:
                        st.error("🛑 กรุณาอัปโหลดรูปภาพด้านบนให้เรียบร้อยก่อนครับ (บอทต้องการรูปอ้างอิง)")
                    else:
                        ref_img_path = st.session_state.uploaded_img_paths[0] # ดึงรูปแรกมาใช้
                        
                        # สร้างไฟล์คำสั่ง
                        with open("bot_task.json", "w", encoding="utf-8") as f:
                            json.dump({
                                "type": "scene_pipeline", 
                                "prompt": edited_prompt,
                                "credit_mode": credit_val,
                                "ref_image": ref_img_path
                            }, f, ensure_ascii=False)
                        
                        log_text = f"> เริ่มเดินเครื่องผลิต ฉากที่ {scene_num}...\n"
                        terminal_box.code(log_text, language="bash")
                        
                        try:
                            custom_env = os.environ.copy()
                            custom_env["PYTHONIOENCODING"] = "utf-8"
                            process = subprocess.Popen(
                                ["python", "-u", "test_bot.py"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=custom_env
                            )
                            for line in process.stdout:
                                log_text += line
                                terminal_box.code(log_text, language="bash")
                            process.wait() 
                            if process.returncode == 0:
                                st.success(f"✅ บอทสร้างภาพนิ่งสำหรับฉากที่ {scene_num} สำเร็จ! รอให้ภาพเจนเสร็จบนเว็บ แล้วมากดปุ่มทำวิดีโอต่อได้เลยครับ")
                            else:
                                st.error("❌ เกิดข้อผิดพลาด รบกวนดูใน Terminal ครับ")
                        except Exception as e:
                            st.error(f"❌ เรียกบอทไม่สำเร็จ: {e}")

# ------------------------------------------
# 🖼️ TAB 2: POSTER MODE
# ------------------------------------------
with tab_poster:
    st.info("โหมดโปสเตอร์ซ่อนไว้ก่อน เพื่อโฟกัสโหมดวิดีโอครับ (โค้ดยังทำงานปกติตามไฟล์เดิมครับ)")