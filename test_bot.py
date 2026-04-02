import os
import sys # 🟢 เพิ่มเพื่อรับ Argument จาก app.py
import json
import time
import socket
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def is_chrome_ready():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', 9222)) == 0

print("🤖 กำลังปลุก AutoBot หลังบ้าน (เวอร์ชันเจาะเกราะ JS Click 100%)...")

# 🟢 จุดแก้ไข 1: รับชื่อไฟล์ที่ส่งมาจาก app.py
task_file = sys.argv[1] if len(sys.argv) > 1 else "bot_task.json"
if not os.path.exists(task_file):
    print(f"📭 ไม่พบคำสั่งใหม่ในระบบ! ({task_file})")
    exit(1)

with open(task_file, "r", encoding="utf-8") as f:
    task_data = json.load(f)

job_type = task_data.get("type", "unknown")
job_image_prompt_safe = "".join(c for c in task_data.get("image_prompt", "") if ord(c) <= 0xFFFF)
job_video_prompt_safe = "".join(c for c in task_data.get("video_prompt", "") if ord(c) <= 0xFFFF)
job_credit = task_data.get("credit_mode", "Lower Priority")
job_ref_image = task_data.get("ref_image", "") 
job_scene_num = task_data.get("scene_num", 1)
job_is_first = task_data.get("is_first_scene", True)
job_ratio = task_data.get("target_ratio", "9:16")

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
# 💥 ฟังก์ชันคลิกทะลุเกราะ (JavaScript Click) - ตัวแก้ปัญหาหลัก
# =======================================================
def force_click(driver, xpath_list, wait_time=1.0):
    for xpath in xpath_list:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                # ใช้ JS สั่งคลิกโดยตรง ไม่สนว่าจะมีอะไรบังอยู่หรือไม่
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", el) 
                time.sleep(wait_time)
                return True
        except:
            continue
    return False

# 🟢 จุดแก้ไข 2: ฟังก์ชันสำหรับยัด Prompt ลงไปแบบติดจรวด ไม่ต้องรอพิมพ์ทีละตัวอักษร
def fast_typing(driver, input_element, text):
    driver.execute_script("""
        var el = arguments[0];
        el.innerText = arguments[1];
        // กระตุ้นให้ React/Angular ของ Google รู้ว่ามีการพิมพ์ข้อความแล้ว
        el.dispatchEvent(new Event('input', { bubbles: true }));
    """, input_element, text)
    time.sleep(0.3)
    # เคาะ Spacebar 1 ทีปิดท้าย เพื่อให้ปุ่มส่งข้อความ (Send) สว่างขึ้น
    input_element.send_keys(" ")

def switch_model_mode(target_mode):
    print(f"   🔄 กำลังบังคับเปิดหน้าต่างสลับโหมดเป็น: {target_mode}...")
    
    # 1. หากล่องปุ่มสลับโหมด
    mode_btn_xpaths = [
        "//button[contains(., 'Nano Banana') or contains(., 'Veo') or contains(., 'x1') or contains(., 'วิดีโอ')]",
        "//div[contains(@class, 'model-selector')]//button"
    ]
    
    if force_click(driver, mode_btn_xpaths, wait_time=1.5):
        # 2. เล็งแท็บเป้าหมาย
        tab_xpaths = [f"//div[@role='tab' or @role='button'][contains(., '{target_mode}')]"]
        if force_click(driver, tab_xpaths, wait_time=1):
            print(f"   ✅ สลับโหมด '{target_mode}' สำเร็จ!")
            return True
            
    print(f"   ⚠️ บังคับปุ่มไม่สำเร็จ บอทจะลุยต่อในโหมดปัจจุบัน")
    return False

