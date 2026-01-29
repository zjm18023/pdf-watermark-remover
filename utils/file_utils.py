"""
文件工具函数
"""
import os
from pathlib import Path
import fitz


def get_output_path(input_path, suffix="【去水印】"):
    """
    生成输出文件路径，避免覆盖原文件
    
    Args:
        input_path: 输入文件路径
        suffix: 文件名后缀
        
    Returns:
        str: 输出文件路径
    """
    input_path = Path(input_path)
    output_dir = input_path.parent
    output_stem = input_path.stem
    output_ext = input_path.suffix
    
    # 生成基础输出路径
    base_output_name = f"{output_stem}{suffix}{output_ext}"
    output_path = output_dir / base_output_name
    
    # 如果文件已存在，添加数字后缀
    counter = 1
    while output_path.exists():
        output_name = f"{output_stem}{suffix}_{counter}{output_ext}"
        output_path = output_dir / output_name
        counter += 1
    
    return str(output_path)


def get_file_size(file_path):
    """
    获取文件大小（以MB为单位）
    
    Args:
        file_path: 文件路径
        
    Returns:
        float: 文件大小（MB），保留2位小数
    """
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    except Exception:
        return 0.0


def get_pdf_page_count(file_path):
    """
    获取PDF文件页数
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        int: 页数，失败返回0
    """
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        return page_count
    except Exception:
        return 0


def is_pdf_file(file_path):
    """
    判断文件是否为PDF文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 如果是PDF文件返回True
    """
    try:
        return Path(file_path).suffix.lower() == '.pdf'
    except Exception:
        return False


def validate_pdf_file(file_path):
    """
    验证PDF文件是否有效
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        tuple: (is_valid, error_message)
            is_valid: 是否有效
            error_message: 错误信息（如果无效）
    """
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not is_pdf_file(file_path):
        return False, "不是PDF文件"
    
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        doc.close()
        
        if page_count == 0:
            return False, "PDF文件没有页面"
        
        return True, ""
    except Exception as e:
        return False, f"无法打开PDF文件: {str(e)}"
