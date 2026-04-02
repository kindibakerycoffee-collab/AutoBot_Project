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

st.set_page_config(page_title="NextGen Ai STORE | Super App 8-in-1", page_icon=logo_img, layout="wide")

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
    "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger Review)",
    "🎙️ โหมดทอล์คโชว์สายปั่น (Stand-up & Satire)",
    "🕺 โหมดสายแดนซ์ชาเลนจ์ (AI Dance Challenge)",
    "🎶 โหมดห้องอัดเสียงเพลงแปลง (Parody Music Studio)"
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

    with st.expander("📸 1. อัปโหลด Reference Image (ล็อกหน้าตาสินค้า)"):
        uploaded_files = st.file_uploader("ลากรูปภาพสินค้ามาวางที่นี่", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="ad_up")
        if st.button("🔍 สกัดข้อมูลสินค้า", type="secondary", use_container_width=True) and uploaded_files:
            with st.spinner("กำลังสกัดข้อมูล..."):
                st.session_state.ad_product_text = smart_generate([Image.open(uploaded_files[0]), "บรรยายรูปร่าง ลักษณะ สินค้าอย่างละเอียด"])
                st.success("✅ สกัดสำเร็จ!")

    st.session_state.ad_product_text = st.text_area("📝 ข้อมูลสินค้า:", value=st.session_state.ad_product_text, height=100)
    
    st.markdown("### 🎬 2. ตั้งค่าสคริปต์")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("👤 พรีเซนเตอร์:", ["ชายหนุ่ม", "หญิงสาว", "ไม่มีพรีเซนเตอร์"], "ad_pres")
        render_custom_select("🗣️ น้ำเสียง:", ["เพื่อนป้ายยา", "ตื่นเต้นขายเก่ง"], "ad_tone")
    with c2:
        render_custom_select("🎥 สไตล์:", ["UGC (รีวิวบ้านๆ)", "Cinematic (ภาพยนตร์)"], "ad_style")
        render_custom_select("⏳ ความยาว:", ["30 วินาที", "15 วินาที"], "ad_dur")
    with c3:
        render_custom_select("📱 แพลตฟอร์ม:", ["TikTok / Shopee", "Facebook Reels"], "ad_plat")
        render_custom_select("🎥 มุมกล้อง:", ["มาตรฐาน", "ถือกล้องถ่ายเอง"], "ad_cam")

    if st.button("🚀 สั่ง AI เขียนสคริปต์โฆษณา", type="primary", use_container_width=True):
        prompt = f"เขียนสคริปต์วิดีโอโฆษณา สินค้า: {st.session_state.ad_product_text}. พรีเซนเตอร์: {st.session_state.get('ad_pres')}. สไตล์: {st.session_state.get('ad_style')}. แยก Prompt ภาพนิ่งและวิดีโอภาษาอังกฤษชัดเจน"
        st.session_state.ad_video_prompt = smart_generate(prompt)

    if st.session_state.ad_video_prompt:
        st.code(st.session_state.ad_video_prompt, language="markdown")