def click_plus_and_select_item(item_index):
    print(f"   ➕ กำลังบังคับกดปุ่ม + และแนบรูป ลำดับที่ {item_index}...")
    plus_btn_xpaths = [
        "//button[contains(@aria-label, 'แนบ') or contains(@aria-label, 'Attach')]",
        "//button[contains(., '+')]"
    ]
    if force_click(driver, plus_btn_xpaths, wait_time=1.5):
        # เลือกรูปจากแกลลอรี่ (มักจะเป็น listitem ตัวแรกๆ)
        gallery_item_xpaths = [
            f"(//div[contains(@class, 'gallery') or @role='listbox']//div[@role='listitem'])[{item_index}]",
            f"(//div[contains(@class, 'image-container') or @role='button'])[{item_index}]"
        ]
        if force_click(driver, gallery_item_xpaths, wait_time=1.5):
            # คลิกพื้นที่ว่าง 1 ที เผื่อป๊อปอัปไม่ยอมปิดตัวลง
            driver.execute_script("document.body.click();")
            time.sleep(0.5)
            print(f"   ✅ แนบรูปสำเร็จ!")
            return True
    print(f"   ❌ แนบรูปไม่สำเร็จ!")
    return False

def smart_wait_for_generation(driver, media_type="image", timeout=300):
    print(f"   📡 เรดาร์ทำงาน: กำลังเฝ้าระบบเจน {media_type}...")
    start_time = time.time()
    target_xpath = "//img" if media_type == "image" else "//video"
    initial_count = len(driver.find_elements(By.XPATH, target_xpath))
    
    while time.time() - start_time < timeout:
        current_count = len(driver.find_elements(By.XPATH, target_xpath))
        elapsed_time = int(time.time() - start_time)
        
        if current_count > initial_count:
            if elapsed_time < 15:
                initial_count = current_count
                time.sleep(2)
                continue
            else:
                time.sleep(3) 
                print(f"   ✅ เจนเสร็จสมบูรณ์! (ใช้เวลา {elapsed_time} วินาที)")
                return True
        
        error_xpaths = driver.find_elements(By.XPATH, "//*[contains(text(), 'ลองอีกครั้ง') or contains(text(), 'Try again') or contains(text(), 'Couldn')]")
        if len(error_xpaths) > 0 and error_xpaths[0].is_displayed():
            print("   ❌ ขัดข้องบน Google Flow! กรุณาเช็กเบราว์เซอร์")
            return False
        time.sleep(2)
        
    print(f"   ❌ รอนานเกินเวลา เรดาร์ขอหยุดทำงาน!")
    return False

