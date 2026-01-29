"""PDF文件处理核心类"""
import fitz
from pathlib import Path
from typing import Optional


class PDFHandler:
    """PDF文件处理类"""
    
    def __init__(self, file_path: str):
        """初始化PDF处理器"""
        self.file_path = file_path
        self.doc: Optional[fitz.Document] = None
        self.is_opened = False
        
    def open(self):
        """打开PDF文档"""
        if self.is_opened:
            return
        
        try:
            self.doc = fitz.open(self.file_path)
            self.is_opened = True
        except Exception as e:
            raise Exception(f"无法打开PDF文件: {e}")
    
    def close(self):
        """关闭PDF文档"""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.is_opened = False
    
    def __enter__(self):
        """上下文管理器入口"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def get_page_count(self) -> int:
        """获取PDF页数"""
        if not self.is_opened:
            self.open()
        return len(self.doc)
    
    def get_page(self, page_num: int) -> fitz.Page:
        """获取指定页面（0-based索引）"""
        if not self.is_opened:
            self.open()
        if page_num < 0 or page_num >= len(self.doc):
            raise IndexError(f"页面编号超出范围: {page_num}")
        return self.doc[page_num]
    
    def render_page(self, page_num: int, zoom: float = 1.0, dpi: int = 150) -> fitz.Pixmap:
        """渲染页面为图像"""
        page = self.get_page(page_num)
        scale = zoom * (dpi / 72.0)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix
    
    def save(self, output_path: str, optimize: bool = True):
        """保存PDF文档"""
        if not self.is_opened:
            raise Exception("PDF文档未打开")
        
        self.doc.save(output_path, garbage=4 if optimize else 0, deflate=True if optimize else False)
        
        if optimize:
            try:
                self.doc.rewrite_images()
            except:
                pass