# =========================================================================================
# 🐾 โหมดที่ 2: คลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator)
# =========================================================================================
elif app_mode == "🐾 โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet Creator)":
    st.markdown("<h1>🐾 สตูดิโอปั้นสัตว์เลี้ยงไวรัล</h1>", unsafe_allow_html=True)
    if 'pet_video_prompt' not in st.session_state: st.session_state.pet_video_prompt = ""

    st.markdown("### 🎬 ตั้งค่าบทบาทให้แก๊งสี่ขา")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("🐱 ตัวละคร (Duo):", ["แมวสลิด 2 ตัว", "แมวส้ม 1 ตัว", "หมาโกลเด้น"], "pet_actor")
        render_custom_select("👕 คอสตูม:", ["ใส่ผ้ากันเปื้อน", "ไม่ใส่ชุด", "ชุดพนักงานออฟฟิศ"], "pet_costume")
        render_custom_select("🔪 แอคชั่น:", ["ช่วยกันทำอาหาร", "แย่งกันกินอาหาร", "นั่งบ่นเจ้านาย"], "pet_action")
    with c2:
        render_custom_select("🍔 พร็อพ:", ["มะม่วงน้ำปลาหวาน", "หมูกระทะ", "โน้ตบุ๊ก"], "pet_props")
        render_custom_select("🏡 สถานที่:", ["แคร่ไม้ไผ่กลางทุ่งนา", "ห้องครัวไทย", "คาเฟ่"], "pet_setting")
        render_custom_select("💬 ข้อความฮุก:", ["POV: ทาสใช้ให้ทำกับข้าว", "มนุษย์เงินเดือน", "ไม่มี"], "pet_hook")
    with c3:
        st.markdown("**🎙️ เสียงและบทสนทนา:**")
        render_custom_select("💬 บทสนทนา:", ["เถียงกันเรื่องสูตรอาหาร", "นินทาเจ้านาย", "ไม่มีเสียงพูด (ASMR)"], "pet_dialogue")

    if st.button("🚀 สั่ง AI เขียนสคริปต์สัตว์เลี้ยง", type="primary", use_container_width=True):
        prompt = f"เขียนสคริปต์มีมสัตว์เลี้ยง (Anthropomorphic) ตัวละคร: {st.session_state.get('pet_actor')} ชุด: {st.session_state.get('pet_costume')} แอคชั่น: {st.session_state.get('pet_action')} กับ {st.session_state.get('pet_props')} ฉาก: {st.session_state.get('pet_setting')} เสียง: {st.session_state.get('pet_dialogue')}. แยก Prompt ภาษาอังกฤษภาพและวิดีโอ (ใส่ Audio Cues ในวิดีโอ)"
        st.session_state.pet_video_prompt = smart_generate(prompt)

    if st.session_state.pet_video_prompt:
        st.code(st.session_state.pet_video_prompt, language="markdown")

# =========================================================================================
# 🎭 โหมดที่ 3: โหมดคาแรคเตอร์สายฮา (Comedy Caricature)
# =========================================================================================
elif app_mode == "🎭 โหมดคาแรคเตอร์สายฮา (Comedy Caricature)":
    st.markdown("<h1>🎭 สตูดิโอปั้นมีมไทบ้าน</h1>", unsafe_allow_html=True)
    if 'meme_video_prompt' not in st.session_state: st.session_state.meme_video_prompt = ""

    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("👥 จำนวน:", ["1 คน (Solo)", "2 คนนั่งคุยกัน"], "meme_count")
        render_custom_select("🤪 ลักษณะเด่น:", ["หน้าเหี่ยวย่น ฟันหลอ ยิ้มกว้าง", "ผมฟูชี้ฟู"], "meme_feature")
        render_custom_select("👕 ชุด:", ["ไม่ใส่เสื้อ คาดผ้าขาวม้า", "เสื้อเก่าๆ มอซอ"], "meme_costume")
    with c2:
        render_custom_select("🍾 พร็อพ:", ["ถือมีดกรีดยาง", "ขวดเหล้าขาว", "สมาร์ทโฟน"], "meme_props")
        render_custom_select("🏡 ฉาก:", ["สวนยางพารา", "เถียงนา", "วงเหล้า"], "meme_setting")
        render_custom_select("🎨 สไตล์:", ["3D Pixar Animation", "3D Caricature", "Hyper-realistic"], "meme_style")
    with c3:
        st.markdown("**🎙️ เสียงและบทบาท:**")
        render_custom_select("💬 บทพูด/เสียง:", ["ร้องเพลงตลกๆ (Singing)", "คุยโวเรื่องถูกหวย", "บ่นเมียหนี"], "meme_dialogue")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์มีมไทบ้าน", type="primary", use_container_width=True):
        prompt = f"เขียนสคริปต์วิดีโอล้อเลียน {st.session_state.get('meme_count')} คน ลักษณะ: {st.session_state.get('meme_feature')} ชุด: {st.session_state.get('meme_costume')} พร็อพ: {st.session_state.get('meme_props')} ฉาก: {st.session_state.get('meme_setting')} สไตล์: {st.session_state.get('meme_style')} บทพูด/ร้อง: {st.session_state.get('meme_dialogue')}. แยก Prompt ภาพนิ่งและวิดีโอ (พร้อม Audio cues)"
        st.session_state.meme_video_prompt = smart_generate(prompt)

    if st.session_state.meme_video_prompt:
        st.code(st.session_state.meme_video_prompt, language="markdown")

