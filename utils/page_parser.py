"""
页面范围解析器 - 解析页面范围字符串
"""
import re


def parse_page_range(page_range_str):
    """
    解析页面范围字符串，返回页面集合
    
    支持的格式：
    - "1-5" -> {1, 2, 3, 4, 5}
    - "1, 3, 5" -> {1, 3, 5}
    - "1-5, 10, 15-20" -> {1, 2, 3, 4, 5, 10, 15, 16, 17, 18, 19, 20}
    
    Args:
        page_range_str: 页面范围字符串
        
    Returns:
        set: 页面编号集合（1-based）
    """
    if not page_range_str or not page_range_str.strip():
        return set()
    
    pages = set()
    
    # 分割不同的范围段
    parts = re.split(r'[,，]', page_range_str.strip())
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # 匹配范围格式 "开始-结束" 或单个页码
        match = re.match(r'(\d+)(?:-(\d+))?', part)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            
            # 添加到集合
            for page_num in range(start, end + 1):
                pages.add(page_num)
    
    return pages


def is_page_excluded(page_num, excluded_pages_str):
    """
    判断页面是否被排除
    
    Args:
        page_num: 页面编号（1-based）
        excluded_pages_str: 排除页面范围字符串
        
    Returns:
        bool: 如果页面被排除返回True，否则返回False
    """
    if not excluded_pages_str or not excluded_pages_str.strip():
        return False
    
    excluded_pages = parse_page_range(excluded_pages_str)
    return page_num in excluded_pages


def format_page_range(pages):
    """
    格式化页面集合为范围字符串
    
    Args:
        pages: 页面编号集合或列表（1-based）
        
    Returns:
        str: 格式化的页面范围字符串，如 "1-5, 10, 15-20"
    """
    if not pages:
        return ""
    
    # 转换为排序的列表
    sorted_pages = sorted(set(pages))
    
    ranges = []
    start = sorted_pages[0]
    end = sorted_pages[0]
    
    for i in range(1, len(sorted_pages)):
        if sorted_pages[i] == end + 1:
            # 连续页面，扩展范围
            end = sorted_pages[i]
        else:
            # 不连续，保存当前范围
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = sorted_pages[i]
            end = sorted_pages[i]
    
    # 添加最后一个范围
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ", ".join(ranges)
