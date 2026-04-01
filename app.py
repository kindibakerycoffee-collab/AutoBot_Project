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

# ดึง API Key
api_keys_list = []
if "GEMINI_API_KEYS" in st.secrets: api_keys_list = st.secrets["GEMINI_API_KEYS"]
elif "GEMINI_API_KEY" in st.secrets: api_keys_list = [st.secrets["GEMINI_API_KEY"]]

if 'current_key_idx' not in st.session_state: st.session_state.current_key_idx = 0
if 'key_status' not in st.session_state: 
    st.session_state.key_status = {i: "⏳ สแตนด์บาย" for i in range(len(api_keys_list))}
    if api_keys_list: st.session_state.key_status[0] = "🟢 กำลังใช้งาน"

def smart_generate(prompt_contents):
    if not api_keys_list: raise Exception("ไม่พบ API Key ในระบบ")
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
    raise Exception("API Key ติดลิมิตทั้งหมดแล้วครับ! โปรดรอสักครู่")

def safe_generate(prompt):
    try: return smart_generate(prompt)
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
    else: st.session_state[key] = selected

def magic_setup(mode_desc, options_dict, context_info=""):
    prompt = f"""คุณคือผู้ช่วย AI อัจฉริยะ จงเลือกการตั้งค่าที่สร้างสรรค์ที่สุดสำหรับวิดีโอโหมด: {mode_desc}
    ข้อมูลตั้งต้น: {context_info}
    จงคืนค่าเป็น JSON โดยมี Key ตามด้านล่าง และเลือก Value จากตัวเลือกที่มีให้:
    {json.dumps(options_dict, ensure_ascii=False, indent=2)}
    🚨 กฎ: ตอบกลับแค่โค้ด JSON เท่านั้น ห้ามมีข้อความอื่น ห้ามใส่ ```json"""
    raw_res = safe_generate(prompt)
    try:
        cleaned = re.sub(r'```json|```', '', raw_res).strip()
        data = json.loads(cleaned)
        for k, v in data.items(): st.session_state[k] = str(v)
        st.rerun()
    except Exception:
        st.error("⚠️ AI สุ่มการตั้งค่าไม่สำเร็จ กรุณาลองใหม่อีกครั้ง")

# ✨ ฟังก์ชันสร้างแคปชั่น 3 แพลตฟอร์ม (ใช้ได้ทุกโหมด)
def generate_captions(script_content):
    if not script_content.strip():
        st.warning("⚠️ กรุณาสร้าง 'สคริปต์วิดีโอ' ก่อนครับ AI จะได้ดึงเนื้อหามาเขียนแคปชั่นให้ตรงกัน")
        return
    with st.spinner("✍️ AI กำลังปั่นแคปชั่นป้ายยาสุดปังให้ 3 แพลตฟอร์ม..."):
        prompt = f"""จงเขียนแคปชั่นโซเชียลมีเดียจากเนื้อหาสคริปต์วิดีโอนี้:
        {script_content}
        
        ให้เขียนแยกเป็น 3 แพลตฟอร์มดังนี้:
        1. 🎵 TikTok: เน้นสั้น กระชับ ฮุกตั้งแต่ประโยคแรก ภาษาวัยรุ่น พร้อมแฮชแท็กฮิต 5-8 อัน
        2. 📘 Facebook: เน้นเล่าเรื่อง (Storytelling) ดูน่าเชื่อถือ อ่านเพลิน พร้อม Call-to-Action ชัดเจน
        3. 🛒 Shopee/Lazada (หรือ IG): เน้นโปรโมชั่น สเปคชัดเจน ปิดการขายไว กระตุ้นให้กดตะกร้าทันที"""
        res = safe_generate(prompt)
        st.success("✅ ได้แคปชั่นพร้อมโพสต์แล้วครับ!")
        st.code(res, language="markdown")

# ==========================================
# 🗂️ 2. เมนูนำทาง (Sidebar)
# ==========================================
if logo_img != "🤖": st.sidebar.image(logo_img, width=150)
st.sidebar.markdown("### 🗂️ เมนูหลัก (Main Menu)")
app_mode = st.sidebar.radio("เลือกโหมดการทำงาน:", [
    "🎬 โหมดโฆษณาสินค้า (Ad Director)", 
    "🐾 โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet)",
    "🎭 โหมดคาแรคเตอร์สายฮา (Comedy Meme)",
    "🎤 โหมดวิทยากร AI (AI Spokesperson)",
    "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger)",
    "🪩 โหมดดีเจและปาร์ตี้ (DJ & Party)",
    "🎵 โหมดมิวสิควิดีโอ (Music Video Studio)"
])
st.sidebar.markdown("---")
for i in range(len(api_keys_list)): st.sidebar.markdown(f"**คีย์ {i+1}:** {st.session_state.key_status.get(i, '⏳')}")
if st.sidebar.button("🔄 รีเซ็ตสถานะคีย์", use_container_width=True):
    st.session_state.current_key_idx = 0
    st.session_state.key_status = {i: "⏳ สแตนด์บาย" for i in range(len(api_keys_list))}
    st.rerun()

