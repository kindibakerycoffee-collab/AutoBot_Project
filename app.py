import streamlit as st
from google import genai
from PIL import Image

# ==========================================
# ⚙️ ส่วนที่ 1: ตั้งค่า API (เวอร์ชันขึ้น Cloud ปลอดภัย 100%)
# ==========================================
# ระบบจะพยายามดึงคีย์จากความลับบน Cloud ก่อน ถ้าไม่เจอจะใช้คีย์ในคอมคุณ
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "ใส่_API_KEY_ของคุณที่นี่_เพื่อรันในคอม" # <--- ใส่คีย์คุณไว้ตรงนี้เหมือนเดิมครับ

client = genai.Client(api_key=API_KEY)

st.set_page_config(page_title="AutoBot_Project", layout="wide")
# ... (โค้ดส่วนอื่นๆ ด้านล่างปล่อยไว้เหมือนเดิมเป๊ะๆ เลยครับ) ...

# สร้างตัวแปรความจำ
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "video_result" not in st.session_state:
    st.session_state.video_result = ""
if "poster_result" not in st.session_state:
    st.session_state.poster_result = ""

# ==========================================
# 🖼️ ส่วนที่ 2: อัปโหลดรูปภาพ และ ดึงข้อความ (OCR)
# ==========================================
st.title("🤖 ระบบผู้กำกับโฆษณา AI (AutoBot_Project)")
st.markdown("1. อัปโหลดรูป -> 2. ดึงข้อความ -> 3. เลือกแท็บ (วิดีโอ/โปสเตอร์) -> 4. กดเจน Prompt")

uploaded_files = st.file_uploader("➕ อัปโหลดรูปภาพอ้างอิง (สินค้า, พรีเซนเตอร์)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

image_names = []
image_parts = [] 

if uploaded_files:
    st.markdown("**รูปภาพที่อัปโหลด:**")
    cols = st.columns(min(len(uploaded_files), 5))
    for idx, file in enumerate(uploaded_files):
        with cols[idx % 5]:
            img = Image.open(file)
            image_parts.append(img)
            st.image(img, width=100)
            st.caption(file.name)
            image_names.append(file.name)

if st.button("🔍 ดึงข้อความและจุดขายจากรูปภาพ"):
    if not uploaded_files:
        st.warning("กรุณาอัปโหลดรูปภาพก่อนครับ")
    else:
        with st.spinner("กำลังให้ AI สแกนข้อความและจุดขายจากรูปภาพ..."):
            try:
                prompt_ocr = "กรุณาดึงข้อความทั้งหมดที่อ่านได้จากรูปภาพเหล่านี้ และสรุปจุดขายหลักของสินค้ามาให้เป็นข้อๆ สั้นๆ"
                response_ocr = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[prompt_ocr] + image_parts
                )
                st.session_state.extracted_text = response_ocr.text
                st.success("ดึงข้อความสำเร็จ! ดูและแก้ไขข้อความด้านล่างได้เลยครับ")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการดึงข้อความ: {e}")

st.divider()

st.markdown("### 📝 รายละเอียดสินค้าสำหรับแต่งสคริปต์")
product_info = st.text_area(
    "ข้อความที่สแกนได้ (สามารถพิมพ์แก้ไข เพิ่มราคา หรือโปรโมชันเองได้เลย):", 
    key="extracted_text", 
    height=150
)

