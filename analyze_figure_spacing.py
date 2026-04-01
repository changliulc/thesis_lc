import os
from pypdf import PdfReader
import sys

def analyze_pdf_elements(pdf_path):
    """分析PDF页面元素位置"""
    try:
        reader = PdfReader(pdf_path)
        print(f"PDF总页数: {len(reader.pages)}")
        
        # 先找到图2.2所在的页面（跳过插图索引）
        figure2_2_page = -1
        print("正在搜索所有页面...")
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            # 跳过插图索引页面（通常前面几页）
            if "插图索引" in text or "图目录" in text:
                continue
            if "图2.2" in text or "图 2.2" in text:
                figure2_2_page = page_num
                print(f"找到图2.2在第 {page_num + 1} 页")
                break
        # 如果没找到，再打印所有包含"图2"的页面看看
        if figure2_2_page == -1:
            print("\n未找到图2.2，列出所有包含'图2'的页面：")
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if "图2" in text and "插图索引" not in text:
                    print(f"第 {page_num + 1} 页包含'图2'")
        
        if figure2_2_page == -1:
            print("未找到图2.2")
            return
        
        # 获取该页
        page = reader.pages[figure2_2_page]
        
        # 提取文本并分析位置
        print("\n=== 页面文本内容 ===")
        print(page.extract_text())
        
        # 尝试获取页面的介质框
        print(f"\n页面介质框: {page.mediabox}")
        
        # 查看页面的内容流
        print("\n=== 尝试获取内容流信息 ===")
        try:
            # 对于简单分析，我们可以尝试使用PyMuPDF库（fitz）来获取更详细的信息
            # 但先检查是否安装了PyMuPDF
            try:
                import fitz  # PyMuPDF
                print("\n使用PyMuPDF进行详细分析...")
                analyze_with_pymupdf(pdf_path, figure2_2_page)
            except ImportError:
                print("未安装PyMuPDF库。尝试安装: pip install pymupdf")
                print("使用pypdf进行基础分析...")
                basic_analysis_with_pypdf(page)
        except Exception as e:
            print(f"分析过程出错: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"读取PDF出错: {e}")
        import traceback
        traceback.print_exc()

def basic_analysis_with_pypdf(page):
    """使用pypdf进行基础分析"""
    print("\n=== pypdf基础分析 ===")
    print(f"页面尺寸: 宽度={page.mediabox.width}, 高度={page.mediabox.height}")
    print("\n注意: pypdf对文本位置的提取有限，建议安装PyMuPDF (fitz) 进行更精确的分析")

def analyze_with_pymupdf(pdf_path, page_num):
    """使用PyMuPDF进行详细分析"""
    import fitz
    
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    print(f"\n=== PyMuPDF详细分析 - 第 {page_num + 1} 页 ===")
    print(f"页面尺寸: {page.rect}")
    
    # 获取所有文本块
    blocks = page.get_text("blocks")
    blocks.sort(key=lambda b: (b[1], b[0]))  # 按y坐标排序（从上到下）
    
    print("\n=== 页面文本块（按位置排序） ===")
    figure2_2_found = False
    figure2_2_bottom = 0
    next_text_top = 0
    
    for i, block in enumerate(blocks):
        x0, y0, x1, y1, text, block_type, block_no = block
        # 只处理文本块
        if block_type == 0:
            print(f"块 {i}: y=[{y0:.1f}, {y1:.1f}], 文本: {text[:60]}...")
            
            # 查找图2.2
            if "图2.2" in text or "图 2.2" in text:
                figure2_2_found = True
                figure2_2_bottom = y1
                print(f"  ★ 找到图2.2标题，底部y坐标: {y1:.1f}")
            
            # 如果已经找到图2.2，找下一个文本块
            elif figure2_2_found and next_text_top == 0:
                next_text_top = y0
                print(f"  ★ 找到下一个文本块，顶部y坐标: {y0:.1f}")
                break
    
    # 计算间距
    if figure2_2_found and next_text_top > 0:
        spacing = next_text_top - figure2_2_bottom
        print(f"\n=== 计算结果 ===")
        print(f"图2.2标题底部y坐标: {figure2_2_bottom:.1f}")
        print(f"下一段文本顶部y坐标: {next_text_top:.1f}")
        print(f"垂直间距 (像素): {spacing:.1f}")
        
        # 假设PDF是72 DPI（常见的PDF分辨率），转换为pt（1pt = 1像素@72DPI）
        spacing_pt = spacing
        print(f"垂直间距 (pt, 假设72DPI): {spacing_pt:.1f} pt")
        
        # 也可以转换为其他单位
        print(f"垂直间距 (英寸): {spacing/72:.3f} 英寸")
        print(f"垂直间距 (毫米): {spacing/72*25.4:.1f} mm")
    else:
        print("\n未能计算间距，请检查是否正确找到图2.2和后续文本")
    
    # 保存页面图像以便查看
    print(f"\n正在生成页面预览图...")
    pix = page.get_pixmap()
    output_image = "page_preview.png"
    pix.save(output_image)
    print(f"页面预览图已保存到: {output_image}")
    
    doc.close()

if __name__ == "__main__":
    # PDF文件路径
    pdf_path = r"d:\xidian_Master\研究生论文\毕业论文\xduts-main\盲审文件图表重做版\xdupgthesis_template_lc.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"错误: PDF文件不存在: {pdf_path}")
        sys.exit(1)
    
    print(f"正在分析PDF文件: {pdf_path}")
    analyze_pdf_elements(pdf_path)
