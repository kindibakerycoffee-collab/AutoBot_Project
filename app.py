import streamlit as st
import time
from google import genai
from PIL import Image
import json
import subprocess
import os
import re

# ==========================================
# 🚨 1. ตั้งค่าหน้าเว็บหลัก
# ==========================================
try:
    logo_img = Image.open("logo.png") 
except FileNotFoundError:
    logo_img = "🤖" 

st.set_page_config(page_title="NextGen Ai STORE | Super App", page_icon=logo_img, layout="wide")

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
# 🗂️ 2. เมนูนำทาง (Sidebar)
# ==========================================
if logo_img != "🤖": st.sidebar.image(logo_img, width=150)
st.sidebar.markdown("### 🗂️ เมนูหลัก (Main Menu)")
app_mode = st.sidebar.radio("เลือกโหมดการทำงาน:", [
    "🎬 โหมดโฆษณาสินค้า (Ad Director)", 
    "🐾 โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator)",
    "🎭 โหมดคาแรคเตอร์สายฮา (Comedy Caricature)",
    "🎤 โหมดวิทยากร AI (AI Spokesperson)",
    "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger Review)"
])
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 สถานะ API Key")
if not api_keys_list: st.sidebar.error("❌ ยังไม่ได้ใส่ API Key")
else:
    for i in range(len(api_keys_list)): st.sidebar.markdown(f"**หมายเลข {i+1}:** {st.session_state.key_status.get(i, '⏳')}")

