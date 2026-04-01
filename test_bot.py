import os
import json
import time
import socket
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def is_chrome_ready():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', 9222)) == 0

print("🤖 กำลังปลุก AutoBot หลังบ้าน (Selenium Ultimate Flow + Smart Wait)...")

task_file = "bot_task.json"
if not os.path.exists(task_file):
    print("📭 ไม่พบคำสั่งใหม่ในระบบ!")
    exit(1)

with open(task_file, "r", encoding="utf-8") as f:
    task_data = json.load(f)

job_type = task_data.get("type", "unknown")
job_prompt = task_data.get("prompt", "") 
job_credit = task_data.get("credit_mode", "Lower Priority")
job_ref_image = task_data.get("ref_image", "") 
job_scene_num = task_data.get("scene_num", 1)
job_is_first = task_data.get("is_first_scene", True)

# =======================================================
# 🛡️ ฟังก์ชันใหม่: เครื่องกรอง Emoji และอักขระพิเศษ
# =======================================================
def clean_text_for_selenium(text):
    """ลบ Emoji และตัวอักษรที่อยู่นอกเหนือมาตรฐาน BMP ที่ทำให้ ChromeDriver แครช"""
    return "".join(c for c in text if ord(c) <= 0xFFFF)

# กรอง Prompt ให้สะอาดก่อนให้บอทพิมพ์
job_prompt_safe = clean_text_for_selenium(job_prompt)

if not is_chrome_ready():
    print("❌ ระบบหยุดทำงาน: มองไม่เห็น Chrome ในโหมดนักพัฒนาครับ!")
    exit(1)

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 15)

try:
    driver.switch_to.window(driver.current_window_handle)
    driver.maximize_window()
    time.sleep(1) 
except:
    pass

# =======================================================
# 🖱️ ฟังก์ชันคลิกด้วยเมาส์จำลอง
# =======================================================
def real_mouse_click(driver, xpath_list, wait_time=0.5):
    for xpath in xpath_list:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.5)
                ActionChains(driver).move_to_element(el).click().perform()
                time.sleep(wait_time)
                return True
        except:
            continue
    return False

# =======================================================
# 🔄 ฟังก์ชันสลับโหมด (รูปภาพ / วิดีโอ) บน Google Flow
# =======================================================
def switch_model_mode(target_mode):
    print(f"   🔄 กำลังสลับไปที่โหมด: {target_mode}...")
    indicator_xpaths = [
        "//button[descendant::*[contains(text(), 'Nano Banana') or contains(text(), 'วิดีโอ') or contains(text(), 'Veo')]]",
        "//div[contains(@class, 'model-selector')]" 
    ]
    if real_mouse_click(driver, indicator_xpaths, wait_time=1):
        tab_xpaths = [f"//div[@role='tab' or @role='button'][contains(., '{target_mode}')]"]
        if real_mouse_click(driver, tab_xpaths, wait_time=1):
            return True
    return False

# =======================================================
# ➕ ฟังก์ชันกดปุ่ม + และเลือกไอเทม
# =======================================================
def click_plus_and_select_item(item_index):
    print(f"   ➕ กำลังกดปุ่ม + เพื่อเพิ่มรูปภาพลำดับที่ {item_index}...")
    plus_btn_xpaths = ["//button[@aria-label='แนบไฟล์' or contains(@aria-label, 'Attach') or descendant::*[text()='+']]", "//div[contains(text(), '+')]"]
    if real_mouse_click(driver, plus_btn_xpaths, wait_time=1.5):
        gallery_item_xpaths = [f"(//div[contains(@class, 'gallery-item') or @role='listitem'])[{item_index}]"]
        if real_mouse_click(driver, gallery_item_xpaths, wait_time=1):
            return True
    return False

# =======================================================
# 📡 เรดาร์ตรวจจับความสำเร็จ 100% (Smart Wait)
# =======================================================
def smart_wait_for_generation(driver, media_type="image", timeout=300):
    print(f"   📡 เรดาร์ทำงาน: กำลังเฝ้ารอระบบเจน {media_type} จนครบ 100%...")
    start_time = time.time()
    
    target_xpath = "//img" if media_type == "image" else "//video"
    initial_count = len(driver.find_elements(By.XPATH, target_xpath))
    
    while time.time() - start_time < timeout:
        current_count = len(driver.find_elements(By.XPATH, target_xpath))
        
        if current_count > initial_count:
            time.sleep(2)
            elapsed_time = int(time.time() - start_time)
            print(f"   ✅ ระบบสร้างผลงานเสร็จสมบูรณ์ 100% แล้ว! (ใช้เวลาไปเพียง {elapsed_time} วินาที)")
            return True
        
        error_xpaths = driver.find_elements(By.XPATH, "//*[contains(text(), 'ลองอีกครั้ง') or contains(text(), 'Try again')]")
        if len(error_xpaths) > 0 and error_xpaths[0].is_displayed():
            print("   ❌ ระบบ Google Flow ขัดข้อง หรือคีย์ติดลิมิต! กรุณาเช็กหน้าจอ")
            return False
            
        time.sleep(2)
        
    print(f"   ❌ รอนานเกิน {timeout} วินาที เรดาร์ขอหยุดทำงานเผื่อระบบค้างครับ!")
    return False


