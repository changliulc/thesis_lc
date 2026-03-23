import os
from pypdf import PdfReader
from docx import Document

def extract_pdf_text(pdf_path, max_pages=10):
    """提取PDF前N页文本"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for i, page in enumerate(reader.pages[:max_pages]):
            text += f"\n--- Page {i+1} ---\n"
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def extract_docx_text(docx_path):
    """提取docx文本"""
    try:
        doc = Document(docx_path)
        text = "\n".join([para.text for para in doc.paragraphs[:50]])
        return text
    except Exception as e:
        return f"Error reading DOCX: {e}"

# 文件路径
base_path = r"D:\my_app\wechat\xwechat_files\wxid_4ns7hqjaxq2l22_1cbc\msg\file\2026-03"

files = {
    "侯照莹": os.path.join(base_path, "侯照莹_面向双车道高速公路的多地磁传感器车辆目标跟踪方法研究_盲审版.pdf"),
    "黄研": os.path.join(base_path, "黄研-低功耗抗干扰地磁检测算法研究0320.docx"),
    "刘畅": os.path.join(base_path, "刘畅_面向智慧交通的车型分类及停车占用检测方法研究_盲审版.pdf"),
    "邱嘉乐": os.path.join(base_path, "邱嘉乐_面向智慧公路的LoRa网关设计与组网优化研究.pdf")
}

print("=" * 80)
print("论文内容提取分析")
print("=" * 80)

for name, path in files.items():
    print(f"\n{'='*80}")
    print(f"【{name}】")
    print(f"{'='*80}")
    
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        continue
    
    if path.endswith('.pdf'):
        text = extract_pdf_text(path, max_pages=5)
    elif path.endswith('.docx'):
        text = extract_docx_text(path)
    else:
        text = "不支持的文件格式"
    
    # 打印前2000字符
    print(text[:3000])
    print("\n... [内容截断] ...")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
