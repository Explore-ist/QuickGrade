import os
import cv2
from core import *

# ========= 1. 用户可修改的参数 ===============================================
root_dir     = STUDENTS_PATH       # 各页文件夹所在根目录
out_dir      = STITCHED_PATH   # 输出目录：建议放到 root_dir 之外
allow_suffix = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}

# ========= 2. 创建输出目录 ====================================================
os.makedirs(out_dir, exist_ok=True)

# ========= 3. 收集有效页文件夹（至少含 1 张图片） =============================
page_dirs = []
for d in sorted(os.listdir(root_dir)):
    full = os.path.join(root_dir, d)
    if not os.path.isdir(full):
        continue
    imgs = [f for f in os.listdir(full)
            if os.path.splitext(f)[1].lower() in allow_suffix]
    if imgs:
        page_dirs.append(d)
    else:
        print(f'⚠ 跳过子文件夹 {d}（无可用图片）')

if len(page_dirs) < 2:
    raise RuntimeError('需要至少两个含图片的页文件夹才能进行拼接！')

print(f'检测到页目录：{page_dirs}')

# ========= 4. 读取各页的文件列表（按顺序对应） ===============================
page_lists = []
for p in page_dirs:
    p_dir = os.path.join(root_dir, p)
    files = sorted([f for f in os.listdir(p_dir)
                    if os.path.splitext(f)[1].lower() in allow_suffix])
    page_lists.append([os.path.join(p_dir, f) for f in files])
    print(f'{p_dir} → {len(files)} 张')

num_students = min(len(lst) for lst in page_lists)
print(f'\n可配对学生数 = {num_students}\n')
if num_students == 0:
    raise RuntimeError('页文件夹里没有可配对的图片！')

# ========= 5. 拼接函数 =======================================================
def vconcat_resize(paths):
    mats = [cv2.imread(p, cv2.IMREAD_COLOR) for p in paths]
    if any(m is None for m in mats):
        bad = [p for p, m in zip(paths, mats) if m is None]
        raise RuntimeError(f'以下文件无法读取：{bad}')

    min_w = min(m.shape[1] for m in mats)
    mats = [cv2.resize(m, (min_w, int(m.shape[0]*min_w/m.shape[1])),
                       interpolation=cv2.INTER_AREA)
            if m.shape[1] != min_w else m
            for m in mats]
    return cv2.vconcat(mats)

# ========= 6. 主循环：依序输出 ==============================================
for i in range(num_students):
    img_paths = [pl[i] for pl in page_lists]          # 各页第 i 张
    merged    = vconcat_resize(img_paths)

    first_name = os.path.splitext(os.path.basename(page_lists[0][i]))[0]
    out_name   = first_name if first_name.isdigit() else f'{i+1}'
    out_path   = os.path.join(out_dir, f'{out_name}.jpg')

    cv2.imwrite(out_path, merged, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f'✔  已保存 {out_path}')

print(f'\n✅ 全部完成！输出目录：{os.path.abspath(out_dir)}')