try:
    if job_type == "scene_pipeline":
        
        # ==========================================
        # 🎬 กรณีฉากที่ 1 (Flow เต็มรูปแบบ: เจนภาพ -> เจนวิดีโอ)
        # ==========================================
        if job_is_first:
            print("=========================================")
            print("🚀 สเต็ป 1: เริ่มต้นสร้างภาพนิ่ง (Image Gen)")
            print("=========================================")
            
            new_chat_xpaths = ["//span[contains(text(), 'New chat') or contains(text(), 'แชทใหม่')]", "//a[contains(@href, '/app')]"]
            real_mouse_click(driver, new_chat_xpaths, wait_time=2.5)
            
            switch_model_mode("รูปภาพ")
            
            if job_ref_image and os.path.exists(job_ref_image):
                print("   📤 กำลังอัปโหลดรูปต้นฉบับ (Reference Image)...")
                try:
                    file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                    file_input.send_keys(job_ref_image)
                    time.sleep(5) 
                except:
                    print("   ❌ หาช่องอัปโหลดรูปไม่เจอ!")
            
            print("   ✍️ พิมพ์ Prompt สำหรับสร้างภาพนิ่ง...")
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            # ✨ ใช้ตัวแปรที่กรอง Emoji แล้ว ✨
            input_box.send_keys(job_prompt_safe)
            
            print("   ⏳ ส่งคำสั่งเจนภาพนิ่ง...")
            send_btn_xpath = "//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']]"
            real_mouse_click(driver, [send_btn_xpath])
            
            smart_wait_for_generation(driver, media_type="image", timeout=180)
            
            print("\n=========================================")
            print("🚀 สเต็ป 2: นำภาพนิ่งมาสร้างวิดีโอฉากแรก (Frame to Video)")
            print("=========================================")
            
            switch_model_mode("วิดีโอ")
            
            real_mouse_click(driver, ["//div[@role='tab' or @role='button'][contains(., 'ส่วนผสม') or contains(., 'Blend')]"], wait_time=1)
            real_mouse_click(driver, ["//*[contains(text(), '9:16')]"], wait_time=1)
            
            print(f"   ⚙️ ตั้งค่าเครดิต: {job_credit}")
            real_mouse_click(driver, [f"//div[@role='option' or contains(text(), '{job_credit}')]"], wait_time=1)

            click_plus_and_select_item(1)
            click_plus_and_select_item(2)

            print("   ✍️ บอทกำลังรอส่ง Prompt วิดีโอ...")
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            input_box.send_keys("Animate this scene smoothly, cinematic motion.") 
            
            real_mouse_click(driver, [send_btn_xpath])
            print("   ✅ ส่งคำสั่งสร้างคลิปฉากที่ 1 สำเร็จ!")
            
            smart_wait_for_generation(driver, media_type="video", timeout=300)

        # ==========================================
        # 🎬 กรณีฉากที่ 2 เป็นต้นไป (ต่อฉากขยาย)
        # ==========================================
        else:
            print(f"=========================================")
            print(f"🚀 สเต็ป: ต่อฉากที่ {job_scene_num} (Extend Video)")
            print(f"=========================================")
            
            print(f"   🔍 กำลังหาคลิปฉากก่อนหน้าเพื่อคลิกเข้าโหมดขยาย...")
            video_xpaths = ["(//video)[last()]", "(//div[@role='button' and descendant::video])[last()]"]
            real_mouse_click(driver, video_xpaths, wait_time=2.5)

            print(f"   ▶️ กำลังกดปุ่ม 'ขยาย' (Extend)...")
            extend_xpaths = ["//button[contains(., 'ขยาย') or contains(., 'Extend')]", "//span[contains(text(), 'ขยาย')]/ancestor::button"]
            if not real_mouse_click(driver, extend_xpaths, wait_time=1.5):
                print("   ❌ หาปุ่ม 'ขยาย' ไม่เจอ! (คลิปก่อนหน้าอาจยังไม่ 100%)")
                exit(1)
                
            real_mouse_click(driver, [f"//div[@role='option' or contains(text(), '{job_credit}')]"], wait_time=1)

            print(f"   ✍️ พิมพ์ Prompt ของฉาก {job_scene_num}...")
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_boxes = driver.find_elements(By.XPATH, prompt_input_xpath)
            input_box = input_boxes[-1] 
            ActionChains(driver).move_to_element(input_box).click().perform()
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            # ✨ ใช้ตัวแปรที่กรอง Emoji แล้ว ✨
            input_box.send_keys(job_prompt_safe) 
            
            send_btn_xpath = "(//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']])[last()]"
            real_mouse_click(driver, [send_btn_xpath])
            print(f"   ✅ ส่งคำสั่งต่อฉากที่ {job_scene_num} เรียบร้อย!")
            
            smart_wait_for_generation(driver, media_type="video", timeout=300)

    if os.path.exists(task_file):
        os.remove(task_file)

    print(f"\n🎉 บอททำงานฉากที่ {job_scene_num} เสร็จสมบูรณ์! เรดาร์ทำงานยอดเยี่ยม!")
    exit(0)

except Exception as e:
    print(f"\n❌ เกิดข้อผิดพลาดที่ไม่คาดคิดหลังบ้าน: {e}")
    exit(1)