# =========================================================================================
# 🎤 โหมดที่ 4: โหมดวิทยากร AI (AI Spokesperson)
# =========================================================================================
elif app_mode == "🎤 โหมดวิทยากร AI (AI Spokesperson)":
    st.markdown("<h1>🎤 สตูดิโอวิทยากร AI</h1>", unsafe_allow_html=True)
    if 'spoke_raw_text' not in st.session_state: st.session_state.spoke_raw_text = ""
    if 'spoke_video_prompt' not in st.session_state: st.session_state.spoke_video_prompt = ""

    st.session_state.spoke_raw_text = st.text_area("📝 บทพูดของคุณ (Script):", value=st.session_state.spoke_raw_text, height=100)
    if st.button("🪄 ขัดเกลาข้อความให้ดูโปรขึ้น", type="secondary"):
        st.session_state.spoke_raw_text = smart_generate(f"ขัดเกลาให้สละสลวยดูเป็นมืออาชีพ: {st.session_state.spoke_raw_text}")
        st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("👤 วิทยากร:", ["CEO หนุ่มไฟแรง", "นักธุรกิจหญิง", "กูรูผู้เชี่ยวชาญ"], "spk_actor")
        render_custom_select("👕 ชุด:", ["เสื้อยืดกางเกงยีนส์", "ชุดสูทเต็มยศ"], "spk_costume")
    with c2:
        render_custom_select("🏡 ฉาก:", ["เวที TED Talk", "สตูดิโอพอดแคสต์"], "spk_setting")
        render_custom_select("🎥 มุมกล้อง:", ["ครึ่งตัวหน้าตรง", "ซูมใกล้ใบหน้า"], "spk_camera")
    with c3:
        render_custom_select("🗣️ อารมณ์:", ["สร้างแรงบันดาลใจ", "ให้ความรู้จริงจัง"], "spk_tone")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์วิทยากร", type="primary", use_container_width=True):
        st.session_state.spoke_video_prompt = smart_generate(f"เขียนสคริปต์ AI Spokesperson วิทยากร: {st.session_state.get('spk_actor')} ชุด: {st.session_state.get('spk_costume')} ฉาก: {st.session_state.get('spk_setting')} กล้อง: {st.session_state.get('spk_camera')} อารมณ์: {st.session_state.get('spk_tone')} บทพูด: {st.session_state.spoke_raw_text}. แยก Prompt ภาพและวิดีโอ (พร้อม Audio Cues)")
    if st.session_state.spoke_video_prompt:
        st.code(st.session_state.spoke_video_prompt, language="markdown")

# =========================================================================================
# 🍰 โหมดที่ 5: โหมดรีวิวร้านตัวเอง (Local Vlogger Review)
# =========================================================================================
elif app_mode == "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger Review)":
    st.markdown("<h1>🍰 สตูดิโอเจ้าของร้านรีวิวเอง (UGC Vlogger)</h1>", unsafe_allow_html=True)
    if 'vlog_product_text' not in st.session_state: st.session_state.vlog_product_text = ""
    if 'vlog_video_prompt' not in st.session_state: st.session_state.vlog_video_prompt = ""

    with st.expander("📸 1. อัปโหลดรูปเมนู (Ingredient Lock)"):
        uploaded_files = st.file_uploader("ลากรูปภาพมาวาง", type=['png', 'jpg', 'jpeg'], key="vlog_up")
        if st.button("🔍 สกัดข้อมูลเมนู") and uploaded_files:
            st.session_state.vlog_product_text = smart_generate([Image.open(uploaded_files), "บรรยายความน่ากินและหน้าตาอาหาร"])
            st.rerun()
    st.session_state.vlog_product_text = st.text_area("📝 ข้อมูลหน้าตาอาหาร:", value=st.session_state.vlog_product_text, height=60)
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        shop_name = st.text_input("🏠 ชื่อร้าน:", value="NextGen Ai STORE")
        render_custom_select("👤 ผู้รีวิว:", ["เจ้าของร้านใจดี", "ชายหนุ่มวัยรุ่น"], "vlog_actor")
        render_custom_select("📸 พร็อพกล้อง:", ["มีมือถือตั้งขาตั้งกล้องถ่ายอยู่บนโต๊ะ", "ถือกล้องเซลฟี่"], "vlog_props")
    with c2:
        menu_item = st.text_input("🍔 ชื่อเมนู:", placeholder="เช่น เค้กช็อกโกแลต...")
        render_custom_select("🏡 ฉาก:", ["คาเฟ่แสงธรรมชาติ", "หน้าร้านสตรีทฟู้ด"], "vlog_setting")
        render_custom_select("😋 แอคชั่น:", ["ตักอาหารโชว์เนื้อสัมผัสใกล้ๆ กล้อง", "กินโชว์ตาโต"], "vlog_action")
    with c3:
        local_cta = st.text_input("📍 พิกัด / CTA:", value="พิกัด: NextGen Ai STORE พรหมโลก นครศรีธรรมราช")
        render_custom_select("🗣️ ภาษาถิ่น:", ["ภาษาใต้ (หรอยแรง)", "ภาษาไทยกลาง", "ภาษาอีสาน"], "vlog_dialect")
        render_custom_select("💬 ข้อความบนจอ:", ["อร่อยแสงออกปาก", "พิกัดลับ!"], "vlog_overlay")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์รีวิวร้าน", type="primary", use_container_width=True):
        st.session_state.vlog_video_prompt = smart_generate(f"สคริปต์ Vlogger รีวิวร้าน {shop_name} เมนู {menu_item} พิกัด: {local_cta}. ข้อมูลอาหาร: {st.session_state.vlog_product_text}. ผู้รีวิว: {st.session_state.get('vlog_actor')} ภาษา: {st.session_state.get('vlog_dialect')}. แยก Prompt ภาพ/วิดีโอ (ใส่ Audio Cues ด้วย)")
    if st.session_state.vlog_video_prompt:
        st.code(st.session_state.vlog_video_prompt, language="markdown")

