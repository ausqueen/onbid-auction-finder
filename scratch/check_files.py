import os
import glob

download_dir = 'backend/tmp_downloads'
print(f"Files in {download_dir}:")
for pattern in ['1_*', '2_*', '3_*', '4_*', '5_*']:
    files = glob.glob(os.path.join(download_dir, pattern))
    print(f"Pattern {pattern}: {files}")
