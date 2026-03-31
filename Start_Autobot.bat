@echo off
cd /d "C:\Users\NEXT Speed\Desktop\autobot_project"
start chrome "http://localhost:8501/"
streamlit run app.py --server.headless true