"""
DB 초기화 스크립트 - 가짜 목업 데이터 전부 삭제
"""
import sqlite3
import sys

db_path = 'backend/onbid.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 삭제 전 카운트 확인
tables = ['analysis_results', 'market_prices', 'properties', 'bankruptcy_properties']
print("=== 삭제 전 데이터 현황 ===")
for t in tables:
    try:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count}건")
    except:
        print(f"  {t}: 테이블 없음")

# 외래키 순서대로 삭제 (analysis_results → market_prices → properties)
print("\n=== 데이터 초기화 중... ===")
cur.execute("DELETE FROM analysis_results")
cur.execute("DELETE FROM market_prices")
cur.execute("DELETE FROM properties")
cur.execute("DELETE FROM bankruptcy_properties")
conn.commit()

# 삭제 후 카운트 확인
print("\n=== 삭제 후 데이터 현황 ===")
for t in tables:
    try:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count}건")
    except:
        print(f"  {t}: 테이블 없음")

conn.close()

# 다운로드 파일 초기화
import os
import shutil
DOWNLOAD_DIR = 'backend/tmp_downloads'
print("\n=== 다운로드 임시파일 초기화 중... ===")
if os.path.exists(DOWNLOAD_DIR):
    deleted_files = 0
    for f in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                deleted_files += 1
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                deleted_files += 1
        except Exception as e:
            print(f"  -> 파일 삭제 실패 ({f}): {e}")
    print(f"  -> {deleted_files}개 임시 파일 삭제 완료.")

print("\n✅ DB 초기화 및 다운로드 폴더 클리어 완료! 이제 새 크롤링을 시작합니다.")