# ==========================================
# 📚 ส่วนที่ 3: ข้อมูลคำแนะนำ (Dictionaries)
# ==========================================
gender_desc = {"ชาย (Male)": "💡 เหมาะกับแมนๆ กีฬา ไอที", "หญิง (Female)": "💡 เหมาะกับบิวตี้ แฟชั่น", "ไม่ระบุเพศ / LGBTQ+": "💡 เข้าถึงคนรุ่นใหม่", "มาสคอตสัตว์น่ารัก (Mascot)": "💡 เป็นมิตรกับทุกวัย"}
video_style_desc = {"UGC (รีวิวบ้านๆ จริงใจ)": "💡 รู้สึกเหมือนเพื่อนมาป้ายยา", "TikTok Live (ขายของดุดัน)": "💡 กระตุ้นยอดขายไว", "Cinematic (พรีเมียม)": "💡 ภาพสวยระดับหนัง", "Unboxing / ASMR": "💡 เน้นเสียงสัมผัส", "Vlog Style (ตามติดชีวิต)": "💡 เนียนไทอินสินค้า", "ละครสั้น / ล้อเลียน": "💡 สร้างดราม่าตลก ไวรัล", "ตลกขบขัน": "💡 คลายเครียด แชร์ต่อ"}
visual_style_desc = {"สมจริง (Photorealistic)": "💡 สกินแคร์, อาหาร (น่าเชื่อถือ)", "การ์ตูน 3D (Pixar Style)": "💡 สินค้าเด็ก, ขนม (น่ารัก)", "อนิเมะญี่ปุ่น (Anime)": "💡 แฟชั่นวัยรุ่น, เกม", "ภาพวาดมินิมอล (Minimalist)": "💡 ออร์แกนิก (คลีนๆ)", "ภาพถ่ายฟิล์มวินเทจ": "💡 สินค้าสายอีโมชัน", "ไซไฟล้ำยุค (Cyberpunk)": "💡 อุปกรณ์ไอที เกมมิ่ง"}
voice_style_desc = {"เพื่อนป้ายยา (เป็นกันเอง)": "💡 จริงใจ เข้าถึงง่าย", "ตื่นเต้น / ขายเก่ง": "💡 ดึงพลังงานคนดู", "ผู้เชี่ยวชาญ / น่าเชื่อถือ": "💡 ให้ข้อมูลแน่นๆ", "หรูหรา / พรีเมียม": "💡 พูดช้า นุ่มลึก", "กวนๆ / ขี้เล่น": "💡 สายฮา ทะ้น"}
story_style_desc = {"PAS (ขยี้ปัญหาแล้วเสนอทางแก้)": "💡 เหมาะกับสินค้าแก้ปัญหา", "FOMO (กระตุ้นความกลัวพลาดโปร)": "💡 กระตุ้นความอยากได้", "Educational (สอนใช้งาน)": "💡 เหมาะกับนวัตกรรมใหม่", "Testimonial (อ้างอิงคนใช้จริง)": "💡 ต้องการความน่าเชื่อถือ"}
target_audience_desc = {"ทั่วไป (Mass)": "💡 เข้าถึงคนทุกกลุ่ม", "วัยรุ่น Gen Z / นักศึกษา": "💡 ทันกระแส ศัพท์ฮิต", "พนักงานออฟฟิศ": "💡 เน้นสะดวก แก้ปัญหา", "แม่บ้าน / พ่อบ้าน": "💡 เน้นคุ้มค่า", "สายลุย / ออกกำลังกาย": "💡 พลังงานล้น ทนทาน", "ผู้สูงอายุ": "💡 อธิบายช้าๆ เน้นสุขภาพ"}
cta_action_desc = {"กดตะกร้าสีเหลือง": "💡 ปิดยอดไว", "ทักแชท / Inbox": "💡 เน้นให้ลูกค้าสอบถาม", "คลิกลิงก์หน้าโปรไฟล์": "💡 พาคนไปหน้าเว็บ", "เก็บโค้ดส่วนลดด่วน": "💡 เร่งตัดสินใจ"}
language_dialect_desc = {"ไทยมาตรฐาน": "💡 เป็นทางการ", "ภาษาใต้": "💡 ดุดัน จริงใจ", "ภาษาอีสาน": "💡 ม่วนซื่น เป็นกันเอง", "ภาษาเหนือ": "💡 อ่อนหวาน นุ่มนวล", "ศัพท์วัยรุ่น T-Pop": "💡 จริตตัวมัม"}

poster_style_desc = {
    "Hard Sale / โปรแรง (ตะโกนขาย)": "💡 ตัวหนังสือใหญ่ เน้นราคา (Shopee/Lazada/TikTok)",
    "Soft Sell / อารมณ์ไลฟ์สไตล์": "💡 ภาพสวยบรรยากาศดี ไม่ยัดเยียดขาย",
    "Minimalist / มินิมอล (คลีนๆ)": "💡 พื้นที่ว่างเยอะ ดูแพง เรียบหรู",
    "Infographic / อธิบายจุดขาย": "💡 เน้นชี้แจงสเปคเป็นข้อๆ (แกดเจ็ตไอที)",
    "Magazine Cover / ปกนิตยสาร": "💡 ฟอนต์พาดหัวหรูหรา ดูพรีเมียม",
    "Pop-Art / Y2K (กราฟิกสีจัดจ้าน)": "💡 สีสันสะดุดตา สนุกสนาน เทรนดี้",
    "Meme / มีมไวรัล (ตลกขบขัน)": "💡 เลย์เอาต์กวนๆ เน้นยอดแชร์"
}

