import urllib.request
from bs4 import BeautifulSoup

url = 'https://www.scourt.go.kr/portal/notice/realestate/RealNoticeView.work?pageIndex=1&bub_cd=&searchWord=&searchOption=&seq_id=33060'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read()
        soup = BeautifulSoup(html, 'html.parser')
        files = soup.select("a[href^='javascript:download']")
        if not files:
            print("No files found!")
        for f in files:
            print('Attachment:', f.text.strip(), f.get('href', ''))
except Exception as e:
    print("Error:", e)