# =========================================================================================
# 🎙️ โหมดที่ 6: ทอล์คโชว์สายปั่น (Stand-up & Satire)
# =========================================================================================
elif app_mode == "🎙️ โหมดทอล์คโชว์สายปั่น (Stand-up & Satire)":
    st.markdown("<h1>🎙️ สตูดิโอทอล์คโชว์ & ปราศรัยสายฮา</h1>", unsafe_allow_html=True)
    if 'satire_raw_text' not in st.session_state: st.session_state.satire_raw_text = ""
    if 'satire_video_prompt' not in st.session_state: st.session_state.satire_video_prompt = ""

    topic = st.text_input("📌 หัวข้อที่จะบ่น / ปราศรัย:", placeholder="เช่น ของแพง, บ่นเมีย...")
    if st.button("✨ ให้ AI ร่างบทสุดปั่น", type="secondary"):
        st.session_state.satire_raw_text = smart_generate(f"เขียนบทเดี่ยวไมโครโฟน/ปราศรัยฮาๆ ประชดประชัน หัวข้อ: '{topic}'")
    st.session_state.satire_raw_text = st.text_area("✍️ บทพูดบนเวที:", value=st.session_state.satire_raw_text, height=100)
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("🐒 ตัวละคร:", ["ลิงแสมหน้าตึง", "ตัวเงินตัวทองใส่สูท", "ลุงหน้าตาย"], "satire_actor")
        render_custom_select("👕 ชุด:", ["คล้องพวงมาลัยดาวเรือง คาดผ้าขาวม้า", "ชุดสูทสีฉูดฉาด"], "satire_costume")
    with c2:
        render_custom_select("🏡 ฉาก:", ["เวทีปราศรัยมีป้ายไวนิล", "คลับมืดๆ มีสปอตไลท์"], "satire_setting")
        render_custom_select("🎙️ พร็อพ:", ["ยืนพูดหน้าไมค์ขาตั้ง", "ถือไมค์ด้วยมือ"], "satire_props")
    with c3:
        render_custom_select("🗣️ ท่าทาง:", ["ยกมือสองข้างขึ้น ชูไม้ชูมือ", "ยืนกอดอกหน้าตึง"], "satire_action")

    if st.button("🚀 สั่ง AI ปั้นสคริปต์ปราศรัย", type="primary", use_container_width=True):
        st.session_state.satire_video_prompt = smart_generate(f"สคริปต์วิดีโอล้อเลียน ตัวละคร: {st.session_state.get('satire_actor')} ชุด: {st.session_state.get('satire_costume')} ฉาก: {st.session_state.get('satire_setting')} บทพูด: {st.session_state.satire_raw_text}. ให้แยก Prompt ภาพและวิดีโอ (พร้อม Audio cues)")
    if st.session_state.satire_video_prompt:
        st.code(st.session_state.satire_video_prompt, language="markdown")