# กำหนดสัดส่วน 5 ขนาดมาตรฐาน (ใช้ร่วมกันทั้งวิดีโอและโปสเตอร์)
ratio_options = [
    "แนวนอน 16:9 (YouTube / TV)", 
    "แนวนอน 4:3 (Standard Photo)", 
    "จัตุรัส 1:1 (FB / IG Post)", 
    "แนวตั้ง 3:4 (Portrait)", 
    "แนวตั้ง 9:16 (Story / Reels / TikTok)"
]

st.divider()

# ==========================================
# 🎛️ ส่วนที่ 4: ระบบ Tabs (วิดีโอ & โปสเตอร์)
# ==========================================
st.markdown("### 🎛️ เลือกโหมดการทำงานหลัก")
tab1, tab2 = st.tabs(["🎬 โหมดสร้างคลิปวิดีโอ", "🖼️ โหมดสร้างโปสเตอร์โฆษณา"])

# ------------------------------------------
# TAB 1: โหมดวิดีโอ
# ------------------------------------------
with tab1:
    st.markdown("#### 🎬 แผงควบคุมวิดีโอ (Video Settings)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        gender_voice = st.selectbox("👤 ผู้พูด/พรีเซนเตอร์:", list(gender_desc.keys()), key="v_gender")
        st.caption(gender_desc[gender_voice])
    with col2:
        review_style = st.selectbox("🎥 สไตล์วิดีโอ:", list(video_style_desc.keys()), key="v_style")
        st.caption(video_style_desc[review_style])
    with col3:
        visual_style = st.selectbox("🎨 สไตล์ภาพ (Visual):", list(visual_style_desc.keys()), key="v_visual")
        st.caption(visual_style_desc[visual_style])

    col4, col5, col6 = st.columns(3)
    with col4:
        voice_style = st.selectbox("🗣️ น้ำเสียง:", list(voice_style_desc.keys()), key="v_voice")
        st.caption(voice_style_desc[voice_style])
    with col5:
        story_style = st.selectbox("📖 การเล่าเรื่อง:", list(story_style_desc.keys()), key="v_story")
        st.caption(story_style_desc[story_style])
    with col6:
        target_audience = st.selectbox("🎯 กลุ่มเป้าหมาย:", list(target_audience_desc.keys()), key="v_target")
        st.caption(target_audience_desc[target_audience])

    col7, col8, col9 = st.columns(3)
    with col7:
        platform_ratio = st.selectbox("📱 สัดส่วนวิดีโอ:", ratio_options, key="v_ratio")
        st.caption("💡 เลือกสัดส่วนให้ตรงกับแพลตฟอร์ม")
    with col8:
        cta_action = st.selectbox("🛒 ปิดการขาย:", list(cta_action_desc.keys()), key="v_cta")
        st.caption(cta_action_desc[cta_action])
    with col9:
        language_dialect = st.selectbox("💬 ภาษาพูด:", list(language_dialect_desc.keys()), key="v_lang")
        st.caption(language_dialect_desc[language_dialect])

    st.write("") 
    col10, col11 = st.columns([2, 1])
    with col10:
        on_screen_text = st.selectbox(
            "🔠 ข้อความโชว์บนวิดีโอ (แก้ปัญหาฟอนต์ต่างด้าว):", 
            [
                "ไม่ใส่ข้อความ (คลีนๆ เน้นภาพและเสียง ค่อยไปเติมซับเอง)", 
                "ข้อความภาษาอังกฤษ (ปลอดภัยสุด AI เจนตัวหนังสือไม่เพี้ยน)", 
                "ข้อความภาษาไทย (คำเตือน: AI อาจเจนฟอนต์เพี้ยนเป็นต่างด้าว)", 
                "ข้อความภาษาไทย + อังกฤษ"
            ], key="v_text"
        )
    with col11:
        video_duration = st.selectbox(
            "⏱️ ความยาวคลิปรวม:", 
            ["สั้นกระชับฮุกคนดู (15 วินาที)", "มาตรฐานกำลังดี (30 วินาที)", "รีวิวจัดเต็ม (1 นาที)"], 
            key="v_duration"
        )

    submit_video = st.button("🚀 เจน Prompt วิดีโอ", use_container_width=True, type="primary", key="btn_video")

    if submit_video:
        if not product_info:
            st.warning("กรุณากรอกรายละเอียดสินค้า หรือกดดึงข้อความจากรูปก่อนครับ")
        else:
            with st.spinner("กำลังประมวลผลสคริปต์วิดีโอ..."):
                file_list_str = ", ".join(image_names) if image_names else "ไม่มีรูปภาพแนบ"
                
                cross_reference = ""
                if st.session_state.poster_result:
                    cross_reference = f"\n\n[ข้อบังคับแคมเปญ]: ก่อนหน้านี้มีการออกแบบโปสเตอร์โฆษณาไว้แล้ว จงแต่งสคริปต์วิดีโอให้เนื้อหาและโปรโมชัน 'สอดคล้องเป็นแคมเปญเดียวกัน' กับโปสเตอร์นี้:\n{st.session_state.poster_result}"

                text_instruction = ""
                if "ไม่ใส่ข้อความ" in on_screen_text:
                    text_instruction = "**ข้อความบนจอ:** ห้ามใส่ข้อความใดๆ บนจอเด็ดขาด (ระบุว่า Text on screen: None)"
                elif "ภาษาอังกฤษ" in on_screen_text:
                    text_instruction = "**ข้อความบนจอ:** ต้องเป็น 'ภาษาอังกฤษสั้นๆ' เท่านั้น เพื่อป้องกัน AI เจนฟอนต์เพี้ยน"
                else:
                    text_instruction = "**ข้อความบนจอ:** ให้มีข้อความดึงจุดขายเด่นๆ มาโชว์"

                system_prompt_video = f"""
                คุณคือ Creative Director มือฉมัง ที่เชี่ยวชาญการทำ AI Video Generation
                [ข้อมูลสินค้า]: {product_info}
                [รูปภาพอ้างอิง]: {file_list_str} (อ้างอิงเพื่อเขียน Image Prompt โดยใส่วงเล็บ "(from ชื่อไฟล์)" ไว้ท้ายวัตถุเสมอ)
                [ทิศทางวิดีโอ]: สไตล์ภาพ {visual_style}, พรีเซนเตอร์ {gender_voice}, เป้าหมาย {target_audience}, เล่าเรื่อง {story_style}, นำเสนอ {review_style}, น้ำเสียง {voice_style}, ภาษาพูด {language_dialect}, สัดส่วน {platform_ratio}, CTA {cta_action}, ความยาวคลิปรวม {video_duration}
                
                คำสั่งสำคัญ (Strict Rules):
                1. เสียงพากย์ (Voiceover): ระบุเพศพรีเซนเตอร์ ({gender_voice}) กำกับไว้หน้าบทพูด "ทุกฉาก" ห้ามให้ AI สลับเสียง
                2. {text_instruction}
                3. [กฎเหล็กเรื่องเวลา]: AI Video 1 ฉากมีความยาวสูงสุดแค่ "4-5 วินาที" 
                   -> บทพูด 1 ฉาก ห้ามยาวเกิน 1-2 ประโยคสั้นๆ (ประมาณ 10-20 คำ) ให้แตกฉากใหม่เสมอถ้าข้อมูลยาว
                   -> ให้ AI กำหนดจำนวนฉากเอง ให้สอดคล้องกับความยาวรวม {video_duration}
                4. [กฎความต่อเนื่อง (Seamless Flow)]: บทพูดระหว่างฉากต้องเชื่อมโยงและไหลลื่นต่อเนื่องกัน (ใช้เทคนิค J-Cut/L-Cut หรือคำเชื่อม เช่น แถม, และที่สำคัญ) ห้ามดูห้วน
                {cross_reference}

                คำสั่ง: จงเขียน Prompt วิดีโอ ตามโครงสร้างนี้:
                ฉากที่ [ลำดับฉาก]
                -บทพูด: [({gender_voice}) + บทพูดสั้นๆ ต่อเนื่องกัน]
                -การสร้างรูปภาพแต่ละคลิป: [Image Prompt ภาษาอังกฤษ ระบุสไตล์ {visual_style}, เพศ, มุมกล้อง, สัดส่วน {platform_ratio} และชื่อไฟล์อ้างอิง]
                -การเคลื่อนไหว ซาวประกอบ เอฟเฟกต์: [Motion Prompt ภาษาอังกฤษ, SFX, Text on screen: (ตามกฎอย่างเคร่งครัด)]
                (รันลำดับฉากไปเรื่อยๆ ตามความยาวคลิป)
                
                สรุปให้เขียน พรอม อย่างเดียว ห้ามพิมพ์คำอธิบาย
                """
                try:
                    # ตัวแปร system_prompt_video ถูกส่งเป็น list เข้าไปกับภาพ
                    request_data = [system_prompt_video] + image_parts
                    response_video = client.models.generate_content(model='gemini-2.5-flash', contents=request_data)
                    st.session_state.video_result = response_video.text 
                    st.success("สร้าง Prompt วิดีโอสำเร็จ!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    if st.session_state.video_result:
        st.text_area("ผลลัพธ์วิดีโอ (คัดลอกไปใช้งานต่อได้เลย):", st.session_state.video_result, height=500, key="video_output")

# ------------------------------------------
# TAB 2: โหมดโปสเตอร์
# ------------------------------------------
with tab2:
    st.markdown("#### 🖼️ แผงควบคุมโปสเตอร์ (Poster Settings)")
    col12, col13 = st.columns(2)
    with col12:
        poster_style = st.selectbox("📐 สไตล์โปสเตอร์โฆษณา:", list(poster_style_desc.keys()), key="p_style")
        st.caption(poster_style_desc[poster_style])
    with col13:
        poster_ratio = st.selectbox("📱 สัดส่วนภาพโปสเตอร์:", ratio_options, key="p_ratio")
        st.caption("💡 เลือกสัดส่วนให้ตรงกับตำแหน่งที่จะยิงแอด")

    poster_tone = st.selectbox("🎨 โทนสีหลักของโปสเตอร์:", ["สีแบรนด์ตามรูปสินค้า (อิงจากภาพอ้างอิง)", "สีแดง/เหลือง/ส้ม (ร้อนแรง กระตุ้น)", "สีพาสเทล (น่ารัก ละมุน)", "สีขาวดำ/เทา (หรูหรา มินิมอล)", "สีนีออนสะท้อนแสง (โดดเด่น ไซไฟ)"], key="p_tone")

    submit_poster = st.button("🚀 เจน Prompt โปสเตอร์", use_container_width=True, type="primary", key="btn_poster")

    if submit_poster:
        if not product_info:
            st.warning("กรุณากรอกรายละเอียดสินค้า หรือกดดึงข้อความจากรูปก่อนครับ")
        else:
            with st.spinner("กำลังประมวลผลกราฟิกโปสเตอร์..."):
                file_list_str = ", ".join(image_names) if image_names else "ไม่มีรูปภาพแนบ"
                
                cross_reference = ""
                if st.session_state.video_result:
                    cross_reference = f"\n\n[ข้อบังคับแคมเปญ]: ก่อนหน้านี้มีการแต่งสคริปต์วิดีโอไว้แล้ว จงคิดคำพาดหัว (Headline) ให้ 'สอดคล้องเป็นแคมเปญเดียวกัน' กับวิดีโอคลิปนี้ ห้ามคิดโปรโมชันฉีกออกไป:\n{st.session_state.video_result}"

                system_prompt_poster = f"""
                คุณคือ Graphic Designer มือฉมัง ที่เชี่ยวชาญการทำโฆษณาและ AI Image Generation
                [ข้อมูลสินค้า จุดขาย โปรโมชัน]: {product_info}
                [รูปภาพอ้างอิง]: {file_list_str} (อ้างอิงเพื่อเขียน Image Prompt โดยใส่วงเล็บ "(from ชื่อไฟล์)" ไว้ท้ายวัตถุเสมอ)
                [ทิศทางโปสเตอร์]: เลย์เอาต์ {poster_style}, สัดส่วน {poster_ratio}, โทนสี {poster_tone}
                {cross_reference}

                คำสั่ง: จงเขียน Prompt โปสเตอร์ ตามโครงสร้างนี้:
                -พรอมสร้างภาพพื้นหลังโปสเตอร์: [Image Prompt ภาษาอังกฤษ (Background) ระบุเลย์เอาต์ "{poster_style}" สัดส่วน {poster_ratio} และโทนสี "{poster_tone}"]
                -ข้อความพาดหัวหลัก (Headline): [คิดพาดหัวตัวใหญ่ ดึงดูดสายตา สอดคล้องกับสไตล์]
                -ข้อความโปรโมชัน/รอง (Sub-headline): [ข้อความสนับสนุน หรือจุดขายเด่นๆ]
                -คำแนะนำการจัดวางกราฟิก (Layout Guide): [อธิบายวิธีวางตัวหนังสือทับลงบนภาพพื้นหลังให้สวยงามระดับมืออาชีพ]
                
                สรุปให้เขียน พรอม อย่างเดียว ห้ามพิมพ์คำอธิบาย
                """
                try:
                    request_data = [system_prompt_poster] + image_parts
                    response_poster = client.models.generate_content(model='gemini-2.5-flash', contents=request_data)
                    st.session_state.poster_result = response_poster.text 
                    st.success("สร้าง Prompt โปสเตอร์สำเร็จ!")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    if st.session_state.poster_result:
        st.text_area("ผลลัพธ์โปสเตอร์ (คัดลอกไปใช้งานต่อได้เลย):", st.session_state.poster_result, height=350, key="poster_output")