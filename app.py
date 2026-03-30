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
MY_API_KEY = "AIzaSyDtWuQH1jibqUk5AT5yHu35E00InHjRvuA"

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

    # 🌟 ครบ 11 โหมด พร้อม Tooltip คำอธิบาย!
    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("👤 ผู้พูด/พรีเซนเตอร์:", 
                     ["ชาย (Male)", "หญิง (Female)", "ไม่ระบุเพศ / LGBTQ+", "มาสคอตสัตว์น่ารัก (Mascot)", "ไม่มีพรีเซนเตอร์ (เน้นสินค้า)"], 
                     key="v_presenter", help="เลือกพรีเซนเตอร์ให้ตรงกับกลุ่มเป้าหมาย")
        st.selectbox("🗣️ น้ำเสียง:", 
                     ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "ผู้เชี่ยวชาญ / น่าเชื่อถือ", "หรูหรา / พรีเมียม", "กวนๆ / ขี้เล่น"], 
                     key="v_tone", help="อารมณ์และสไตล์การพูดของพรีเซนเตอร์")
        st.selectbox("📱 สัดส่วนวิดีโอ:", 
                     ["แนวตั้ง 9:16 (Story / Reels / TikTok)", "แนวนอน 16:9 (YouTube / TV)"], 
                     key="v_ratio", help="9:16 เหมาะกับมือถือ / 16:9 เหมาะกับจอใหญ่")
        st.selectbox("🌐 ภาษาของคลิป:", 
                     ["ไทยมาตรฐาน", "อังกฤษ (English)", "ไม่มีเสียงพูด (ใส่เพลงอย่างเดียว)"], 
                     key="v_lang", help="กำหนดภาษาของบทพูดพากย์เสียง")
                     
    with col2:
        st.selectbox("🎥 สไตล์วิดีโอ:", 
                     ["UGC (รีวิวบ้านๆ จริงใจ)", "Cinematic (พรีเมียม)", "Unboxing / ASMR"], 
                     key="v_style", help="UGC จะดูเป็นธรรมชาติที่สุดเหมือนคนซื้อมาใช้จริง")
        st.selectbox("📖 การเล่าเรื่อง:", 
                     ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "FOMO (กระตุ้นความกลัวพลาดโปร)"], 
                     key="v_story", help="โครงสร้างการเล่าเรื่องเพื่อดึงคนดูให้จบ")
        st.selectbox("⏳ ความยาวคลิปรวม:", 
                     ["สั้นกระชับฮุกคนดู (15 วินาที)", "มาตรฐานกำลังดี (30 วินาที)"], 
                     key="v_duration", help="ความยาวคลิปโดยรวม (AI จะแบ่งเวลาแต่ละฉากให้เอง)")
        st.selectbox("💬 สไตล์ข้อความบนจอ:", 
                     ["ข้อความภาษาไทย (ตัวใหญ่เน้นๆ)", "ข้อความภาษาอังกฤษ", "ไม่มีข้อความบนจอ"], 
                     key="v_text_overlay", help="สำหรับทำ Text Overlay แปะทับลงในคลิปเพื่อดึงดูดสายตา")
                     
    with col3:
        st.selectbox("🎨 สไตล์ภาพ (Visual):", 
                     ["สมจริง (Photorealistic)", "การ์ตูน 3D (Pixar Style)", "อนิเมะญี่ปุ่น (Anime)"], 
                     key="v_visual", help="สไตล์ภาพอ้างอิงสำหรับส่งให้ AI Generate ภาพและวิดีโอ")
        st.selectbox("🎯 กลุ่มเป้าหมาย:", 
                     ["ทั่วไป (Mass)", "วัยรุ่น Gen Z", "พนักงานออฟฟิศ", "แม่บ้าน / คนมีครอบครัว"], 
                     key="v_target", help="กำหนดบริบทและคำศัพท์ให้ตรงกับคนดู")
        st.selectbox("👉 ปิดการขาย (CTA):", 
                     ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ", "คลิกลิงก์หน้าโปรไฟล์", "เก็บคูปองส่วนลด"], 
                     key="v_cta", help="Call to Action: สิ่งที่อยากให้คนดูทำตอนจบคลิป")
        
    st.write("")
    
    btn_vid1, btn_vid2 = st.columns(2)
    with btn_vid1:
        if st.button("🚀 เจน Prompt วิดีโอ", type="primary", use_container_width=True):
            if not st.session_state.product_text.strip():
                st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
            else:
                with st.spinner("🎬 ผู้กำกับ AI กำลังเขียนสคริปต์และ Prompt ภาพ..."):
                    try:
                        # 🚨 กฎเหล็ก + ข้อมูลจาก 11 โหมดครบถ้วน!
                        prompt_cmd = f"""คุณคือผู้กำกับโฆษณามืออาชีพ จงเขียนสคริปต์และ Prompt สร้างภาพและวิดีโอจากข้อมูล:
                        สินค้า: {st.session_state.product_text}
                        พรีเซนเตอร์: {st.session_state.v_presenter} | น้ำเสียง: {st.session_state.v_tone} | ภาษา: {st.session_state.v_lang}
                        สไตล์: {st.session_state.v_style} | การเล่าเรื่อง: {st.session_state.v_story} | ความยาวรวม: {st.session_state.v_duration}
                        งานภาพ: {st.session_state.v_visual} | กลุ่มเป้าหมาย: {st.session_state.v_target} 
                        ข้อความบนจอ: {st.session_state.v_text_overlay} | ปิดการขาย: {st.session_state.v_cta}
                        
                        🚨 กฎเหล็ก (Strict Rules) ต้องทำตามอย่างเคร่งครัด:
                        1. ห้ามมีคำเกริ่นนำ ทักทาย สรุป หรือคำอธิบายใดๆ นอกเหนือจากสคริปต์เด็ดขาด
                        2. ให้เริ่มต้นข้อความบรรทัดแรกด้วยคำว่า "ฉากที่ 1" ทันที
                        3. รูปแบบของแต่ละฉากต้องมีองค์ประกอบครบถ้วนตามนี้เป๊ะๆ (ห้ามเปลี่ยนคำนำหน้าหัวข้อ):
                        
                        ฉากที่ [หมายเลข]
                        -⏱️ ความยาว: [กี่วินาที]
                        -🎥 มุมกล้อง: [เช่น Close-up, Pan left, Zoom in]
                        -🎬 ภาพที่เห็น: [อธิบายการกระทำ หรือสิ่งที่เกิดขึ้นในวิดีโอ]
                        -💬 ข้อความบนจอ: [คำโปรยตามสไตล์ {st.session_state.v_text_overlay}]
                        -🎵 เสียง: [ดนตรีประกอบ หรือเสียงเอฟเฟกต์]
                        -🗣️ บทพูด: [ข้อความบทพูดภาษา {st.session_state.v_lang} และเน้น CTA {st.session_state.v_cta} ในฉากสุดท้าย]
                        -🖼️ Prompt สร้างภาพนิ่ง: (ภาษาอังกฤษล้วน บรรยายภาพ {st.session_state.v_visual} อย่างละเอียด เพื่อใช้สร้างรูปตั้งต้น)
                        -🎞️ Prompt สร้างวิดีโอ: (ภาษาอังกฤษล้วน บรรยายการเคลื่อนไหว/Motion ที่ต่อเนื่องจากภาพนิ่ง เพื่อให้ AI วิดีโอขยับภาพ)"""
                        
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
                        ปิดการขายด้วย: {st.session_state.v_cta}
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

        raw_text = st.session_state.generated_video_prompt
        scenes = raw_text.split("ฉากที่")
        valid_scenes = [s for s in scenes if len(s.strip()) > 5]

        for i, scene_text in enumerate(valid_scenes):
            scene_num = i + 1
            full_scene_text = "ฉากที่" + scene_text
            
            with st.expander(f"🎬 คิวถ่ายทำ: ฉากที่ {scene_num}", expanded=True):
                edited_prompt = st.text_area(f"สคริปต์ฉากที่ {scene_num}", value=full_scene_text, height=350, key=f"text_{i}")
                
                terminal_box = st.empty()

                if st.button(f"🚀 สั่งบอทลุย 'ฉากที่ {scene_num}' (อัปโหลดรูปต้นฉบับ ➡️ เจนภาพนิ่งพื้นฐาน)", type="primary", key=f"btn_scene_{i}"):
                    if not st.session_state.uploaded_img_paths:
                        st.error("🛑 กรุณาอัปโหลดรูปภาพด้านบนให้เรียบร้อยก่อนครับ (บอทต้องการรูปอ้างอิง)")
                    else:
                        ref_img_path = st.session_state.uploaded_img_paths[0] 
                        
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