# =========================================================================================
# 🕺 โหมดที่ 7: สายแดนซ์ชาเลนจ์ (AI Dance Challenge)
# =========================================================================================
elif app_mode == "🕺 โหมดสายแดนซ์ชาเลนจ์ (AI Dance Challenge)":
    st.markdown("<h1>🕺 สตูดิโอปั้นนักเต้น AI (Character Sheets)</h1>", unsafe_allow_html=True)
    if 'dance_image_prompt' not in st.session_state: st.session_state.dance_image_prompt = ""

    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("🐱 ตัวละคร:", ["แมวส้ม", "หมีแพนด้า", "เด็กชายชุดนักเรียน"], "dance_actor")
        render_custom_select("👕 ชุดเต้น:", ["ชุดฮิปฮอปโอเวอร์ไซส์", "ชุดนักเรียนไทย"], "dance_outfit")
    with c2:
        render_custom_select("🏡 ฉากหลัง:", ["สีขาวคลีนๆ (Solid white)", "ห้องสตูดิโอซ้อมเต้น"], "dance_bg")
        render_custom_select("📏 มุมกล้อง:", ["เห็นเต็มตัวตั้งแต่หัวจรดเท้า (Full body shot)"], "dance_shot")
    with c3:
        render_custom_select("✨ พิเศษ:", ["ใส่รองเท้าผ้าใบเท่ๆ", "ใส่หมวกแก็ป"], "dance_extra")
        render_custom_select("🎨 สไตล์:", ["สมจริง 3D", "อนิเมะญี่ปุ่น"], "dance_style")

    if st.button("🚀 สั่ง AI เจน Prompt นักเต้นต้นแบบ", type="primary", use_container_width=True):
        st.session_state.dance_image_prompt = smart_generate(f"เขียน Prompt ภาษาอังกฤษสร้างภาพนิ่งตัวละครเต้น ตัวละคร: {st.session_state.get('dance_actor')} ชุด: {st.session_state.get('dance_outfit')} ฉาก: {st.session_state.get('dance_bg')} ต้องเป็น Full body shot หน้าตรง ห้ามแขนขาหลุดขอบ")
    if st.session_state.dance_image_prompt:
        st.code(st.session_state.dance_image_prompt, language="markdown")

# =========================================================================================
# 🎶 โหมดที่ 8: ห้องอัดเสียงเพลงแปลง (Parody Music Studio)
# =========================================================================================
elif app_mode == "🎶 โหมดห้องอัดเสียงเพลงแปลง (Parody Music Studio)":
    st.markdown("<h1>🎶 ห้องอัดเสียงเพลงแปลง (AI Music Studio)</h1>", unsafe_allow_html=True)
    if 'music_lyrics' not in st.session_state: st.session_state.music_lyrics = ""

    topic = st.text_input("📌 หัวข้อ/เรื่องที่จะบ่นในเพลง:", placeholder="เช่น ราคายางตก, เมียยึดเงินเดือน...")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("อารมณ์:", ["ตลกร้าย/ประชดประชัน", "กวนโอ๊ย"], "music_mood")
        render_custom_select("แนวดนตรี:", ["ลูกทุ่งโจ๊ะๆ", "หมอลำซิ่ง", "แร็ปฮิปฮอป", "เพื่อชีวิต"], "music_genre")
    with c2:
        render_custom_select("เครื่องดนตรีเด่น:", ["กีตาร์โปร่ง", "แคนและพิณ", "เบสหนักๆ"], "music_inst")
    with c3:
        render_custom_select("นักร้อง:", ["ผู้ชายเสียงแหบสู้ชีวิต", "แร็ปเปอร์เสียงดุดัน"], "music_vocal")

    if st.button("🚀 สั่ง AI แต่งเนื้อเพลงและ Prompt ทำดนตรี", type="primary", use_container_width=True):
        st.session_state.music_lyrics = smart_generate(f"แต่งเนื้อเพลง 1 นาที หัวข้อ: {topic} อารมณ์: {st.session_state.get('music_mood')} แนว: {st.session_state.get('music_genre')} ดนตรี: {st.session_state.get('music_inst')} นักร้อง: {st.session_state.get('music_vocal')}. สร้าง 2 ส่วน: 1. Prompt ดนตรีภาษาอังกฤษ 2. เนื้อเพลงภาษาไทยพร้อมโครงสร้าง (Intro, Chorus, etc.)")
    if st.session_state.music_lyrics:
        st.code(st.session_state.music_lyrics, language="markdown")