# =========================================================================================
# 🎬 โหมดที่ 1: โฆษณาสินค้า (Ad Director)
# =========================================================================================
if app_mode == "🎬 โหมดโฆษณาสินค้า (Ad Director)":
    st.markdown("<h1>😀 ระบบผู้กำกับโฆษณา AI</h1>", unsafe_allow_html=True)
    if 'ad_product_text' not in st.session_state: st.session_state.ad_product_text = ""
    if 'ad_video_prompt' not in st.session_state: st.session_state.ad_video_prompt = ""

    with st.expander("📸 1. อัปโหลด Reference Image (ล็อกหน้าตาสินค้า)", expanded=True):
        uploaded_files = st.file_uploader("ลากรูปภาพสินค้ามาวางที่นี่", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="ad_up")
        if st.button("🔍 สกัดข้อมูลสินค้า", type="secondary", use_container_width=True) and uploaded_files:
            with st.spinner("กำลังสกัดข้อมูล..."):
                info = ""
                for img_file in uploaded_files:
                    info += smart_generate([Image.open(img_file), "บรรยายรูปร่าง ลักษณะ สี วัสดุ และรูปทรงของตัวสินค้าในภาพอย่างละเอียด เพื่อนำไปใช้เป็นข้อมูลล็อกสินค้า (Ingredient Lock)"]) + "\n"
                st.session_state.ad_product_text = info
                st.success("✅ สกัดสำเร็จ!")

    st.session_state.ad_product_text = st.text_area("📝 ข้อมูลตั้งต้นสำหรับ Scene Builder:", value=st.session_state.ad_product_text, height=100)
    st.divider()
    
    st.markdown("### 🎬 2. ตั้งค่าสคริปต์ผู้กำกับ")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("👤 พรีเซนเตอร์:", ["ชายหนุ่ม (Young Male)", "หญิงสาว (Young Female)", "ไม่มีพรีเซนเตอร์"], "ad_pres")
        render_custom_select("🗣️ น้ำเสียง:", ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "หรูหรา / พรีเมียม"], "ad_tone")
        render_custom_select("🎯 กลุ่มเป้าหมาย:", ["ทั่วไป (Mass)", "วัยรุ่น Gen Z"], "ad_target")
        render_custom_select("🌐 ภาษาคลิป:", ["ไทยภาคกลาง", "อังกฤษ (English)"], "ad_lang")
    with c2:
        render_custom_select("🎥 สไตล์วิดีโอ:", ["UGC (รีวิวบ้านๆ จริงใจ)", "โทนภาพยนตร์ (Cinematic)", "โฆษณาทีวี (TV Commercial)"], "ad_style")
        render_custom_select("📖 การเล่าเรื่อง:", ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "Storytelling (เล่าเรื่องชวนติดตาม)"], "ad_story")
        render_custom_select("👉 ปิดการขาย (CTA):", ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ"], "ad_cta")
        render_custom_select("⏳ ความยาวคลิปรวม:", ["มาตรฐานกำลังดี (30 วินาที)", "สั้นกระชับฮุกคนดู (15 วินาที)"], "ad_dur")
    with c3:
        render_custom_select("📱 แพลตฟอร์ม:", ["TikTok / Shopee / Lazada", "Facebook Reels"], "ad_plat")
        render_custom_select("🎨 สไตล์ภาพ:", ["สมจริงเหมือนถ่ายทำจริง (Photorealistic)", "การ์ตูน 3D น่ารัก (Pixar/Disney Style)"], "ad_vis")
        render_custom_select("🎥 Camera Controls:", ["มาตรฐาน (Smooth & Steady)", "ซูมเข้าช้าๆ (Slow Zoom in)", "ถือกล้องถ่ายเองสมจริง (Handheld Camera)"], "ad_cam")
        render_custom_select("🎵 ดนตรีประกอบ:", ["เพลงป๊อปสนุกสนาน (Upbeat Pop)", "ดนตรีตื่นเต้นเร้าใจ (Energetic/Epic)"], "ad_music")

    if st.button("🚀 สั่ง AI เขียนสคริปต์โฆษณา", type="primary", use_container_width=True):
        if not st.session_state.ad_product_text.strip(): st.warning("⚠️ กรุณาใส่รายละเอียดสินค้าก่อนครับ")
        else:
            with st.spinner("🎬 ผู้กำกับ AI กำลังวางโครงสร้าง Scene Builder..."):
                prompt = f"""คุณคือผู้กำกับโฆษณามืออาชีพ จงเขียนสคริปต์วิดีโอจากข้อมูล:
                สินค้า: {st.session_state.ad_product_text}. พรีเซนเตอร์: {st.session_state.get('ad_pres')}. 
                สไตล์: {st.session_state.get('ad_style')}. กล้อง: {st.session_state.get('ad_cam')}
                🚨 กฎเหล็ก: โครงสร้างแต่ละฉากต้องมีบรรทัด "Prompt สร้างภาพนิ่ง:" และ "Prompt สร้างวิดีโอ:" แยกกันชัดเจนเป็นภาษาอังกฤษล้วน และใส่รายละเอียดสินค้าลงไปให้ครบ"""
                st.session_state.ad_video_prompt = smart_generate(prompt)

    if st.session_state.ad_video_prompt:
        st.markdown("---")
        st.code(st.session_state.ad_video_prompt, language="markdown")

# =========================================================================================
# 🐾 โหมดที่ 2: คลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator) 
# =========================================================================================
elif app_mode == "🐾 โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator)":
    st.markdown("<h1>🐾 สตูดิโอปั้นสัตว์เลี้ยงไวรัล (Anthropomorphic Duo & Audio)</h1>", unsafe_allow_html=True)
    if 'pet_video_prompt' not in st.session_state: st.session_state.pet_video_prompt = ""
    if 'pet_context_text' not in st.session_state: st.session_state.pet_context_text = ""

    with st.expander("📸 1. อัปโหลดรูปภาพ Reference (ล็อกบรรยากาศหรือหน้าตาสัตว์เลี้ยง)", expanded=True):
        uploaded_files = st.file_uploader("ลากรูปมาวางที่นี่", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="pet_uploader")
        if st.button("🔍 สกัดบรรยากาศจากภาพ", type="secondary", use_container_width=True) and uploaded_files:
            with st.spinner("AI กำลังวิเคราะห์รูปภาพ..."):
                st.session_state.pet_context_text = smart_generate([Image.open(uploaded_files[0]), "บรรยายสิ่งของ อาหาร หรือสัตว์เลี้ยงในภาพอย่างละเอียด เพื่อทำบริบทการสร้างภาพแนว Anthropomorphic"])
                st.success("✅ สกัดข้อมูลสำเร็จ!")
                
    st.session_state.pet_context_text = st.text_area("📝 ข้อมูลบริบทภาพ:", value=st.session_state.pet_context_text, height=100)
    st.divider()

    st.markdown("### 🎬 2. ตั้งค่าบทบาทให้แก๊งสี่ขา")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("🐱 ตัวละคร (Actor/Duo):", ["แมวสลิด 2 ตัว (Two Tabby Cats)", "แมว 1 ตัว (Single Tabby Cat)", "แมวส้มกับหมาโกลเด้น (Orange Cat and Golden Retriever)", "แมวส้มหัวโตตัวคน (Giant Cat Head on Human)"], "pet_actor")
        render_custom_select("👕 คอสตูม (Costume):", ["ไม่ใส่ชุด (Natural)", "ใส่ผ้ากันเปื้อนทั้งคู่ (Both wear aprons)", "ชุดพนักงานออฟฟิศผูกไท (Office Shirt and Tie)"], "pet_costume")
        render_custom_select("🔪 การกระทำ (Action):", ["ช่วยกันทำอาหาร / หั่นผัก / ตำส้มตำ", "แย่งกันกินอาหารอร่อยๆ", "นั่งโต๊ะทำงานบ่นเจ้านายด้วยกัน"], "pet_action")
    with c2:
        render_custom_select("🍔 พร็อพ (Props):", ["มะม่วงน้ำปลาหวาน", "หมูกระทะเตาถ่าน", "โน้ตบุ๊กและเอกสาร"], "pet_props")
        render_custom_select("🏡 สถานที่ (Setting):", ["แคร่ไม้ไผ่กลางทุ่งนา", "ห้องครัวไทยบ้านๆ", "คาเฟ่มินิมอล"], "pet_setting")
        render_custom_select("💬 ข้อความฮุกบนจอ (Text Hook):", ["POV: เมื่อทาสใช้ให้ทำกับข้าว", "มนุษย์เงินเดือนสู้ชีวิต", "ไม่มีข้อความบนจอ"], "pet_hook")
    with c3:
        st.markdown("**🎙️ เสียงและบทสนทนา (Audio Cues):**")
        render_custom_select("💬 บทสนทนา/เสียงพากย์:", ["เถียงกันเรื่องสูตรอาหาร (Arguing about the recipe)", "คุยกันนินทาเจ้านาย (Gossiping about the owner)", "ชวนกันกินของอร่อย (Inviting each other to eat)", "ไม่มีเสียงพูด (ASMR / BGM only)"], "pet_dialogue")

    if st.button("🚀 สั่ง AI เขียนสคริปต์มีมสัตว์เลี้ยง (พร้อมคำสั่งเสียง)", type="primary", use_container_width=True):
        prompt = f"""เขียนสคริปต์วิดีโอมีมสัตว์เลี้ยงพฤติกรรมเหมือนคน (Anthropomorphic)
        ตัวละคร: {st.session_state.get('pet_actor')} ใส่ชุด {st.session_state.get('pet_costume')}
        แอคชั่น: {st.session_state.get('pet_action')} กับ {st.session_state.get('pet_props')}
        สถานที่: {st.session_state.get('pet_setting')}
        บทพูด/เสียง (Audio Cues): {st.session_state.get('pet_dialogue')}
        
        🚨 กฎเหล็ก:
        1. ต้องมี "Prompt สร้างภาพนิ่ง:" และ "Prompt สร้างวิดีโอ:" แยกกันชัดเจนเป็นภาษาอังกฤษล้วน
        2. ใน "Prompt สร้างวิดีโอ:" ให้ฝังคำสั่งควบคุมเสียง (Audio cue) ลงไป เช่น "Audio: The two cats are talking and saying [บทสนทนา]" เพื่อให้ Veo 3.1 ลิปซิงค์ปาก
        3. ต้องใช้คำว่า "Anthropomorphic" และ "human-like hands" เพื่อให้สัตว์ทำกิจกรรมได้สมจริง"""
        st.session_state.pet_video_prompt = smart_generate(prompt)

    if st.session_state.pet_video_prompt:
        st.markdown("---")
        st.code(st.session_state.pet_video_prompt, language="markdown")

# =========================================================================================
# 🎭 โหมดที่ 3: โหมดคาแรคเตอร์สายฮา (Comedy Caricature)
# =========================================================================================
elif app_mode == "🎭 โหมดคาแรคเตอร์สายฮา (Comedy Caricature)":
    st.markdown("<h1>🎭 สตูดิโอปั้นมีมไทบ้าน (จบใน Google Flow 100%)</h1>", unsafe_allow_html=True)
    if 'meme_video_prompt' not in st.session_state: st.session_state.meme_video_prompt = ""

    st.markdown("### 🎨 ออกแบบคาแรคเตอร์และบทพูด")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("👥 จำนวนคน (Count):", ["2 คนนั่งคุยกัน (Duo Conversation)", "1 คน (Solo Portrait)"], "meme_count")
        render_custom_select("🤪 ลักษณะเด่น (Feature):", ["ผมฟูชี้ฟูเหมือนโดนไฟช็อต", "มัดจุกกลางหัวแบบโบราณ", "หน้าเหี่ยวย่นจัดๆ ฟันหลอ"], "meme_feature")
        render_custom_select("👕 การแต่งกาย (Costume):", ["เสื้อเก่าๆ ขาดๆ มอซอ (Ragged clothes)", "คาดผ้าขาวม้า (Loincloth)"], "meme_costume")
    with c2:
        render_custom_select("🍾 พร็อพคู่ใจ (Props):", ["ขวดเหล้าขาวและแก้วเป๊ก", "ถือสมาร์ทโฟน", "นั่งซ้อนมอเตอร์ไซค์เก่าๆ"], "meme_props")
        render_custom_select("🏡 ฉากหลัง (Setting):", ["แคร่ไม้ไผ่หน้าเถียงนา", "วงเหล้าหน้าร้านชำ"], "meme_setting")
        render_custom_select("🎨 สไตล์งานอาร์ต (Art Style):", ["3D Caricature (หัวโตเกินจริง ตัวลีบ)", "Hyper-realistic Comedy"], "meme_style")
    with c3:
        st.markdown("**🎙️ สั่งเสียงพูด (Audio Cues):**")
        render_custom_select("💬 บทพูดตัวละคร:", ["คุยโวเรื่องถูกหวย (Bragging about winning lottery)", "บ่นเมียหนี (Complaining about wife)", "ทวงหนี้เพื่อนแบบฮาๆ"], "meme_dialogue")

    if st.button("🚀 สั่ง AI เขียนสคริปต์มีมไทบ้าน (พร้อมคำสั่งเสียง)", type="primary", use_container_width=True):
        prompt = f"""เขียนสคริปต์วิดีโอมีมล้อเลียนตลกๆ (Caricature)
        จำนวนคน: {st.session_state.get('meme_count')} | ลักษณะเด่น: {st.session_state.get('meme_feature')}
        ชุด: {st.session_state.get('meme_costume')} | พร็อพ: {st.session_state.get('meme_props')}
        ฉาก: {st.session_state.get('meme_setting')} | สไตล์: {st.session_state.get('meme_style')}
        บทพูด/เสียง (Audio): {st.session_state.get('meme_dialogue')}

        🚨 กฎเหล็ก:
        1. ต้องมี "Prompt สร้างภาพนิ่ง:" และ "Prompt สร้างวิดีโอ:" แยกกันชัดเจนเป็นภาษาอังกฤษ
        2. ใน "Prompt สร้างวิดีโอ:" ให้เพิ่มคำสั่งควบคุมเสียง (Audio cue) ลงไปด้วยอย่างชัดเจน เพื่อให้ระบบ AI ลิปซิงค์ปากพร้อมเสียงพูด"""
        st.session_state.meme_video_prompt = smart_generate(prompt)

    if st.session_state.meme_video_prompt:
        st.markdown("---")
        st.code(st.session_state.meme_video_prompt, language="markdown")

# =========================================================================================
# 🎤 โหมดที่ 4: โหมดวิทยากร AI (AI Spokesperson) 
# =========================================================================================
elif app_mode == "🎤 โหมดวิทยากร AI (AI Spokesperson)":
    st.markdown("<h1>🎤 สตูดิโอวิทยากร AI (สร้างความน่าเชื่อถือ)</h1>", unsafe_allow_html=True)
    if 'spoke_raw_text' not in st.session_state: st.session_state.spoke_raw_text = ""
    if 'spoke_video_prompt' not in st.session_state: st.session_state.spoke_video_prompt = ""

    st.markdown("### 📝 1. เตรียมบทพูด (Script Preparation)")
    script_mode = st.radio("เลือกวิธีการสร้างสคริปต์:", ["💡 มีแค่หัวข้อ (ให้ AI ร่างบทให้)", "✍️ มีบทพูดอยู่แล้ว (พิมพ์เองหรือเอามาวาง)"], horizontal=True)
    
    col_input1, col_input2 = st.columns([3, 1])
    with col_input1:
        if "มีแค่หัวข้อ" in script_mode:
            topic_input = st.text_input("📌 พิมพ์หัวข้อที่ต้องการพูด:", placeholder="เช่น เทคนิคปั้นยอดขาย TikTok...")
            if st.button("✨ ให้ AI ร่างบทพูดให้", type="secondary"):
                if topic_input:
                    with st.spinner("กำลังเขียนบท..."):
                        st.session_state.spoke_raw_text = smart_generate(f"เขียนบทพูดหน้ากล้อง ความยาว 30-60 วินาที หัวข้อ: '{topic_input}'. ขอภาษาไทยที่ดูเป็นมืออาชีพ สละสลวย")
                else: st.warning("กรุณาใส่หัวข้อก่อนครับ")
        else:
            st.info("💡 นำข้อความที่คุณเตรียมไว้มาวางในกล่องด้านล่างได้เลยครับ")

    st.session_state.spoke_raw_text = st.text_area("✍️ บทพูดของคุณ (สามารถแก้ไขได้):", value=st.session_state.spoke_raw_text, height=150)

    if st.button("🪄 ขัดเกลาข้อความให้ดูโปรขึ้น (Refine Script)", type="secondary", use_container_width=True):
        if st.session_state.spoke_raw_text.strip():
            with st.spinner("AI กำลังปรับแก้สำนวน..."):
                st.session_state.spoke_raw_text = smart_generate(f"ขัดเกลาบทพูดต่อไปนี้ ให้ภาษาสละสลวย ดูเป็นมืออาชีพ น่าเชื่อถือ เป็นธรรมชาติ และเหมาะกับการพูดหน้ากล้อง: \n\n{st.session_state.spoke_raw_text}")
                st.rerun()
        else:
            st.warning("กรุณาใส่ข้อความในกล่องก่อนครับ")

    st.divider()
    st.markdown("### 🎬 2. ตั้งค่าภาพลักษณ์วิทยากร (Visual & Stage)")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("👤 วิทยากร (Speaker):", ["CEO หนุ่มไฟแรง (Young Male Tech CEO)", "นักธุรกิจหญิงมาดมั่น (Professional Businesswoman)", "กูรูผู้เชี่ยวชาญ (Middle-aged Expert Guru)"], "spoke_actor")
        render_custom_select("👕 คอสตูม (Costume):", ["เสื้อยืดกางเกงยีนส์ (Steve Jobs style)", "ชุดสูทเต็มยศ (Formal Business Suit)", "เสื้อเชิ้ตดูดี (Smart Casual)"], "spoke_costume")
    with c2:
        render_custom_select("🏡 สถานที่ (Setting):", ["เวทีสัมมนาใหญ่มีสปอตไลท์ (TED Talk Stage)", "สตูดิโอพอดแคสต์มีไมค์โครโฟน (Podcast Studio)", "ห้องทำงานผู้บริหารทันสมัย (Modern Office)"], "spoke_setting")
        render_custom_select("🎥 มุมกล้อง (Camera):", ["ครึ่งตัวหน้าตรงเห็นท่าทาง (Medium Frontal Shot)", "ซูมใกล้ใบหน้าเน้นอารมณ์ (Close-up)"], "spoke_camera")
    with c3:
        render_custom_select("🗣️ อารมณ์การพูด (Tone):", ["สร้างแรงบันดาลใจ มีพลัง (Inspirational)", "ให้ความรู้จริงจัง (Educational)", "เป็นกันเองน่าเชื่อถือ (Friendly)"], "spoke_tone")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์วิทยากร (พร้อมระบบลิปซิงค์)", type="primary", use_container_width=True):
        if not st.session_state.spoke_raw_text.strip(): st.error("🛑 กรุณาเตรียมบทพูดด้านบนก่อนครับ!")
        else:
            with st.spinner("🎬 กำลังเซ็ตอัประบบเวทีและแสงสี..."):
                prompt = f"""คุณคือโปรดิวเซอร์รายการพอดแคสต์ จงเขียน Prompt สร้างวิดีโอ AI จากข้อมูลต่อไปนี้:
                วิทยากร: {st.session_state.get('spoke_actor')} ใส่ชุด {st.session_state.get('spoke_costume')}
                สถานที่: {st.session_state.get('spoke_setting')} | มุมกล้อง: {st.session_state.get('spoke_camera')}
                อารมณ์และท่าทาง: {st.session_state.get('spoke_tone')}
                
                บทพูดที่ต้องลิปซิงค์ (Audio): "{st.session_state.spoke_raw_text}"

                🚨 กฎเหล็ก:
                1. ต้องมี "Prompt สร้างภาพนิ่ง:" และ "Prompt สร้างวิดีโอ:" แยกกันชัดเจนเป็นภาษาอังกฤษ
                2. ใน "Prompt สร้างวิดีโอ:" ให้เพิ่มคำสั่ง Audio ลงไปให้ชัดเจน เพื่อให้ระบบลิปซิงค์ปาก โดยอนุญาตให้นำ "บทพูดภาษาไทย" ไปใส่ในกล่องเครื่องหมายคำพูดของส่วน Audio ได้เลย เช่น Audio: The speaker says "[บทพูดภาษาไทย]" clearly."""
                st.session_state.spoke_video_prompt = smart_generate(prompt)

    if st.session_state.spoke_video_prompt:
        st.markdown("---")
        st.code(st.session_state.spoke_video_prompt, language="markdown")

# =========================================================================================
# 🍰 โหมดที่ 5: โหมดรีวิวร้านตัวเอง (Local Vlogger Review) - ฉบับ UGC ขั้นสุด!
# =========================================================================================
elif app_mode == "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger Review)":
    st.markdown("<h1>🍰 สตูดิโอเจ้าของร้านรีวิวเอง (UGC Vlogger)</h1>", unsafe_allow_html=True)
    if 'vlog_product_text' not in st.session_state: st.session_state.vlog_product_text = ""
    if 'vlog_video_prompt' not in st.session_state: st.session_state.vlog_video_prompt = ""

    st.markdown("### 📸 1. อัปโหลดรูปเมนูของร้าน (Ingredient Lock)")
    with st.expander("อัปโหลดรูปภาพอาหาร/เครื่องดื่มของจริงที่นี่", expanded=True):
        uploaded_files = st.file_uploader("ลากรูปภาพเมนูมาวางที่นี่", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="vlog_up")
        if st.button("🔍 สกัดข้อมูลเมนูเด็ด", type="secondary", use_container_width=True) and uploaded_files:
            with st.spinner("AI กำลังวิเคราะห์ความน่ากิน..."):
                st.session_state.vlog_product_text = smart_generate([Image.open(uploaded_files[0]), "บรรยายรูปร่าง หน้าตา สีสัน และเนื้อสัมผัสของอาหาร/เครื่องดื่มในภาพอย่างละเอียด เพื่อนำไปใช้ล็อกหน้าตาสินค้าให้ตรงปก"])
                st.success("✅ สกัดสำเร็จ!")
    
    st.session_state.vlog_product_text = st.text_area("📝 ข้อมูลหน้าตาอาหารตั้งต้น:", value=st.session_state.vlog_product_text, height=100)
    st.divider()

    st.markdown("### 🎬 2. จัดฉากและบทบาท Vlogger")
    c1, c2, c3 = st.columns(3)
    with c1:
        shop_name = st.text_input("🏠 ชื่อร้าน / แบรนด์:", placeholder="เช่น NextGen Ai STORE...")
        render_custom_select("👤 ผู้รีวิว (Vlogger):", ["ชายหนุ่มวัยรุ่น (Young Thai man)", "หญิงสาวน่ารัก (Cute Thai girl)", "เจ้าของร้านใจดี (Friendly shop owner)"], "vlog_actor")
        render_custom_select("📸 พร็อพถ่ายทำ (Vlog Props):", ["มีมือถือตั้งขาตั้งกล้องถ่ายอยู่บนโต๊ะ (Smartphone on tripod recording on table)", "ถือกล้องเซลฟี่ (Selfie style angle)", "ถ่ายมุมมองบุคคลที่ 1 (POV view)"], "vlog_props")
    with c2:
        menu_item = st.text_input("🍔 ชื่อเมนูที่จะรีวิว:", placeholder="เช่น เค้กช็อกโกแลตลาวา...")
        render_custom_select("🏡 สถานที่ (Setting):", ["คาเฟ่สไตล์มินิมอล แสงธรรมชาติ", "ห้องครัวทำเบเกอรี่", "หน้าร้านสตรีทฟู้ด"], "vlog_setting")
        render_custom_select("😋 แอคชั่นการรีวิว (Action):", ["ตักอาหารโชว์เนื้อสัมผัสใกล้ๆ กล้อง (Scooping food close to camera)", "กัดแล้วทำตาโตอร่อยมาก (Taking a bite with wide eyes)", "นั่งพูดป้ายยาพร้อมยิ้มแย้ม (Talking enthusiastically)"], "vlog_action")
    with c3:
        local_cta = st.text_input("📍 พิกัดร้าน / ปิดการขาย (CTA):", placeholder="เช่น ร้านอยู่พรหมโลก นครศรีฯ / สั่งใน Shopee...")
        render_custom_select("🗣️ ภาษา/สำเนียง (Dialect):", ["ภาษาใต้ (หรอยแรง)", "ภาษาอีสาน (แซ่บอีหลี)", "ภาษาเหนือ (ลำขนาด)", "ภาษาไทยกลาง (อร่อยมาก)"], "vlog_dialect")
        render_custom_select("💬 ป๊อปอัปบนจอ (Text Overlay):", ["อร่อยแสงออกปาก 10/10", "พิกัดลับห้ามพลาด!", "เมนูขายดีประจำร้าน", "ไม่มีข้อความบนจอ"], "vlog_text_overlay")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์รีวิวร้าน (พร้อมลิปซิงค์ภาษาถิ่น)", type="primary", use_container_width=True):
        if not menu_item or not st.session_state.vlog_product_text.strip():
            st.warning("⚠️ กรุณาอัปโหลดรูปและระบุชื่อเมนูก่อนครับ AI จะได้รีวิวได้ตรงปก!")
        else:
            with st.spinner("🎬 ผู้กำกับกำลังวางบล็อกกิ้ง Vlogger..."):
                prompt_cmd = f"""คุณคือ Vlogger รีวิวอาหารและเจ้าของร้านมืออาชีพ จงเขียนสคริปต์คลิปรีวิวเพื่อนำไปเจนในระบบ AI วิดีโอ 
                ข้อมูลร้าน: {shop_name} | เมนูเด็ด: {menu_item} | พิกัด/ปิดการขาย: {local_cta}
                หน้าตาอาหารที่ต้องล็อกให้ตรงปก: {st.session_state.vlog_product_text}
                ผู้รีวิว: {st.session_state.get('vlog_actor')} | สถานที่: {st.session_state.get('vlog_setting')}
                แอคชั่นการรีวิว: {st.session_state.get('vlog_action')} | มุมกล้อง/พร็อพ: {st.session_state.get('vlog_props')}
                ข้อความบนจอ: "{st.session_state.get('vlog_text_overlay')}"
                
                🗣️ ภาษาที่ใช้พูด (Audio Cues): ต้องเป็นสไตล์ {st.session_state.get('vlog_dialect')} (เขียนบทพูดและสำเนียงให้สอดคล้องกับพิกัดร้านและปิดการขายอย่างเป็นธรรมชาติ)

                🚨 กฎเหล็ก:
                1. ต้องมี "Prompt สร้างภาพนิ่ง:" และ "Prompt สร้างวิดีโอ:" แยกกันชัดเจนเป็นภาษาอังกฤษล้วน
                2. ใน "Prompt สร้างภาพนิ่ง:" ให้ใส่รายละเอียดของอาหาร (Ingredient Lock) สถานที่ และพร็อพลงไปให้ครบถ้วน
                3. ใน "Prompt สร้างวิดีโอ:" ให้ฝังคำสั่งควบคุมเสียง (Audio cue) ลงไปให้ชัดเจน เช่น Audio: The character enthusiastically says "[บทพูดรีวิว]" เพื่อให้ระบบ AI ลิปซิงค์ปากพร้อมพูดเสียง"""
                
                st.session_state.vlog_video_prompt = smart_generate(prompt_cmd)

    if st.session_state.vlog_video_prompt:
        st.markdown("---")
        st.code(st.session_state.vlog_video_prompt, language="markdown")