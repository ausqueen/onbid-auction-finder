import sqlite3
import os

def fix_bad_ai():
    # 데이터베이스 연결
    db_path = os.path.join(os.path.dirname(__file__), 'onbid.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # '명시되어 있지 않' 문구가 포함되었거나, 
    # PDF 파일인데 주소(address)나 최저매각가격(min_price)이 누락/오류인 항목들을 찾음
    # (단, attachment_filename이 .pdf 로 끝나는 항목만 대상)
    
    query = """
    SELECT id, title, target_property, ai_summary, min_price, attachment_filename
    FROM bankruptcy_properties
    WHERE 
      is_analyzed = 1 
      AND attachment_filename LIKE '%.pdf'
      AND (
        target_property LIKE '%명시되어 있지 않%' 
        OR ai_summary LIKE '%명시되어 있지 않%'
        OR target_property LIKE '%구체적인 정보%'
        OR target_property IS NULL
        OR target_property = '내용 없음'
        OR target_property = '내용없음'
        OR min_price IS NULL
        OR min_price = '내용 없음'
        OR min_price = '내용없음'
        OR min_price = '-'
      )
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    print(f"발견된 불량/재분석 대상 데이터: {len(rows)}건")
    
    # is_analyzed 플래그를 0으로 초기화하여 analyze_worker.py가 다시 픽업하도록 함
    if rows:
        ids_to_fix = [r[0] for r in rows]
        print(f"재분석 대상 ID: {ids_to_fix}")
        
        update_query = f"UPDATE bankruptcy_properties SET is_analyzed = 0, ai_summary = NULL WHERE id IN ({','.join(map(str, ids_to_fix))})"
        cur.execute(update_query)
        conn.commit()
        print("데이터베이스 초기화 완료. analyze_worker.py가 이 항목들을 새로운 로직으로 재분석할 것입니다.")
    else:
        print("재분석 대상이 없습니다.")

    conn.close()

if __name__ == "__main__":
    fix_bad_ai()
