import os
import subprocess

def ensure_file_permissions(filepath: str):
    """
    Windows 환경에서 지정한 파일/디렉터리가 존재하도록 하고,
    빌트인 Users 그룹(SID: *S-1-5-32-545)에 수정(Modify) 권한을 명시적으로 부여합니다.
    이 함수는 로그 파일이나 DB 파일에 대해 SYSTEM 권한으로 실행 시 락이 걸리는 현상을 방지합니다.
    """
    if os.name != "nt":
        return
    
    filepath = os.path.abspath(filepath)
    try:
        # 1. 상위 디렉터리 생성 및 권한 설정
        dirpath = os.path.dirname(filepath)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
            # 디렉터리에 상속 권한 부여 (OI)(CI)M
            subprocess.run(
                ["icacls", dirpath, "/grant", "*S-1-5-32-545:(OI)(CI)M"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        
        # 2. 파일이 존재하지 않는 경우 빈 파일 생성
        if not os.path.exists(filepath):
            with open(filepath, "a", encoding="utf-8") as f:
                pass
        
        # 3. 파일 자체에 수정 권한 부여
        subprocess.run(
            ["icacls", filepath, "/grant", "*S-1-5-32-545:M"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
    except Exception:
        pass  # 예외 발생 시 다른 로직에 영향을 주지 않기 위해 무시
