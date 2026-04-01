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

print("🤖 กำลังปลุก AutoBot หลังบ้าน (Selenium Ultimate Master)...")

task_file = "bot_task.json"
if not os.path.exists(task_file):
    print("📭 ไม่พบคำสั่งใหม่ในระบบ!")
    exit(1)

with open(task_file, "r", encoding="utf-8") as f:
    task_data = json.load(f)

job_type = task_data.get("type", "unknown")
# ดึงค่าพร้อมกรองอักขระแปลกๆ ทิ้งทันที (ป้องกันบอทแครช)
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

def switch_model_mode(target_mode):
    print(f"   🔄 กำลังคลิกเปิดหน้าต่างสลับโหมด: {target_mode}...")
    
    # เล็งหาปุ่มที่อยู่ก่อนปุ่มลูกศรส่ง (แม่นยำ 100%)
    mode_btn_xpaths = [
        "//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']]/preceding-sibling::*[1]",
        "//*[contains(text(), 'x1')]/ancestor::*[@role='button' or local-name()='button'][1]"
    ]
    
    popup_opened = real_mouse_click(driver, mode_btn_xpaths, wait_time=1.5)
    
    # ท่าไม้ตาย (JS) ถ้าคลิกธรรมดาไม่โดน
    if not popup_opened:
        try:
            driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for(var i=0; i<btns.length; i++){
                    if((btns[i].innerText.includes('x1') || btns[i].innerText.includes('Nano') || btns[i].innerText.includes('วิดีโอ')) && !btns[i].innerText.includes('ส่ง')){
                        btns[i].click();
                        break;
                    }
                }
            """)
            time.sleep(1.5)
            popup_opened = True
        except:
            pass

    if popup_opened:
        if real_mouse_click(driver, [f"//div[@role='tab' or @role='button'][contains(., '{target_mode}')]"], wait_time=1):
            print(f"   ✅ สลับเป็นโหมด '{target_mode}' สำเร็จ!")
            return True
            
    print(f"   ⚠️ หาปุ่มไม่เจอ บอทจะลุยต่อในโหมดปัจจุบัน")
    return False

def click_plus_and_select_item(item_index):
    print(f"   ➕ กำลังกดปุ่ม + และแนบรูป ลำดับที่ {item_index}...")
    plus_btn_xpaths = [
        "//button[descendant::*[text()='+'] or contains(@aria-label, 'แนบไฟล์')]",
        "//div[text()='+']/ancestor::button[1]"
    ]
    if real_mouse_click(driver, plus_btn_xpaths, wait_time=1.5):
        gallery_item_xpaths = [f"(//div[contains(@class, 'gallery-item') or @role='listitem'])[{item_index}]"]
        if real_mouse_click(driver, gallery_item_xpaths, wait_time=1):
            return True
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
            # ป้องกันเรดาร์โดนหลอกถ้ารูปโผล่มาไวกว่า 15 วิ (นั่นคือรูปอัปโหลด)
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
    if job_type == "scene_pipeline":
        
        # ==========================================
        # 🎬 กรณีฉากที่ 1 (Image Gen -> Frame to Video)
        # ==========================================
        if job_is_first:
            print("=========================================")
            print("🚀 สเต็ป 1: Image Gen (Nano Banana 2)")
            print("=========================================")
            
            real_mouse_click(driver, ["//span[contains(text(), 'New chat') or contains(text(), 'แชทใหม่')]", "//a[contains(@href, '/app')]"], wait_time=2.5)
            
            switch_model_mode("รูปภาพ")
            
            print(f"   ⚙️ ตั้งค่าสัดส่วนภาพ: {job_ratio}")
            ratio_xpaths = [f"//*[text()='{job_ratio}' or contains(text(), '{job_ratio}')]/ancestor-or-self::*[@role='button']"]
            real_mouse_click(driver, ratio_xpaths, wait_time=1)
            
            if job_ref_image and os.path.exists(job_ref_image):
                print("   📤 กำลังอัปโหลด Reference Image...")
                try:
                    file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                    file_input.send_keys(job_ref_image)
                    time.sleep(6) # รอรูปโหลดเข้า Flow
                except Exception as e:
                    print(f"   ❌ หาช่องอัปโหลดไม่เจอ! ({e})")
                
                # แนบรูปที่เพิ่งอัปโหลดลงในช่อง Prompt (ลำดับที่ 1)
                click_plus_and_select_item(1)
                time.sleep(1.5)
            
            print("   ✍️ พิมพ์ Image Prompt...")
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            input_box.send_keys(job_image_prompt_safe)
            
            send_btn_xpath = "//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']]"
            real_mouse_click(driver, [send_btn_xpath])
            
            if not smart_wait_for_generation(driver, "image", 180):
                print("\n🛑 ยกเลิกสเต็ป 2 เนื่องจากรูปภาพล้มเหลว")
                exit(1)
            
            print("\n=========================================")
            print("🚀 สเต็ป 2: Frame to Video (Veo 3.1)")
            print("=========================================")
            
            switch_model_mode("วิดีโอ")
            
            # เลือกระบบเครดิต
            real_mouse_click(driver, [f"//div[@role='option' or contains(text(), '{job_credit}')]"], wait_time=1)

            # แนบภาพนิ่งที่เพิ่งเจนเสร็จ (ลำดับ 1) เพื่อใช้ตั้งต้นทำวิดีโอ
            click_plus_and_select_item(1) 

            print("   ✍️ พิมพ์ Video Prompt...")
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            input_box.send_keys(job_video_prompt_safe) 
            
            real_mouse_click(driver, [send_btn_xpath])
            
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
            real_mouse_click(driver, video_xpaths, wait_time=2.5)

            print(f"   ▶️ กดปุ่ม Extend...")
            extend_xpaths = ["//button[contains(., 'ขยาย') or contains(., 'Extend')]", "//span[contains(text(), 'ขยาย')]/ancestor::button"]
            if not real_mouse_click(driver, extend_xpaths, wait_time=1.5):
                print("   ❌ หาปุ่ม Extend ไม่เจอ! คลิปก่อนหน้าอาจยังไม่ 100%")
                exit(1)
                
            real_mouse_click(driver, [f"//div[@role='option' or contains(text(), '{job_credit}')]"], wait_time=1)

            print(f"   ✍️ พิมพ์ Video Prompt สำหรับต่อฉาก {job_scene_num}...")
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_boxes = driver.find_elements(By.XPATH, prompt_input_xpath)
            input_box = input_boxes[-1] 
            ActionChains(driver).move_to_element(input_box).click().perform()
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            input_box.send_keys(job_video_prompt_safe) 
            
            send_btn_xpath = "(//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']])[last()]"
            real_mouse_click(driver, [send_btn_xpath])
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