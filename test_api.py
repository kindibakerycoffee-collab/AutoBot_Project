from google import genai

# วาง API Key ของคุณ (ใช้ตัวล่าสุดที่คุณสร้างมาได้เลยครับ)
API_KEY = "ใส่คีย์เทส" 

# รูปแบบการเรียกใช้งานแบบใหม่
client = genai.Client(api_key=API_KEY)

print("กำลังทดสอบเชื่อมต่อด้วยระบบใหม่ (google-genai)...")
print("-" * 30)

try:
    # เรียกใช้โมเดลเวอร์ชันใหม่ (gemini-2.5-flash)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='สวัสดี ทักทายฉันสั้นๆ 1 ประโยค'
    )
    
    print("✅ ยินดีด้วย! API Key และระบบใหม่ใช้งานได้สมบูรณ์ 100%")
    print("🤖 AI ตอบกลับมาว่า:", response.text)
    
except Exception as e:
    print("❌ การเชื่อมต่อล้มเหลว ลองเช็ค Error:")
    print(e)