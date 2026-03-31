import os
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

print("🤖 กำลังปลุก AutoBot หลังบ้าน (V.2 สไนเปอร์โหมด)...")

task_file = "bot_task.json"
if not os.path.exists(task_file):
    print("📭 ไม่พบคำสั่งใหม่ในระบบ!")
    exit(1)

with open(task_file, "r", encoding="utf-8") as f:
    task_data = json.load(f)

job_type = task_data.get("type", "unknown")
job_prompt = task_data.get("prompt", "")
job_credit = task_data.get("credit_mode", "Lower Priority")

print(f"✅ ได้รับภารกิจใหม่: โหมด {job_type.upper()}")
print(f"💰 โหมดเครดิตที่เลือก: {job_credit}")

if not is_chrome_ready():
    print("❌ ระบบหยุดทำงาน: มองไม่เห็น Chrome ในโหมดนักพัฒนาครับ!")
    exit(1)

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

try:
    driver.switch_to.window(driver.current_window_handle)
    driver.maximize_window()
    driver.execute_script("window.focus();")
except:
    pass

# =======================================================
# ⚡ ฟังก์ชัน JS Click (คลิกทะลุมิติแบบไร้เงา)
# =======================================================
def invisible_click(driver, xpath_list):
    for xpath in xpath_list:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in reversed(elements):
                if el.size['width'] > 0 and el.size['height'] > 0:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].style.border='3px solid red';", el)
                    print("   🎯 [สไนเปอร์ล็อกเป้า] เจอเป้าหมายแล้ว!")
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", el)
                    driver.execute_script("arguments[0].style.border='';", el)
                    return True
        except:
            continue
    return False

try:
    if job_type == "scene_pipeline":
        
        # 🎯 สเต็ป 1: ตั้งค่าเครดิต (Veo 3.1)
        print("📌 [1/3] กำลังตั้งค่าระบบเครดิต (Veo 3.1)...")
        
        # กดเปิด Dropdown ของ Veo 3.1
        veo_btn_xpaths = [
            "//button[contains(., 'Veo 3.1')]",
            "//div[@role='button' or @role='combobox'][contains(., 'Veo 3.1')]"
        ]
        if invisible_click(driver, veo_btn_xpaths):
            time.sleep(1.5) # รอเมนูกาง
            
            # เลือกโหมดตามที่ตั้งค่าใน Streamlit
            if "Lower Priority" in job_credit:
                print("   -> เลือกโหมดสายฟรี (Lower Priority)")
                target_credit_xpaths = ["//span[contains(text(), 'Lower Priority')]", "//div[contains(text(), 'Lower Priority')]"]
            else:
                print("   -> เลือกโหมดติดจรวด (Fast - ใช้เครดิต)")
                # หาปุ่ม Fast ที่ไม่ใช่ Lower Priority
                target_credit_xpaths = [
                    "//span[text()='Veo 3.1 - Fast']", 
                    "//div[text()='Veo 3.1 - Fast']",
                    "//*[contains(text(), 'Fast') and not(contains(text(), 'Lower'))]"
                ]
            
            invisible_click(driver, target_credit_xpaths)
            time.sleep(1)
            print("   ✅ ตั้งค่าเครดิตสำเร็จ!")
        else:
            print("   ⚠️ หาปุ่มเปลี่ยนเครดิต Veo 3.1 ไม่เจอ (อาจจะตั้งค่าไว้แล้ว บอทข้ามไปลุยต่อ)")

        # 🎯 สเต็ป 2: พิมพ์ Prompt สคริปต์
        print("📌 [2/3] กำลังพิมพ์ Prompt ของฉากลงไป...")
        try:
            prompt_input_xpath = "//div[@contenteditable='true']"
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, prompt_input_xpath)))
            
            driver.execute_script("arguments[0].style.border='3px solid blue';", input_box)
            time.sleep(1)
            
            driver.execute_script("arguments[0].click();", input_box)
            time.sleep(0.5)
            driver.execute_script("arguments[0].innerText = '';", input_box) 
            input_box.send_keys(job_prompt)
            print("   ✅ พิมพ์ Prompt สำเร็จ")
            driver.execute_script("arguments[0].style.border='';", input_box)
            time.sleep(1)
        except Exception as e:
            print("   ❌ หากล่อง 'สิ่งที่จะเกิดขึ้นต่อไป' ไม่เจอ!")
            exit(1)

        # 🎯 สเต็ป 3: กดปุ่มส่ง (Action!)
        print("📌 [3/3] กำลังสั่ง Action เริ่มถ่ายทำ...")
        try:
            send_btn_xpath = "//button[@aria-label='ส่งข้อความ' or @aria-label='Send message' or descendant::*[@name='arrow-forward']]"
            send_btn = wait.until(EC.presence_of_element_located((By.XPATH, send_btn_xpath)))
            
            driver.execute_script("arguments[0].style.border='3px solid green';", send_btn)
            time.sleep(1)
            
            driver.execute_script("arguments[0].click();", send_btn)
            print("   ✅ ส่งคำสั่งสำเร็จ! ผู้กำกับสั่ง Action แล้วครับ 🎬")
            driver.execute_script("arguments[0].style.border='';", send_btn)
        except Exception as e:
            print("   ❌ หาปุ่มส่งข้อความไม่เจอ!")
            exit(1)

    if os.path.exists(task_file):
        os.remove(task_file)

    print("\n🎉 บอททำงานสำเร็จ! โหมดสไนเปอร์แม่นยำ 100% ครับ!")
    exit(0)

except Exception as e:
    print(f"\n❌ เกิดข้อผิดพลาดที่ไม่คาดคิดหลังบ้าน: {e}")
    exit(1)