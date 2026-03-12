#!/usr/bin/env python3 
# -*- coding: utf-8 -*- 
 
import os 
import subprocess 
 
def svg_to_png_inkscape(svg_path, png_path=None, dpi=600): 
    """使用Inkscape将SVG转换为PNG
    
    Args:
        svg_path: SVG文件路径
        png_path: 输出PNG路径，默认为同目录下同名的.png
        dpi: 输出DPI，越高越清晰
    """
    if png_path is None: 
        png_path = os.path.splitext(svg_path)[0] + '.png' 
 
    if not os.path.exists(svg_path): 
        raise FileNotFoundError(f'SVG文件不存在: {svg_path}') 
 
    inkscape = r'D:\xidian_Master\专利与软著\软著\生成svg图片\bin\inkscape.exe'
    if not os.path.exists(inkscape): 
        raise FileNotFoundError(f'Inkscape未找到: {inkscape}') 
 
    cmd = [ 
        inkscape, 
        svg_path, 
        '--export-type=png', 
        f'--export-filename={png_path}', 
        f'--export-dpi={dpi}', 
    ] 
    subprocess.run(cmd, check=True) 
    return png_path 
 
if __name__ == '__main__': 
    svg_file = r'D:\xidian_Master\研究生论文\毕业论文\图片\第三章\端侧流程图.svg' 
    out_png = svg_file.replace('.svg', '.png') 
    png = svg_to_png_inkscape(svg_file, out_png, dpi=600) 
    print(f'[OK] saved: {png}')