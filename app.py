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
    if not api_keys_list: raise Exception("ไม่พบ API Key กรุณาตั้งค่าใน Secrets ก่อนครับ")
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
    raise Exception(f"API Key ติดลิมิตทั้งหมดแล้วครับ! กรุณารอประมาณ 1 นาทีแล้วลองใหม่")

def safe_generate(prompt):
    try:
        return smart_generate(prompt)
    except Exception as e:
        st.error(f"❌ ระบบขัดข้อง: {e}")
        return ""

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
    "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger Review)",
    "🪩 โหมดดีเจและปาร์ตี้ (DJ & Party Vibe)"
])
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 สถานะ API Key")
if not api_keys_list: st.sidebar.error("❌ ยังไม่ได้ใส่ API Key")
else:
    for i in range(len(api_keys_list)): st.sidebar.markdown(f"**คีย์ {i+1}:** {st.session_state.key_status.get(i, '⏳')}")
    if st.sidebar.button("🔄 รีเซ็ตคีย์", use_container_width=True):
        st.session_state.current_key_idx = 0
        st.session_state.key_status = {i: "⏳ สแตนด์บาย" for i in range(len(api_keys_list))}
        st.rerun()

# =========================================================================================
# 🎬 โหมดที่ 1: โฆษณาสินค้า (Ad Director)
# =========================================================================================
if app_mode == "🎬 โหมดโฆษณาสินค้า (Ad Director)":
    st.markdown("<h1>😀 ระบบผู้กำกับโฆษณา AI</h1>", unsafe_allow_html=True)
    if 'ad_product_text' not in st.session_state: st.session_state.ad_product_text = ""
    if 'ad_actor_text' not in st.session_state: st.session_state.ad_actor_text = ""
    if 'ad_video_prompt' not in st.session_state: st.session_state.ad_video_prompt = ""
    if 'ad_poster_prompt' not in st.session_state: st.session_state.ad_poster_prompt = ""

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        with st.expander("📦 1. อัปโหลดรูปสินค้า (Ingredient Lock)", expanded=True):
            up_prod = st.file_uploader("ลากรูปสินค้ามาวาง", type=['png', 'jpg', 'jpeg'], key="ad_prod_up")
            if st.button("🔍 สกัดข้อมูลสินค้า", key="btn_ad_prod") and up_prod:
                with st.spinner("กำลังสกัดข้อมูล..."):
                    st.session_state.ad_product_text = safe_generate([Image.open(up_prod), "บรรยายรูปร่าง ลักษณะ สินค้าอย่างละเอียดเพื่อนำไปเจาะจงใน Prompt"])
        st.session_state.ad_product_text = st.text_area("📝 ข้อมูลสินค้า:", value=st.session_state.ad_product_text, height=80)
    with col_up2:
        with st.expander("👤 2. อัปโหลดรูปตัวเอง/พรีเซนเตอร์ (Character Lock)", expanded=True):
            up_actor = st.file_uploader("ลากรูปหน้าคุณมาวาง", type=['png', 'jpg', 'jpeg'], key="ad_actor_up")
            if st.button("🔍 สกัดหน้าตาพรีเซนเตอร์", key="btn_ad_actor") and up_actor:
                with st.spinner("กำลังวิเคราะห์ใบหน้า..."):
                    st.session_state.ad_actor_text = safe_generate([Image.open(up_actor), "บรรยายใบหน้า ทรงผม เสื้อผ้า และลักษณะเด่นของบุคคลในภาพอย่างละเอียด"])
        st.session_state.ad_actor_text = st.text_area("📝 ข้อมูลพรีเซนเตอร์:", value=st.session_state.ad_actor_text, height=80)

    st.divider()
    st.markdown("### 🎬 3. ตั้งค่าการถ่ายทำ")
    c1, c2, c3 = st.columns(3)
    with c1: render_custom_select("🗣️ น้ำเสียง:", ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "หรูหรา / พรีเมียม"], "ad_tone")
    with c2: render_custom_select("🎥 สไตล์วิดีโอ:", ["UGC (รีวิวบ้านๆ)", "โทนภาพยนตร์ (Cinematic)", "โฆษณาทีวี (TV Commercial)"], "ad_style")
    with c3: render_custom_select("👉 ปิดการขาย (CTA):", ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ"], "ad_cta")

    tab_vid, tab_poster = st.tabs(["🎬 สร้างวิดีโอโฆษณา", "🖼️ สร้างแบนเนอร์สินค้า"])
    with tab_vid:
        if st.button("🚀 สั่ง AI เขียนสคริปต์วิดีโอ", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์วิดีโอโฆษณา. สินค้า: {st.session_state.ad_product_text}. หน้าตาพรีเซนเตอร์: {st.session_state.ad_actor_text}. สไตล์: {st.session_state.get('ad_style')}. กฎ: แยก Prompt ภาพนิ่งและวิดีโอเป็นภาษาอังกฤษ"
            st.session_state.ad_video_prompt = safe_generate(prompt)
        if st.session_state.ad_video_prompt: st.code(st.session_state.ad_video_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพ:", ["9:16", "1:1", "16:9"], key="ad_pratio")
        with col_p2: p_style = st.selectbox("📄 สไตล์โปสเตอร์:", ["Hard Sale", "Soft Sell"], key="ad_pstyle")
        if st.button("🎨 สั่ง AI เขียน Prompt สร้างโปสเตอร์", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt ภาษาอังกฤษสำหรับ Image Gen (Nano Banana 2). สินค้า: {st.session_state.ad_product_text}. หน้าตาคน: {st.session_state.ad_actor_text}. สไตล์: {p_style}. สัดส่วน: {p_ratio}."
            st.session_state.ad_poster_prompt = safe_generate(prompt)
        if st.session_state.ad_poster_prompt: st.code(st.session_state.ad_poster_prompt, language="markdown")

# =========================================================================================
# 🐾 โหมดที่ 2: คลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator) - อัปเกรดสายแดนซ์!! ✨
# =========================================================================================
elif app_mode == "🐾 โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator)":
    st.markdown("<h1>🐾 สตูดิโอปั้นสัตว์เลี้ยงไวรัล (แดนซ์/ทำอาหาร)</h1>", unsafe_allow_html=True)
    if 'pet_context_text' not in st.session_state: st.session_state.pet_context_text = ""
    if 'pet_video_prompt' not in st.session_state: st.session_state.pet_video_prompt = ""
    if 'pet_poster_prompt' not in st.session_state: st.session_state.pet_poster_prompt = ""

    with st.expander("📸 1. อัปโหลดรูปน้องหมา/น้องแมวของคุณ (Character Lock)"):
        up_pet = st.file_uploader("ลากรูปสัตว์เลี้ยงมาวาง", type=['png', 'jpg', 'jpeg'], key="pet_up")
        if st.button("🔍 สกัดคาแรคเตอร์สัตว์เลี้ยง") and up_pet:
            st.session_state.pet_context_text = safe_generate([Image.open(up_pet), "บรรยายลักษณะสัตว์เลี้ยง สีขน เพื่อใช้เป็นแบบ"])
    st.session_state.pet_context_text = st.text_area("📝 ข้อมูลสัตว์เลี้ยง:", value=st.session_state.pet_context_text, height=60)
    
    st.markdown("### 🎬 2. ตั้งค่าบทบาทให้แก๊งสี่ขา")
    c1, c2, c3 = st.columns(3)
    with c1: 
        render_custom_select("🐱 ตัวละคร:", ["แมวสลิด 1 ตัว", "แมวส้มหัวโตตัวคน", "หมาโกลเด้น", "อิงตามรูป"], "pet_actor")
        # ✨ อัปเกรดคอสตูม
        render_custom_select("👕 คอสตูม:", ["ชุด รปภ. (Security Guard)", "เสื้อยืดสกรีนลายเท่ๆ (Trendy T-shirt)", "ใส่ผ้ากันเปื้อน", "ไม่ใส่ชุด"], "pet_costume")
    with c2: 
        # ✨ อัปเกรดแอคชั่นเต้น
        render_custom_select("🕺 แอคชั่น:", ["ยืนสองขาเต้นแดนซ์กระจาย (Standing on two legs dancing energetically)", "ทำอาหาร/ตำส้มตำ (Cooking)", "แย่งกันกินอาหาร", "นั่งทำงานหน้าคอม"], "pet_action")
        render_custom_select("🍔 พร็อพประกอบ:", ["ไม่มีพร็อพ (เต้นอย่างเดียว)", "ขวดนมคล้องคอ (Baby bottle necklace)", "มะม่วงน้ำปลาหวาน", "โน้ตบุ๊ก"], "pet_props")
    with c3: 
        render_custom_select("🏡 สถานที่:", ["ในห้องน้ำสาธารณะ (Public Restroom)", "ห้องนั่งเล่น (Living room)", "แคร่ไม้ไผ่กลางทุ่งนา"], "pet_setting")
        # ✨ อัปเกรดการลิปซิงค์
        render_custom_select("🎙️ เสียงพากย์/เพลง:", ["ลิปซิงค์ร้องเพลงฮิต (Lip-syncing to a song)", "บ่นเจ้านาย", "เถียงกันฮาๆ", "ไม่มีเสียงพูด"], "pet_dialogue")
    
    tab_vid, tab_poster = st.tabs(["🎬 สร้างคลิปไวรัลสัตว์เลี้ยง", "🖼️ สร้างภาพปกคลิป"])
    with tab_vid:
        if st.button("🚀 สั่ง AI เขียนสคริปต์มีมสัตว์เลี้ยง", type="primary", use_container_width=True):
            prompt = f"""เขียนสคริปต์วิดีโอมีมสัตว์เลี้ยงพฤติกรรมเหมือนคน. 
            หน้าตา: {st.session_state.pet_context_text} ({st.session_state.get('pet_actor')}). 
            ชุด: {st.session_state.get('pet_costume')}. 
            แอคชั่น: {st.session_state.get('pet_action')} พร้อมกับพร็อพ {st.session_state.get('pet_props')}. 
            สถานที่: {st.session_state.get('pet_setting')}. 
            เสียง: {st.session_state.get('pet_dialogue')}. 
            
            กฎเหล็ก: แยก Prompt ภาพนิ่งและวิดีโอเป็นภาษาอังกฤษ 
            *ถ้าแอคชั่นคือการยืนสองขาเต้น ให้ระบุใน Prompt ว่า "anthropomorphic, standing on two legs like a human" ให้ชัดเจน 
            *ถ้ามีการลิปซิงค์ ให้ระบุใน Audio Cue ว่าให้ขยับปากร้องเพลง (singing/lip-syncing)"""
            st.session_state.pet_video_prompt = safe_generate(prompt)
        if st.session_state.pet_video_prompt: st.code(st.session_state.pet_video_prompt, language="markdown")
    
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพปก:", ["9:16", "1:1", "16:9"], key="pet_pratio")
        with col_p2: p_text = st.text_input("💬 ข้อความฮุกบนปก:", value="สเต็ปเทพ!", key="pet_ptext")
        
        if st.button("🎨 สั่ง AI เขียน Prompt สร้างภาพปก", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt ภาษาอังกฤษสำหรับ Image Gen ทำภาพปกคลิป. ภาพสัตว์เลี้ยง: {st.session_state.pet_context_text} กำลัง {st.session_state.get('pet_action')}. มีข้อความตัวใหญ่ว่า '{p_text}'. สัดส่วน: {p_ratio}"
            st.session_state.pet_poster_prompt = safe_generate(prompt)
        if st.session_state.pet_poster_prompt: st.code(st.session_state.pet_poster_prompt, language="markdown")

# =========================================================================================
# 🎭 โหมดที่ 3: โหมดคาแรคเตอร์สายฮา (Comedy Caricature)
# =========================================================================================
elif app_mode == "🎭 โหมดคาแรคเตอร์สายฮา (Comedy Caricature)":
    st.markdown("<h1>🎭 สตูดิโอปั้นมีมไทบ้าน</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: render_custom_select("🤪 ลักษณะเด่น:", ["ผมฟูชี้ฟู", "หน้าเหี่ยวย่นฟันหลอ", "มัดจุกบนหัว"], "meme_feature")
    with c2: render_custom_select("🍾 พร็อพคู่ใจ:", ["ขวดเหล้าขาว", "ไก่ชน", "สมาร์ทโฟน"], "meme_props")
    with c3: render_custom_select("🎙️ บทพูด:", ["คุยโวเรื่องถูกหวย", "ทวงหนี้เพื่อน", "นินทาเมีย"], "meme_dialogue")
    
    if st.button("🚀 สั่ง AI เขียนสคริปต์คลิปมีม", type="primary"):
        prompt = f"เขียนสคริปต์คลิปล้อเลียน (Caricature). ลักษณะ: {st.session_state.get('meme_feature')} | พร็อพ: {st.session_state.get('meme_props')} | บทพูด: {st.session_state.get('meme_dialogue')}. แยก Prompt ภาพนิ่งและวิดีโอเป็นอังกฤษ และใส่ Audio Cue ในวิดีโอ"
        st.code(safe_generate(prompt), language="markdown")

# =========================================================================================
# 🎤 โหมดที่ 4: โหมดวิทยากร AI (AI Spokesperson) 
# =========================================================================================
elif app_mode == "🎤 โหมดวิทยากร AI (AI Spokesperson)":
    st.markdown("<h1>🎤 สตูดิโอวิทยากร AI</h1>", unsafe_allow_html=True)
    if 'spoke_actor_text' not in st.session_state: st.session_state.spoke_actor_text = ""
    if 'spoke_raw_text' not in st.session_state: st.session_state.spoke_raw_text = ""
    with st.expander("👤 อัปโหลดรูปตัวเอง (Character Lock)"):
        up_spoke = st.file_uploader("ลากรูปมาวาง", type=['png', 'jpg', 'jpeg'], key="spoke_up")
        if st.button("🔍 สกัดหน้าตา") and up_spoke:
            st.session_state.spoke_actor_text = safe_generate([Image.open(up_spoke), "บรรยายใบหน้าและเสื้อผ้า"])
    st.session_state.spoke_raw_text = st.text_area("✍️ วางสคริปต์ที่จะให้พูด:", value=st.session_state.spoke_raw_text, height=100)
    
    if st.button("🚀 สั่ง AI ปั้นสคริปต์วิทยากร", type="primary"):
        prompt = f"เขียน Prompt สร้างวิดีโอ. หน้าตา: {st.session_state.spoke_actor_text}. บทพูด: '{st.session_state.spoke_raw_text}'. แยก Prompt ภาพนิ่งและวิดีโอเป็นอังกฤษ และใส่ Audio cue สำหรับลิปซิงค์"
        st.code(safe_generate(prompt), language="markdown")

# =========================================================================================
# 🍰 โหมดที่ 5: โหมดรีวิวร้านตัวเอง (Local Vlogger Review)
# =========================================================================================
elif app_mode == "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger Review)":
    st.markdown("<h1>🍰 สตูดิโอเจ้าของร้านรีวิวเอง (UGC Vlogger)</h1>", unsafe_allow_html=True)
    if 'vlog_product_text' not in st.session_state: st.session_state.vlog_product_text = ""
    if 'vlog_actor_text' not in st.session_state: st.session_state.vlog_actor_text = ""
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.session_state.vlog_product_text = st.text_area("📝 ข้อมูลอาหาร/สินค้า:", value=st.session_state.vlog_product_text, height=60)
    with col_v2:
        st.session_state.vlog_actor_text = st.text_area("📝 ข้อมูลผู้รีวิว:", value=st.session_state.vlog_actor_text, height=60)
    
    c1, c2 = st.columns(2)
    with c1: render_custom_select("🏡 สถานที่:", ["คาเฟ่มินิมอล", "หน้าร้าน"], "vlog_setting")
    with c2: render_custom_select("🗣️ ภาษาถิ่น:", ["ภาษาใต้", "ภาษาอีสาน", "ภาษาไทยกลาง"], "vlog_dialect")
    
    if st.button("🚀 สั่ง AI ปั้นสคริปต์รีวิวร้าน", type="primary"):
        prompt = f"เขียนสคริปต์รีวิว อาหาร: {st.session_state.vlog_product_text}. คนรีวิว: {st.session_state.vlog_actor_text}. สถานที่: {st.session_state.get('vlog_setting')}. ภาษา: {st.session_state.get('vlog_dialect')}. แยก Prompt ภาพนิ่ง/วิดีโอ และใส่ Audio Cue ให้ Veo ลิปซิงค์"
        st.code(safe_generate(prompt), language="markdown")

# =========================================================================================
# 🪩 โหมดที่ 6: โหมดดีเจและปาร์ตี้ (DJ & Party Vibe)
# =========================================================================================
elif app_mode == "🪩 โหมดดีเจและปาร์ตี้ (DJ & Party Vibe)":
    st.markdown("<h1>🪩 สตูดิโอปาร์ตี้ (DJ & Music Video)</h1>", unsafe_allow_html=True)
    if 'dj_actor_text' not in st.session_state: st.session_state.dj_actor_text = ""

    with st.expander("👤 อัปโหลดรูปดีเจ / ศิลปิน (Character Lock)"):
        up_dj = st.file_uploader("ลากรูปหน้าคุณหรือดีเจมาวางที่นี่", type=['png', 'jpg', 'jpeg'], key="dj_up")
        if st.button("🔍 สกัดหน้าตาศิลปิน") and up_dj:
            st.session_state.dj_actor_text = safe_generate([Image.open(up_dj), "บรรยายใบหน้า ทรงผม เสื้อผ้า"])
    
    st.session_state.dj_actor_text = st.text_area("📝 ข้อมูลลุคของศิลปิน:", value=st.session_state.dj_actor_text, height=60)
    
    c1, c2, c3 = st.columns(3)
    with c1: render_custom_select("🕺 แอคชั่นดีเจ:", ["สแครชแผ่นและโยกหัวแรงๆ", "ชูมือขึ้นฟ้าบิ๊วคนดู"], "dj_action")
    with c2: render_custom_select("💡 แสงสี (Lighting):", ["ไฟเลเซอร์พุ่งตัดสลับ", "ไฟดิสโก้หลากสี"], "dj_light")
    with c3: 
        audio_choice = st.radio("เลือกวิธีใส่เพลง:", ["🔊 ให้ AI สร้างเพลงประกอบให้เลย", "🔇 ไม่เอาเสียง / เอาไปใส่เพลงฮิตเอง"])
        if "🔊" in audio_choice: render_custom_select("🎵 แนวเพลง:", ["EDM สายตื๊ด", "สามช่า / ลูกทุ่ง"], "dj_genre")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์ปาร์ตี้", type="primary"):
        audio_instruction = f"ใส่ Audio Cue: High-energy {st.session_state.get('dj_genre')}" if "🔊" in audio_choice else "ไม่ต้องใส่ Audio แต่เน้นขยับเร็ว (Fast-paced)"
        prompt = f"เขียน Prompt สร้างวิดีโอ. ศิลปิน: {st.session_state.dj_actor_text}. แสงสี: {st.session_state.get('dj_light')}. แอคชั่น: {st.session_state.get('dj_action')}. แยก Prompt ภาพนิ่งและวิดีโอเป็นอังกฤษ. {audio_instruction}"
        st.code(safe_generate(prompt), language="markdown")