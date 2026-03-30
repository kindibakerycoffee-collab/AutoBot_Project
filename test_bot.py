import os
import json
import time
import socket
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains # 👈 อิมพอร์ตระบบเมาส์จริง

def is_chrome_ready():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', 9222)) == 0

print("🤖 กำลังปลุก AutoBot หลังบ้าน (Selenium)...")

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

print(f"✅ ได้รับภารกิจใหม่: โหมด {job_type.upper()}")

print("🌐 กำลังค้นหา Chrome (Port 9222)...")
if not is_chrome_ready():
    print("❌ ระบบหยุดทำงาน: มองไม่เห็น Chrome ในโหมดนักพัฒนาครับ!")
    exit(1)

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

print("🪄 กำลังดึงหน้าต่าง Google Flow ขึ้นมาโชว์ตัว...")
try:
    driver.switch_to.window(driver.current_window_handle)
    driver.maximize_window()
    driver.execute_script("window.focus();")
    time.sleep(1) 
except:
    pass

# =======================================================
# 🖱️ ฟังก์ชันใหม่: เล็งแล้วยิงด้วยเมาส์จริง (Physical Mouse Click)
# =======================================================
def real_mouse_click(driver, xpath_list):
    for xpath in xpath_list:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                # เลื่อนหน้าจอไปหาปุ่ม
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.5)
                # ใช้ ActionChains จำลองการขยับเมาส์ไปชี้แล้วคลิกซ้าย
                ActionChains(driver).move_to_element(el).click().perform()
                return True
        except:
            continue
    return False

try:
    if job_type == "scene_pipeline":
        
        # 🚀 สเต็ป 1: อัปโหลดรูปอ้างอิง
        if job_ref_image and os.path.exists(job_ref_image):
            print("📌 [1/5] กำลังอัปโหลดรูปอ้างอิงเข้าสู่ระบบ Google Flow...")
            try:
                file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
                file_input.send_keys(job_ref_image)
                print("   ✅ อัปโหลดรูปภาพต้นฉบับสำเร็จ รอโหลดสักครู่...")
                time.sleep(5) 
            except Exception as e:
                print(f"   ❌ หาช่องทางลับสำหรับอัปโหลดรูปไม่เจอ: {e}")
                exit(1)

        # 🎯 สเต็ป 2: เปิดตั้งค่าป๊อปอัป (แก้บั๊กผีหลอก)
        print("📌 [2/5] กำลังใช้เมาส์จำลองคลิกเปิดป๊อปอัป...")
        # เล็งปุ่มที่อยู่ก่อนหน้าปุ่มส่งข้อความเป๊ะๆ
        settings_xpaths = [
            "//button[descendant::*[@name='arrow-forward']]/preceding::button[1]",
            "//button[@aria-label='ส่งข้อความ' or @aria-label='Send message']/preceding::button[1]"
        ]
        
        if real_mouse_click(driver, settings_xpaths):
            print("   ✅ คลิกปุ่มด้วยเมาส์จำลองสำเร็จ! (รอเมนูกางออก 2 วินาที)")
            time.sleep(2) # รอให้แอนิเมชันป๊อปอัปเด้งจนสุด
        else:
            print("   ❌ หาปุ่มตั้งค่าข้างๆ ปุ่มส่งข้อความไม่เจอ!")

        # 🎯 สเต็ป 3: เลือกลำดับ (รูปภาพ -> 9:16 -> x1) แบบลุยไม่หยุด
        print("📌 [3/5] เลือกโหมด 'รูปภาพ' และตั้งค่าสัดส่วน...")
        
        print("   -> กำลังหาแท็บ 'รูปภาพ'...")
        img_xpaths = ["//div[@role='tab' or @role='button' or @role='menuitem'][contains(., 'รูปภาพ')]", "//span[contains(text(), 'รูปภาพ')]"]
        if real_mouse_click(driver, img_xpaths):
            print("   ✅ คลิกแท็บ 'รูปภาพ' สำเร็จ!")
            time.sleep(1.5)
        else:
            print("   ⚠️ หาแท็บ 'รูปภาพ' ไม่เจอ (ข้าม)")

        print("   -> กำลังหาปุ่มสัดส่วน '9:16'...")
        ratio_xpaths = ["//*[contains(text(), '9:16')]", "//span[contains(text(), '9:16')]"]
        if real_mouse_click(driver, ratio_xpaths):
            print("   ✅ คลิกสัดส่วน '9:16' สำเร็จ!")
            time.sleep(0.5)
        else:
            print("   ⚠️ หาปุ่ม '9:16' ไม่เจอ (ข้าม)")
            
        print("   -> กำลังเลือกจำนวน 'x1'...")
        x1_xpaths = ["//button[contains(., 'x1')]", "//div[@role='button' or @role='option'][contains(., 'x1')]"]
        real_mouse_click(driver, x1_xpaths)
        time.sleep(1)

        # 🎯 สเต็ป 4: พิมพ์ Prompt
        print("📌 [4/5] กำลังพิมพ์ Prompt ของฉากลงไป...")
        try:
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            # ใช้เมาส์คลิกกล่องข้อความก่อนพิมพ์
            ActionChains(driver).move_to_element(input_box).click().perform()
            time.sleep(0.5)
            
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            input_box.send_keys(job_prompt)
            print("   ✅ พิมพ์ Prompt สำเร็จ")
            time.sleep(1)
        except Exception as e:
            print("   ❌ หากล่องพิมพ์ข้อความไม่เจอ!")
            exit(1)

        # 🎯 สเต็ป 5: ส่งคำสั่ง
        print("📌 [5/5] กำลังกดส่งคำสั่ง...")
        try:
            send_btn_xpath = "//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']]"
            send_btn = wait.until(EC.presence_of_element_located((By.XPATH, send_btn_xpath)))
            ActionChains(driver).move_to_element(send_btn).click().perform()
            print("   ✅ ส่งคำสั่งสร้างภาพนิ่งสำเร็จ! ระบบกำลังประมวลผล...")
        except Exception as e:
            print("   ❌ หาปุ่มส่งข้อความไม่เจอ!")
            exit(1)

    if os.path.exists(task_file):
        os.remove(task_file)

    print("\n🎉 บอททำงานใน Phase 1 สำเร็จแล้วครับ!")
    exit(0)

except Exception as e:
    print(f"\n❌ เกิดข้อผิดพลาดที่ไม่คาดคิดหลังบ้าน: {e}")
    exit(1)