import os
import glob
from google import genai

api_key = "AIzaSyDB_I_WoaOaSaQG9V6bow_RszKJb6DOU9k"
client = genai.Client(api_key=api_key)

pdf_files = glob.glob('c:\\antigravity\\onbid-auction-finder\\tmp_downloads\\*.pdf')
if not pdf_files:
    print("NO PDF FOUND")
else:
    pdf_path = pdf_files[0]
    print("Uploading:", pdf_path)
    myfile = client.files.upload(file=pdf_path)
    print("Uploaded! URI:", myfile.uri)
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[myfile, "이 스캔본 파일의 본문을 간략히 한 줄 요약해라."]
    )
    print("AI Reply:", response.text)