try:
    if job_type == "scene_pipeline" or job_type == "image_only":
        
        # ==========================================
        # 🎬 กรณีฉากที่ 1 (Image Gen -> Frame to Video) หรือ โปสเตอร์
        # ==========================================
        if job_is_first or job_type == "image_only":
            print("=========================================")
            print("🚀 สเต็ป 1: Image Gen (Nano Banana 2)")
            print("=========================================")
            
            force_click(driver, ["//span[contains(text(), 'New chat') or contains(text(), 'แชทใหม่')]", "//a[contains(@href, '/app')]"], wait_time=2.5)
            
            switch_model_mode("รูปภาพ")
            
            print(f"   ⚙️ ตั้งค่าสัดส่วนภาพ: {job_ratio}")
            force_click(driver, [f"//*[text()='{job_ratio}' or contains(text(), '{job_ratio}')]/ancestor-or-self::*[@role='button']"], wait_time=1)
            
            if job_ref_image and os.path.exists(job_ref_image):
                print("   📤 กำลังอัปโหลด Reference Image...")
                try:
                    file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                    file_input.send_keys(job_ref_image)
                    
                    # 🟢 จุดแก้ไข 3: ใช้ Wait ตรวจจับ UI รูปภาพโหลดเสร็จ แทน sleep(6)
                    wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'thumbnail') or @aria-label='Remove image' or @role='img' or contains(@class, 'preview')]")))
                    print("   ✅ รูปภาพโหลดเข้า Flow เรียบร้อย!")
                    time.sleep(1) # เผื่อจังหวะ UI กระตุก
                except Exception as e:
                    print(f"   ❌ หาช่องอัปโหลดไม่เจอ หรือโหลดช้าเกินไป! ({e})")
                
                # แนบรูปที่เพิ่งอัปโหลดลงในช่อง Prompt (ลำดับที่ 1)
                click_plus_and_select_item(1)
            
            print("   ✍️ พิมพ์ Image Prompt แบบติดจรวด...")
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            
            # 🟢 จุดแก้ไข 4: ใช้ fast_typing แทน send_keys
            fast_typing(driver, input_box, job_image_prompt_safe)
            
            send_btn_xpath = ["//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']]"]
            force_click(driver, send_btn_xpath)
            
            if not smart_wait_for_generation(driver, "image", 180):
                print("\n🛑 ยกเลิกสเต็ป 2 เนื่องจากรูปภาพล้มเหลว")
                exit(1)
            
            # หากเป็นแค่ภาพนิ่ง/โปสเตอร์ ให้จบการทำงานตรงนี้
            if job_type == "image_only":
                print(f"\n🎉 รันโปสเตอร์เสร็จสมบูรณ์!")
                if os.path.exists(task_file): os.remove(task_file)
                exit(0)
            
            print("\n=========================================")
            print("🚀 สเต็ป 2: Frame to Video (Veo 3.1)")
            print("=========================================")
            
            switch_model_mode("วิดีโอ")
            
            force_click(driver, [f"//div[@role='option' or contains(text(), '{job_credit}')]"], wait_time=1)

            # แนบภาพนิ่งที่เพิ่งเจนเสร็จ (ลำดับ 1) เพื่อใช้ตั้งต้นทำวิดีโอ
            click_plus_and_select_item(1) 

            print("   ✍️ พิมพ์ Video Prompt แบบติดจรวด...")
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            
            # 🟢 จุดแก้ไข 4: ใช้ fast_typing แทน
            fast_typing(driver, input_box, job_video_prompt_safe)
            
            force_click(driver, send_btn_xpath)
            
            if not smart_wait_for_generation(driver, "video", 300):
                exit(1)

        # ==========================================
        # 🎬 กรณีฉากที่ 2 เป็นต้นไป (Extend Scene)
        # ==========================================
        else:
            print(f"=========================================")
            print(f"🚀 สเต็ป: ขยายฉากที่ {job_scene_num} (Extend Scene)")
            print(f"=========================================")
            
            print(f"   🔍 หาคลิปล่าสุดเพื่อทำการ Extend...")
            video_xpaths = ["(//video)[last()]", "(//div[@role='button' and descendant::video])[last()]"]
            force_click(driver, video_xpaths, wait_time=2.5)

            print(f"   ▶️ กดปุ่ม Extend...")
            extend_xpaths = ["//button[contains(., 'ขยาย') or contains(., 'Extend')]", "//span[contains(text(), 'ขยาย')]/ancestor::button"]
            if not force_click(driver, extend_xpaths, wait_time=1.5):
                print("   ❌ หาปุ่ม Extend ไม่เจอ! คลิปก่อนหน้าอาจยังไม่ 100%")
                exit(1)
                
            force_click(driver, [f"//div[@role='option' or contains(text(), '{job_credit}')]"], wait_time=1)

            print(f"   ✍️ พิมพ์ Video Prompt สำหรับต่อฉาก {job_scene_num} แบบติดจรวด...")
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_boxes = driver.find_elements(By.XPATH, prompt_input_xpath)
            input_box = input_boxes[-1] 
            driver.execute_script("arguments[0].click();", input_box)
            
            # 🟢 จุดแก้ไข 4: ใช้ fast_typing แทน
            fast_typing(driver, input_box, job_video_prompt_safe)
            
            send_btn_xpath = ["(//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']])[last()]"]
            force_click(driver, send_btn_xpath)
            print(f"   ✅ ส่งคำสั่ง Extend เรียบร้อย!")
            
            if not smart_wait_for_generation(driver, "video", 300):
                exit(1)

    if os.path.exists(task_file):
        os.remove(task_file)

    print(f"\n🎉 Handoff ฉากที่ {job_scene_num} เสร็จสมบูรณ์!")
    exit(0)

except Exception as e:
    print(f"\n❌ ข้อผิดพลาดหลังบ้าน: {e}")
    exit(1)