# =========================================================================================
# 🎬 1. โหมดโฆษณาสินค้า (Ad Director)
# =========================================================================================
if app_mode == "🎬 โหมดโฆษณาสินค้า (Ad Director)":
    st.markdown("<h1>😀 ระบบผู้กำกับโฆษณา AI (Pro Edition)</h1>", unsafe_allow_html=True)
    if 'ad_product_text' not in st.session_state: st.session_state.ad_product_text = ""
    if 'ad_actor_text' not in st.session_state: st.session_state.ad_actor_text = ""
    if 'ad_video_prompt' not in st.session_state: st.session_state.ad_video_prompt = ""

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        with st.expander("📦 1. อัปโหลดรูปสินค้า (Ingredient Lock)"):
            up_prod = st.file_uploader("ลากรูปสินค้ามาวาง", type=['png', 'jpg', 'jpeg'], key="ad_prod_up")
            if st.button("🔍 สกัดข้อมูลสินค้า") and up_prod:
                st.session_state.ad_product_text = safe_generate([Image.open(up_prod), "บรรยายรูปร่าง ลักษณะ สินค้าอย่างละเอียด"])
        st.session_state.ad_product_text = st.text_area("📝 ข้อมูลสินค้า:", value=st.session_state.ad_product_text, height=60)
    with col_up2:
        with st.expander("👤 2. อัปโหลดรูปพรีเซนเตอร์ (Character Lock)"):
            up_actor = st.file_uploader("ลากรูปหน้ามาวาง", type=['png', 'jpg', 'jpeg'], key="ad_actor_up")
            if st.button("🔍 สกัดหน้าตาพรีเซนเตอร์") and up_actor:
                st.session_state.ad_actor_text = safe_generate([Image.open(up_actor), "บรรยายใบหน้า ทรงผม เสื้อผ้า อย่างละเอียด"])
        st.session_state.ad_actor_text = st.text_area("📝 ข้อมูลพรีเซนเตอร์:", value=st.session_state.ad_actor_text, height=60)

    st.divider()
    st.markdown("### 🎬 3. ตั้งค่าการถ่ายทำ (14 Options)")
    
    if st.button("✨ ให้ AI ช่วยคิดการตั้งค่าทั้งหมด (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "ad_tone": ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "หรูหรา / พรีเมียม"],
            "ad_target": ["ทั่วไป (Mass)", "วัยรุ่น Gen Z", "วัยทำงาน / ผู้ใหญ่"],
            "ad_lang": ["ไทยภาคกลาง", "ภาษาใต้แท้", "ภาษาอีสาน", "ภาษาเหนือ", "อังกฤษ (English)"],
            "ad_dur": ["30 วินาที", "15 วินาที"],
            "ad_mood": ["สนุกสนานร่าเริง", "ลึกลับน่าค้นหา", "อบอุ่นละมุน"],
            "ad_style": ["UGC (รีวิวบ้านๆ)", "โทนภาพยนตร์ (Cinematic)", "โฆษณาทีวี (TV Commercial)"],
            "ad_story": ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "Storytelling (เล่าเรื่อง)"],
            "ad_cta": ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ", "กดลิงก์หน้าโปรไฟล์"],
            "ad_edit": ["ตัดสลับรวดเร็ว (Fast Cuts)", "สมูทนุ่มนวล (Smooth Transitions)"],
            "ad_light": ["สว่างสดใส", "ดาร์กโทน", "แสงนีออน (Neon)"],
            "ad_plat": ["TikTok / Shopee", "Facebook Reels", "YouTube"],
            "ad_vis": ["สมจริง (Photorealistic)", "การ์ตูน 3D (Pixar/Disney)"],
            "ad_cam": ["มาตรฐาน (Steady)", "ซูมเข้าช้าๆ", "ถือกล้องถ่ายเอง (Handheld)"],
            "ad_music": ["เพลงป๊อปสนุกสนาน", "ดนตรีตื่นเต้นเร้าใจ", "ล้ำสมัย (Electronic)"]
        }
        with st.spinner("🧠 AI กำลังคำนวณสูตรโฆษณาที่ปังที่สุด..."): magic_setup("โฆษณาสินค้า", opts, st.session_state.ad_product_text)

    c1, c2, c3 = st.columns(3)
    with c1: 
        render_custom_select("🗣️ 1. น้ำเสียง:", ["เพื่อนป้ายยา (เป็นกันเอง)", "ตื่นเต้น / ขายเก่ง", "หรูหรา / พรีเมียม"], "ad_tone")
        render_custom_select("🎯 2. กลุ่มเป้าหมาย:", ["ทั่วไป (Mass)", "วัยรุ่น Gen Z", "วัยทำงาน / ผู้ใหญ่"], "ad_target")
        render_custom_select("🌐 3. ภาษาคลิป:", ["ไทยภาคกลาง", "ภาษาใต้แท้", "ภาษาอีสาน", "ภาษาเหนือ", "อังกฤษ (English)"], "ad_lang")
        render_custom_select("⏳ 4. ความยาวคลิป:", ["30 วินาที", "15 วินาที"], "ad_dur")
        render_custom_select("🎭 5. อารมณ์คลิป:", ["สนุกสนานร่าเริง", "ลึกลับน่าค้นหา", "อบอุ่นละมุน"], "ad_mood")
    with c2: 
        render_custom_select("🎥 6. สไตล์วิดีโอ:", ["UGC (รีวิวบ้านๆ)", "โทนภาพยนตร์ (Cinematic)", "โฆษณาทีวี (TV Commercial)"], "ad_style")
        render_custom_select("📖 7. การเล่าเรื่อง:", ["PAS (ขยี้ปัญหาแล้วเสนอทางแก้)", "Storytelling (เล่าเรื่อง)"], "ad_story")
        render_custom_select("👉 8. ปิดการขาย:", ["กดตะกร้าสีเหลือง", "ทักแชทสั่งซื้อ", "กดลิงก์หน้าโปรไฟล์"], "ad_cta")
        render_custom_select("✂️ 9. จังหวะตัดต่อ:", ["ตัดสลับรวดเร็ว (Fast Cuts)", "สมูทนุ่มนวล (Smooth Transitions)"], "ad_edit")
        render_custom_select("💡 10. แสงและสี:", ["สว่างสดใส", "ดาร์กโทน", "แสงนีออน (Neon)"], "ad_light")
    with c3: 
        render_custom_select("📱 11. แพลตฟอร์ม:", ["TikTok / Shopee", "Facebook Reels", "YouTube"], "ad_plat")
        render_custom_select("🎨 12. สไตล์ภาพ:", ["สมจริง (Photorealistic)", "การ์ตูน 3D (Pixar/Disney)"], "ad_vis")
        render_custom_select("🎥 13. มุมกล้อง:", ["มาตรฐาน (Steady)", "ซูมเข้าช้าๆ", "ถือกล้องถ่ายเอง (Handheld)"], "ad_cam")
        render_custom_select("🎵 14. ดนตรีประกอบ:", ["เพลงป๊อปสนุกสนาน", "ดนตรีตื่นเต้นเร้าใจ", "ล้ำสมัย (Electronic)"], "ad_music")

    # ✨ ระบบ 3 แท็บ (วิดีโอ, โปสเตอร์, แคปชั่น)
    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 1. สร้างวิดีโอ", "🖼️ 2. สร้างโปสเตอร์", "✍️ 3. แคปชั่น 3 แพลตฟอร์ม"])
    with tab_vid:
        if st.button("🚀 สั่ง AI เขียนสคริปต์วิดีโอ", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์โฆษณา {st.session_state.get('ad_dur')} ลง {st.session_state.get('ad_plat')}. สินค้า: {st.session_state.ad_product_text} พรีเซนเตอร์: {st.session_state.ad_actor_text}. อารมณ์ {st.session_state.get('ad_mood')} เล่าเรื่อง {st.session_state.get('ad_story')} ภาษาพูด {st.session_state.get('ad_lang')}. สไตล์ภาพ {st.session_state.get('ad_vis')} กล้อง {st.session_state.get('ad_cam')} ดนตรี {st.session_state.get('ad_music')}. แยก Prompt นิ่ง/วิดีโอเป็นอังกฤษ ฝังเสียงพูด"
            st.session_state.ad_video_prompt = safe_generate(prompt)
        if st.session_state.ad_video_prompt: st.code(st.session_state.ad_video_prompt, language="markdown")
            
    with tab_poster:
        st.markdown("**🎨 ตั้งค่าหน้าปก / โปสเตอร์ (4 Options)**")
        col_p1, col_p2 = st.columns(2)
        with col_p1: 
            p_ratio = st.selectbox("📏 1. สัดส่วนภาพ:", ["9:16", "1:1", "16:9"], key="ad_pratio")
            p_color = st.selectbox("🌈 3. โทนสีหลัก:", ["สดใสจัดจ้าน", "พาสเทลละมุน", "ดาร์กโหมดพรีเมียม", "คลีนๆ ขาวดำ"], key="ad_pcolor")
        with col_p2: 
            p_style = st.selectbox("📄 2. สไตล์โปสเตอร์:", ["Hard Sale (โปรแรง)", "Soft Sell (ไลฟ์สไตล์)", "Minimal (มินิมอล)"], key="ad_pstyle")
            p_text = st.text_input("💬 4. ข้อความพาดหัว:", value="ลดราคาสุดพิเศษ!", key="ad_ptext")
            
        if st.button("🎨 สั่ง AI เขียน Prompt โปสเตอร์", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt ภาษาอังกฤษทำโปสเตอร์โฆษณา. สินค้า: {st.session_state.ad_product_text}. พรีเซนเตอร์: {st.session_state.ad_actor_text}. สไตล์: {p_style}. โทนสี: {p_color}. ข้อความ: '{p_text}'. สัดส่วน: {p_ratio}."
            st.code(safe_generate(prompt), language="markdown")
            
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นป้ายยา (3 แพลตฟอร์ม)", key="cap_btn_ad", type="primary", use_container_width=True):
            generate_captions(st.session_state.ad_video_prompt or st.session_state.ad_product_text)

# =========================================================================================
# 🐾 2. โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet)
# =========================================================================================
elif app_mode == "🐾 โหมดคลิปไวรัลสัตว์เลี้ยง (Viral Pet)":
    st.markdown("<h1>🐾 สตูดิโอปั้นสัตว์เลี้ยงไวรัล</h1>", unsafe_allow_html=True)
    if 'pet_context_text' not in st.session_state: st.session_state.pet_context_text = ""
    if 'pet_video_prompt' not in st.session_state: st.session_state.pet_video_prompt = ""

    with st.expander("📸 1. อัปโหลดรูปสัตว์เลี้ยง (Character Lock)"):
        up_pet = st.file_uploader("ลากรูปมาวาง", type=['png', 'jpg', 'jpeg'], key="pet_up")
        if st.button("🔍 สกัดคาแรคเตอร์") and up_pet:
            st.session_state.pet_context_text = safe_generate([Image.open(up_pet), "บรรยายลักษณะสัตว์เลี้ยง"])
    st.session_state.pet_context_text = st.text_area("📝 ข้อมูลสัตว์เลี้ยง:", value=st.session_state.pet_context_text, height=60)
    
    st.markdown("### 🎬 2. ตั้งค่าบทบาทให้แก๊งสี่ขา")
    if st.button("✨ ให้ AI สุ่มบทบาทสุดปั่นให้ (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "pet_costume": ["ชุด รปภ.", "เสื้อยืดสกรีนลายเท่ๆ", "ใส่ผ้ากันเปื้อน", "ไม่ใส่ชุด"],
            "pet_action": ["ยืนสองขาเต้นแดนซ์กระจาย", "ทำอาหาร/ตำส้มตำ", "นั่งทำงานหน้าคอม"],
            "pet_props": ["มะม่วงน้ำปลาหวาน", "โน้ตบุ๊ก", "ไม่มีพร็อพ"],
            "pet_setting": ["ในห้องน้ำสาธารณะ", "ห้องนั่งเล่น", "แคร่ไม้ไผ่กลางทุ่งนา"],
            "pet_dialogue": ["ลิปซิงค์ร้องเพลงฮิต", "บ่นเจ้านาย", "ไม่มีเสียงพูด"]
        }
        with st.spinner("🧠 AI กำลังสุ่มบทบาท..."): magic_setup("คลิปไวรัลสัตว์เลี้ยง", opts, st.session_state.pet_context_text)

    c1, c2, c3 = st.columns(3)
    with c1: 
        render_custom_select("👕 คอสตูม:", ["ชุด รปภ.", "เสื้อยืดสกรีนลายเท่ๆ", "ใส่ผ้ากันเปื้อน", "ไม่ใส่ชุด"], "pet_costume")
        render_custom_select("🎙️ เสียงพากย์:", ["ลิปซิงค์ร้องเพลงฮิต", "บ่นเจ้านาย", "ไม่มีเสียงพูด"], "pet_dialogue")
    with c2: 
        render_custom_select("🕺 แอคชั่น:", ["ยืนสองขาเต้นแดนซ์กระจาย", "ทำอาหาร/ตำส้มตำ", "นั่งทำงานหน้าคอม"], "pet_action")
        render_custom_select("🍔 พร็อพ:", ["ไม่มีพร็อพ", "มะม่วงน้ำปลาหวาน", "โน้ตบุ๊ก"], "pet_props")
    with c3: 
        render_custom_select("🏡 สถานที่:", ["ในห้องน้ำสาธารณะ", "ห้องนั่งเล่น", "แคร่ไม้ไผ่กลางทุ่งนา"], "pet_setting")
    
    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 1. สร้างวิดีโอ", "🖼️ 2. สร้างภาพปกคลิป", "✍️ 3. แคปชั่น 3 แพลตฟอร์ม"])
    with tab_vid:
        if st.button("🚀 สั่ง AI เขียนสคริปต์วิดีโอ", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์วิดีโอมีมสัตว์เลี้ยงพฤติกรรมเหมือนคน (Anthropomorphic). หน้าตา: {st.session_state.pet_context_text}. ชุด: {st.session_state.get('pet_costume')}. แอคชั่น: {st.session_state.get('pet_action')} กับพร็อพ {st.session_state.get('pet_props')}. สถานที่: {st.session_state.get('pet_setting')}. แยก Prompt ภาพนิ่ง/วิดีโอเป็นอังกฤษ ฝัง Audio cue"
            st.session_state.pet_video_prompt = safe_generate(prompt)
        if st.session_state.pet_video_prompt: st.code(st.session_state.pet_video_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพ:", ["9:16", "1:1", "16:9"], key="pet_pratio")
        with col_p2: p_text = st.text_input("💬 ข้อความฮุก:", value="สเต็ปเทพ!", key="pet_ptext")
        if st.button("🎨 สั่ง AI เขียน Prompt หน้าปก", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt อังกฤษทำปกคลิปสัตว์เลี้ยง: {st.session_state.pet_context_text} กำลัง {st.session_state.get('pet_action')}. มีข้อความ '{p_text}'. สัดส่วน {p_ratio}"
            st.code(safe_generate(prompt), language="markdown")
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นป้ายยา (3 แพลตฟอร์ม)", key="cap_btn_pet", type="primary", use_container_width=True):
            generate_captions(st.session_state.pet_video_prompt or st.session_state.pet_context_text)

# =========================================================================================
# 🎭 3. โหมดคาแรคเตอร์สายฮา (Comedy Meme)
# =========================================================================================
elif app_mode == "🎭 โหมดคาแรคเตอร์สายฮา (Comedy Meme)":
    st.markdown("<h1>🎭 สตูดิโอปั้นมีมไทบ้าน</h1>", unsafe_allow_html=True)
    if 'meme_video_prompt' not in st.session_state: st.session_state.meme_video_prompt = ""

    if st.button("✨ ให้ AI สุ่มคาแรคเตอร์ฮาๆ (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "meme_feature": ["ผมฟูชี้ฟู", "หน้าเหี่ยวย่นฟันหลอ", "มัดจุกบนหัว"],
            "meme_props": ["ขวดเหล้าขาว", "ไก่ชน", "สมาร์ทโฟน"],
            "meme_dialogue": ["คุยโวเรื่องถูกหวย", "ทวงหนี้เพื่อน", "นินทาเมีย"],
            "meme_setting": ["แคร่ไม้ไผ่หน้าเถียงนา", "วงเหล้าหน้าร้านชำ"]
        }
        magic_setup("มีมไทบ้านสายฮา", opts)

    c1, c2, c3 = st.columns(3)
    with c1: render_custom_select("🤪 ลักษณะเด่น:", ["ผมฟูชี้ฟู", "หน้าเหี่ยวย่นฟันหลอ", "มัดจุกบนหัว"], "meme_feature")
    with c2: render_custom_select("🍾 พร็อพ:", ["ขวดเหล้าขาว", "ไก่ชน", "สมาร์ทโฟน"], "meme_props")
    with c3: 
        render_custom_select("🏡 ฉากหลัง:", ["แคร่ไม้ไผ่หน้าเถียงนา", "วงเหล้าหน้าร้านชำ"], "meme_setting")
        render_custom_select("🎙️ บทพูด:", ["คุยโวเรื่องถูกหวย", "ทวงหนี้เพื่อน", "นินทาเมีย"], "meme_dialogue")
    
    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 1. สร้างคลิปมีม", "🖼️ 2. สร้างโปสเตอร์มีมตลก", "✍️ 3. แคปชั่น 3 แพลตฟอร์ม"])
    with tab_vid:
        if st.button("🚀 สั่ง AI เขียนสคริปต์คลิปมีม", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์คลิปล้อเลียน (Caricature). ลักษณะ: {st.session_state.get('meme_feature')} พร็อพ: {st.session_state.get('meme_props')} ฉาก: {st.session_state.get('meme_setting')}. แยก Prompt ภาพนิ่ง/วิดีโอเป็นอังกฤษ และฝัง Audio Cue สำหรับบทพูด: {st.session_state.get('meme_dialogue')}"
            st.session_state.meme_video_prompt = safe_generate(prompt)
        if st.session_state.meme_video_prompt: st.code(st.session_state.meme_video_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพ:", ["1:1", "9:16", "16:9"], key="meme_pratio")
        with col_p2: p_text = st.text_input("💬 คำคมสายเมา:", value="เงินไม่มี บารมีไม่เกิด", key="meme_ptext")
        if st.button("🎨 สั่ง AI เขียน Prompt มีมภาพนิ่ง", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt อังกฤษทำภาพมีม Caricature: {st.session_state.get('meme_feature')} ฉาก {st.session_state.get('meme_setting')}. มีข้อความ '{p_text}'. สัดส่วน {p_ratio}"
            st.code(safe_generate(prompt), language="markdown")
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นป้ายยา (3 แพลตฟอร์ม)", key="cap_btn_meme", type="primary", use_container_width=True):
            generate_captions(st.session_state.meme_video_prompt)

# =========================================================================================
# 🎤 4. โหมดวิทยากร AI (AI Spokesperson) 
# =========================================================================================
elif app_mode == "🎤 โหมดวิทยากร AI (AI Spokesperson)":
    st.markdown("<h1>🎤 สตูดิโอวิทยากร AI</h1>", unsafe_allow_html=True)
    if 'spoke_actor_text' not in st.session_state: st.session_state.spoke_actor_text = ""
    if 'spoke_raw_text' not in st.session_state: st.session_state.spoke_raw_text = ""
    if 'spoke_video_prompt' not in st.session_state: st.session_state.spoke_video_prompt = ""

    with st.expander("👤 1. อัปโหลดรูปตัวเอง (Character Lock)", expanded=True):
        up_spoke = st.file_uploader("ลากรูปมาวาง", type=['png', 'jpg', 'jpeg'], key="spoke_up")
        if st.button("🔍 สกัดหน้าตา") and up_spoke:
            st.session_state.spoke_actor_text = safe_generate([Image.open(up_spoke), "บรรยายใบหน้าและเสื้อผ้าให้ละเอียด"])
    
    st.markdown("### 📝 2. เตรียมบทพูด")
    topic = st.text_input("📌 หัวข้อให้ AI ช่วยเขียนสคริปต์:")
    if st.button("✨ ร่างบทพูด", type="secondary"): st.session_state.spoke_raw_text = safe_generate(f"เขียนบทพูดหน้ากล้อง: {topic}")
    st.session_state.spoke_raw_text = st.text_area("✍️ วางสคริปต์ที่จะให้พูด:", value=st.session_state.spoke_raw_text, height=100)
    
    st.markdown("### 🎬 3. เวทีและบรรยากาศ")
    if st.button("✨ ให้ AI จัดเวทีให้ (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "spoke_setting": ["สตูดิโอพอดแคสต์มีไมค์", "เวทีสัมมนาใหญ่"],
            "spoke_tone": ["สร้างแรงบันดาลใจ", "ให้ความรู้จริงจัง"]
        }
        magic_setup("คลิปวิทยากรให้ความรู้", opts, topic)

    c1, c2 = st.columns(2)
    with c1: render_custom_select("🏡 สถานที่:", ["สตูดิโอพอดแคสต์มีไมค์", "เวทีสัมมนาใหญ่"], "spoke_setting")
    with c2: render_custom_select("🗣️ อารมณ์:", ["สร้างแรงบันดาลใจ", "ให้ความรู้จริงจัง"], "spoke_tone")

    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 1. สร้างคลิปให้ความรู้", "🖼️ 2. สร้างหน้าปกคลิป", "✍️ 3. แคปชั่น 3 แพลตฟอร์ม"])
    with tab_vid:
        if st.button("🚀 สั่ง AI ปั้นสคริปต์วิทยากร", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt สร้างวิดีโอ. หน้าตา: {st.session_state.spoke_actor_text}. สถานที่: {st.session_state.get('spoke_setting')}. อารมณ์: {st.session_state.get('spoke_tone')}. บทพูด: '{st.session_state.spoke_raw_text}'. แยก Prompt ภาพนิ่ง/วิดีโอเป็นอังกฤษ ฝัง Audio cue"
            st.session_state.spoke_video_prompt = safe_generate(prompt)
        if st.session_state.spoke_video_prompt: st.code(st.session_state.spoke_video_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพ:", ["16:9", "1:1", "9:16"], key="spoke_pratio")
        with col_p2: p_text = st.text_input("💬 หัวข้อบนปก:", value="เคล็ดลับความสำเร็จ", key="spoke_ptext")
        if st.button("🎨 สั่ง AI เขียน Prompt หน้าปก", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt อังกฤษทำปกคลิป. วิทยากร: {st.session_state.spoke_actor_text} ฉาก {st.session_state.get('spoke_setting')}. มีอักษร '{p_text}'. สัดส่วน {p_ratio}"
            st.code(safe_generate(prompt), language="markdown")
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นป้ายยา (3 แพลตฟอร์ม)", key="cap_btn_spoke", type="primary", use_container_width=True):
            generate_captions(st.session_state.spoke_raw_text)

# =========================================================================================
# 🍰 5. โหมดรีวิวร้านตัวเอง (Local Vlogger) - แก้ไข Bug ขาวสะอาดตรงกันแล้ว! ✨
# =========================================================================================
elif app_mode == "🍰 โหมดรีวิวร้านตัวเอง (Local Vlogger)":
    st.markdown("<h1>🍰 สตูดิโอเจ้าของร้านรีวิวเอง</h1>", unsafe_allow_html=True)
    if 'vlog_product_text' not in st.session_state: st.session_state.vlog_product_text = ""
    if 'vlog_actor_text' not in st.session_state: st.session_state.vlog_actor_text = ""
    if 'vlog_video_prompt' not in st.session_state: st.session_state.vlog_video_prompt = ""

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        with st.expander("📸 อัปโหลดอาหาร (Ingredient Lock)"):
            up_vprod = st.file_uploader("ลากรูปอาหารมาวาง", type=['png', 'jpg', 'jpeg'], key="vlog_prod_up")
            if st.button("🔍 สกัดข้อมูลเมนู") and up_vprod:
                st.session_state.vlog_product_text = safe_generate([Image.open(up_vprod), "บรรยายความน่ากินอย่างละเอียด"])
        st.session_state.vlog_product_text = st.text_area("📝 ข้อมูลอาหาร:", value=st.session_state.vlog_product_text, height=60)
    with col_v2:
        with st.expander("👤 อัปโหลดตัวเอง (Character Lock)"):
            up_vactor = st.file_uploader("ลากรูปหน้าคุณมาวาง", type=['png', 'jpg', 'jpeg'], key="vlog_act_up")
            if st.button("🔍 สกัดหน้าตาตัวเอง") and up_vactor:
                st.session_state.vlog_actor_text = safe_generate([Image.open(up_vactor), "บรรยายหน้าตาเสื้อผ้า"])
        st.session_state.vlog_actor_text = st.text_area("📝 ข้อมูลผู้รีวิว:", value=st.session_state.vlog_actor_text, height=60)
    
    st.markdown("### 🎬 จัดฉากและบทพูด")
    if st.button("✨ ให้ AI เซ็ตอัปการรีวิว (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "vlog_setting": ["คาเฟ่มินิมอล", "หน้าร้านสตรีทฟู้ด", "ห้องครัว"],
            "vlog_dialect": ["ภาษาใต้", "ภาษาอีสาน", "ภาษาไทยกลาง", "ภาษาเหนือ"]
        }
        magic_setup("รีวิวร้านอาหาร", opts, st.session_state.vlog_product_text)

    c1, c2 = st.columns(2)
    with c1: render_custom_select("🏡 สถานที่:", ["คาเฟ่มินิมอล", "หน้าร้านสตรีทฟู้ด", "ห้องครัว"], "vlog_setting")
    with c2: render_custom_select("🗣️ ภาษาถิ่น:", ["ภาษาใต้", "ภาษาอีสาน", "ภาษาไทยกลาง", "ภาษาเหนือ"], "vlog_dialect")
    
    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 1. สร้างคลิปป้ายยา", "🖼️ 2. สร้างรูปโปรโมทร้าน", "✍️ 3. แคปชั่น 3 แพลตฟอร์ม"])
    with tab_vid:
        if st.button("🚀 สั่ง AI ปั้นสคริปต์รีวิวร้าน", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์รีวิว อาหาร: {st.session_state.vlog_product_text}. คนรีวิว: {st.session_state.vlog_actor_text}. สถานที่: {st.session_state.get('vlog_setting')}. ภาษา: {st.session_state.get('vlog_dialect')}. แยก Prompt ภาพนิ่ง/วิดีโออังกฤษ ฝัง Audio Cue ลิปซิงค์"
            st.session_state.vlog_video_prompt = safe_generate(prompt)
        if st.session_state.vlog_video_prompt: st.code(st.session_state.vlog_video_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนรูป:", ["4:3", "9:16", "1:1"], key="vlog_pratio")
        with col_p2: p_text = st.text_input("💬 ข้อความบนรูป:", value="อร่อยแสงออกปาก!", key="vlog_ptext")
        if st.button("🎨 สั่ง AI เขียน Prompt ทำแบนเนอร์", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt อังกฤษทำแบนเนอร์อาหาร: {st.session_state.vlog_product_text}. รีวิวโดย: {st.session_state.vlog_actor_text} บรรยากาศ {st.session_state.get('vlog_setting')}. มีอักษร '{p_text}'. สัดส่วน {p_ratio}"
            st.code(safe_generate(prompt), language="markdown")
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นป้ายยา (3 แพลตฟอร์ม)", key="cap_btn_vlog", type="primary", use_container_width=True):
            generate_captions(st.session_state.vlog_video_prompt or st.session_state.vlog_product_text)

# =========================================================================================
# 🪩 6. โหมดดีเจและปาร์ตี้ (DJ & Party) - แก้ไข Bug ขาวสะอาดตรงกันแล้ว! ✨
# =========================================================================================
elif app_mode == "🪩 โหมดดีเจและปาร์ตี้ (DJ & Party)":
    st.markdown("<h1>🪩 สตูดิโอปาร์ตี้ (DJ & Music Video)</h1>", unsafe_allow_html=True)
    if 'dj_actor_text' not in st.session_state: st.session_state.dj_actor_text = ""
    if 'dj_video_prompt' not in st.session_state: st.session_state.dj_video_prompt = ""

    with st.expander("👤 1. อัปโหลดรูปดีเจ (Character Lock)", expanded=True):
        up_dj = st.file_uploader("ลากรูปหน้าดีเจมาวาง", type=['png', 'jpg', 'jpeg'], key="dj_up")
        if st.button("🔍 สกัดหน้าตาศิลปิน") and up_dj:
            st.session_state.dj_actor_text = safe_generate([Image.open(up_dj), "บรรยายความเท่ ใบหน้า เสื้อผ้า"])
    st.session_state.dj_actor_text = st.text_area("📝 ข้อมูลลุคศิลปิน:", value=st.session_state.dj_actor_text, height=60)
    
    st.markdown("### 🎬 2. ตั้งค่าเวทีและแสงสี")
    if st.button("✨ ให้ AI จัดเวทีและแสงสี (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "dj_action": ["สแครชแผ่นและโยกหัวแรงๆ", "ชูมือขึ้นฟ้าบิ๊วคนดู", "จับไมค์ตะโกน"],
            "dj_light": ["ไฟเลเซอร์พุ่งตัดสลับ", "ไฟดิสโก้หลากสี", "แสงฟุ้งๆ ควันพุ่ง"],
            "dj_setting": ["ผับหรูไฟนีออน", "คอนเสิร์ต EDM กลางแจ้ง", "เวทีรถแห่สไตล์ไทบ้าน"]
        }
        magic_setup("วิดีโอปาร์ตี้ดีเจ", opts, st.session_state.dj_actor_text)

    c1, c2, c3 = st.columns(3)
    with c1: render_custom_select("🏙️ สถานที่:", ["ผับหรูไฟนีออน", "คอนเสิร์ต EDM กลางแจ้ง", "เวทีรถแห่สไตล์ไทบ้าน"], "dj_setting")
    with c2: render_custom_select("🕺 แอคชั่น:", ["สแครชแผ่นและโยกหัวแรงๆ", "ชูมือขึ้นฟ้าบิ๊วคนดู", "จับไมค์ตะโกน"], "dj_action")
    with c3: render_custom_select("💡 แสงสี:", ["ไฟเลเซอร์พุ่งตัดสลับ", "ไฟดิสโก้หลากสี", "แสงฟุ้งๆ ควันพุ่ง"], "dj_light")

    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 1. สร้างคลิปดีเจ", "🖼️ 2. สร้างโปสเตอร์ผับ/อีเวนต์", "✍️ 3. แคปชั่นโปรโมทร้าน"])
    with tab_vid:
        audio_choice = st.radio("เลือกวิธีใส่เพลง:", ["🔊 AI สร้างเพลงประกอบให้เลย (Native Audio)", "🔇 ไม่เอาเสียง (ไปใส่เพลงใน CapCut)"])
        if "🔊" in audio_choice: render_custom_select("🎵 แนวเพลง:", ["EDM สายตื๊ด", "สามช่า", "Hip-Hop"], "dj_genre")
        
        if st.button("🚀 สั่ง AI ปั้นสคริปต์ปาร์ตี้", type="primary", use_container_width=True):
            audio_inst = f"ใส่ Audio Cue: High-energy {st.session_state.get('dj_genre')}" if "🔊" in audio_choice else "ไม่ต้องใส่ Audio แต่เน้นขยับเร็ว (Fast-paced)"
            prompt = f"เขียน Prompt สร้างวิดีโอ. ศิลปิน: {st.session_state.dj_actor_text}. แสงสี: {st.session_state.get('dj_light')}. แอคชั่น: {st.session_state.get('dj_action')}. ฉาก: {st.session_state.get('dj_setting')}. แยก Prompt ภาพนิ่ง/วิดีโออังกฤษ. {audio_inst}"
            st.session_state.dj_video_prompt = safe_generate(prompt)
        if st.session_state.dj_video_prompt: st.code(st.session_state.dj_video_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพ:", ["4:3", "9:16", "1:1"], key="dj_pratio")
        with col_p2: p_text = st.text_input("💬 พาดหัวโปสเตอร์:", value="GRAND OPENING PARTY", key="dj_ptext")
        if st.button("🎨 สั่ง AI เขียน Prompt Flyer", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt อังกฤษทำ Party Flyer. ศิลปิน: {st.session_state.dj_actor_text} ฉาก {st.session_state.get('dj_setting')} แสง {st.session_state.get('dj_light')}. มีอักษร Neon คำว่า '{p_text}'. สัดส่วน {p_ratio}"
            st.code(safe_generate(prompt), language="markdown")
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นโปรโมทร้าน (3 แพลตฟอร์ม)", key="cap_btn_dj", type="primary", use_container_width=True):
            generate_captions(st.session_state.dj_video_prompt or "โปรโมทปาร์ตี้ดีเจสุดมันส์ คืนนี้เจอกัน")

# =========================================================================================
# 🎵 7. โหมดมิวสิควิดีโอ (Music Video Studio)
# =========================================================================================
elif app_mode == "🎵 โหมดมิวสิควิดีโอ (Music Video Studio)":
    st.markdown("<h1>🎵 สตูดิโอสร้างเพลงและ MV</h1>", unsafe_allow_html=True)
    if 'mv_lyrics_text' not in st.session_state: st.session_state.mv_lyrics_text = ""
    if 'mv_full_prompt' not in st.session_state: st.session_state.mv_full_prompt = ""
    mv_topic = st.text_input("📌 หัวข้อเพลง/เรื่องราว:", placeholder="เช่น ความรักในเมืองใหญ่...")

    if st.button("✨ ให้ AI คิดแนวเพลงและภาพให้ทั้งหมด (Magic Setup)", type="secondary", use_container_width=True):
        opts = {
            "mv_genre": ["Pop ไทยร่วมสมัย", "ลูกทุ่งอินดี้ร่วมสมัย", "Rock หนักแน่น", "EDM / Dance"],
            "mv_lang": ["ไทยกลาง", "อีสาน", "ใต้", "อังกฤษ"],
            "mv_vocal": ["เสียงผู้ชาย", "เสียงผู้หญิง", "ดูโอ้"],
            "mv_tempo": ["ปานกลาง", "ช้าซึ้ง", "เร็วสนุกสนาน"],
            "mv_inst": ["กีตาร์โปร่ง", "เปียโน", "ซินธิไซเซอร์", "พิณ/แคน"],
            "mv_style": ["ภาพยนตร์ดราม่า", "อนิเมะสวยงาม", "ย้อนยุค", "Cyberpunk"],
            "mv_cam": ["สโลว์โมชั่นนิ่งๆ", "ตัดสลับรวดเร็ว", "โดรนมุมสูง"],
            "mv_light": ["สีทองอบอุ่น", "แสงสีนีออน", "ขาวดำหรูหรา"]
        }
        with st.spinner("🧠 AI กำลังคำนวณแนวเพลงและภาพที่เหมาะสมที่สุด..."): magic_setup("MV เพลงฮิต", opts, mv_topic)

    st.markdown("### 🎼 ตั้งค่าดนตรีและภาพ")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_custom_select("🎸 แนวเพลง:", ["Pop ไทยร่วมสมัย", "ลูกทุ่งอินดี้ร่วมสมัย", "Rock หนักแน่น", "EDM / Dance"], "mv_genre")
        render_custom_select("🥁 จังหวะ:", ["ปานกลาง", "ช้าซึ้ง", "เร็วสนุกสนาน"], "mv_tempo")
        render_custom_select("🎨 สไตล์ภาพ MV:", ["ภาพยนตร์ดราม่า", "อนิเมะสวยงาม", "ย้อนยุค", "Cyberpunk"], "mv_style")
    with c2:
        render_custom_select("🗣️ ภาษา:", ["ไทยกลาง", "อีสาน", "ใต้", "อังกฤษ"], "mv_lang")
        render_custom_select("🎹 เครื่องดนตรี:", ["กีตาร์โปร่ง", "เปียโน", "ซินธิไซเซอร์", "พิณ/แคน"], "mv_inst")
        render_custom_select("🎥 มุมกล้อง:", ["สโลว์โมชั่นนิ่งๆ", "ตัดสลับรวดเร็ว", "โดรนมุมสูง"], "mv_cam")
    with c3:
        render_custom_select("🎙️ นักร้อง:", ["เสียงผู้ชาย", "เสียงผู้หญิง", "ดูโอ้"], "mv_vocal")
        render_custom_select("💡 โทนแสง:", ["สีทองอบอุ่น", "แสงสีนีออน", "ขาวดำหรูหรา"], "mv_light")

    if st.button("✨ 1. สั่งแต่งเนื้อเพลง", type="secondary", use_container_width=True):
        st.session_state.mv_lyrics_text = safe_generate(f"แต่งเนื้อเพลง หัวข้อ: {mv_topic} แนว: {st.session_state.get('mv_genre')} ภาษา: {st.session_state.get('mv_lang')} เสียงร้อง: {st.session_state.get('mv_vocal')}")
    st.session_state.mv_lyrics_text = st.text_area("📝 เนื้อเพลง:", value=st.session_state.mv_lyrics_text, height=120)

    tab_vid, tab_poster, tab_cap = st.tabs(["🎬 2. สร้างมิวสิควิดีโอ", "🖼️ 3. สร้างหน้าปกซิงเกิล", "✍️ 4. แคปชั่นโปรโมทเพลง"])
    with tab_vid:
        if st.button("🚀 สั่ง AI เขียนสคริปต์ MV และเสียง", type="primary", use_container_width=True):
            prompt = f"เขียนสคริปต์แยก 2 ส่วน: 1. Audio (สไตล์ {st.session_state.get('mv_genre')}, ดนตรี {st.session_state.get('mv_inst')}, จังหวะ {st.session_state.get('mv_tempo')}) เนื้อเพลง: {st.session_state.mv_lyrics_text}. 2. Video (ภาพสไตล์ {st.session_state.get('mv_style')}, กล้อง {st.session_state.get('mv_cam')}, แสง {st.session_state.get('mv_light')}). ให้เป็นภาษาอังกฤษล้วน"
            st.session_state.mv_full_prompt = safe_generate(prompt)
        if st.session_state.mv_full_prompt: st.code(st.session_state.mv_full_prompt, language="markdown")
    with tab_poster:
        col_p1, col_p2 = st.columns(2)
        with col_p1: p_ratio = st.selectbox("📏 สัดส่วนภาพ:", ["1:1 (ปก Album/Spotify)", "16:9", "9:16"], key="mv_pratio")
        with col_p2: p_text = st.text_input("💬 ชื่อเพลงบนปก:", value="New Single", key="mv_ptext")
        if st.button("🎨 สั่ง AI เขียน Prompt หน้าปก", type="primary", use_container_width=True):
            prompt = f"เขียน Prompt ภาษาอังกฤษทำภาพปกอัลบั้ม. สไตล์: {st.session_state.get('mv_style')}. เรื่องราว {mv_topic}. มีตัวอักษรสวยงามเขียนว่า '{p_text}'. สัดส่วน {p_ratio}"
            st.code(safe_generate(prompt), language="markdown")
    with tab_cap:
        if st.button("✍️ สั่ง AI คิดแคปชั่นโปรโมทเพลง (3 แพลตฟอร์ม)", key="cap_btn_mv", type="primary", use_container_width=True):
            generate_captions(st.session_state.mv_lyrics_text or mv_topic)