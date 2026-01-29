"""水印删除逻辑"""
import fitz
from typing import List, Dict, Set
from utils.page_parser import is_page_excluded


class WatermarkRemover:
    """水印删除器"""
    
    PDF_REDACT_IMAGE_PIXELS = fitz.PDF_REDACT_IMAGE_PIXELS
    PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED = fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED
    PDF_REDACT_TEXT_REMOVE = fitz.PDF_REDACT_TEXT_REMOVE
    
    def __init__(self, pdf_handler):
        """初始化水印删除器"""
        self.pdf_handler = pdf_handler
        self.doc = pdf_handler.doc
        
    def remove_regions(self, regions: List[Dict], excluded_pages: Set[int] = None, 
                      mode: str = "actual"):
        """删除指定区域"""
        if excluded_pages is None:
            excluded_pages = set()
        
        page_count = self.pdf_handler.get_page_count()
        page_redactions = {}
        
        for region in regions:
            rect = region["rect"]
            scope = region.get("scope", "current")
            region_page = region.get("page")
            
            if scope == "current" and region_page is not None:
                target_pages = [region_page]
            elif scope == "all_pages" or scope == "all_files":
                # all_files 在单个文件处理时等同于 all_pages
                target_pages = list(range(page_count))
            else:
                target_pages = [region_page] if region_page is not None else []
            
            for page_num in target_pages:
                if (page_num + 1) in excluded_pages:
                    continue
                
                if page_num not in page_redactions:
                    page_redactions[page_num] = []
                page_redactions[page_num].append(rect)
        
        for page_num, rects in page_redactions.items():
            page = self.pdf_handler.get_page(page_num)
            
            for rect in rects:
                if mode == "cover":
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                else:
                    page.add_redact_annot(rect)
            
            page.apply_redactions(
                images=self.PDF_REDACT_IMAGE_PIXELS,
                graphics=self.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                text=self.PDF_REDACT_TEXT_REMOVE
            )
    
    def remove_text(self, texts: List[str], excluded_pages: Set[int] = None):
        """删除指定文字"""
        if excluded_pages is None:
            excluded_pages = set()
        
        page_count = self.pdf_handler.get_page_count()
        text_match_counts = {text.strip(): 0 for text in texts if text and text.strip()}
        
        for page_num in range(page_count):
            if (page_num + 1) in excluded_pages:
                continue
            
            page = self.pdf_handler.get_page(page_num)
            page_has_redactions = False
            
            for text in texts:
                if not text or not text.strip():
                    continue
                
                text_clean = text.strip()
                text_instances = page.search_for(text_clean)
                
                if text_clean in text_match_counts:
                    text_match_counts[text_clean] += len(text_instances)
                
                for rect in text_instances:
                    page.add_redact_annot(rect)
                    page_has_redactions = True
            
            if page_has_redactions:
                page.apply_redactions(
                    images=self.PDF_REDACT_IMAGE_PIXELS,
                    graphics=self.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                    text=self.PDF_REDACT_TEXT_REMOVE
                )
        
        return text_match_counts
    
    def remove_text_from_page(self, page_num: int, texts: List[str]):
        """从指定页面删除文字"""
        page = self.pdf_handler.get_page(page_num)
        has_redactions = False
        
        for text in texts:
            if not text or not text.strip():
                continue
            
            # 搜索文字实例
            text_instances = page.search_for(text.strip())
            
            # 为每个实例添加删除注释
            for rect in text_instances:
                page.add_redact_annot(rect)
                has_redactions = True
        
        # 应用删除
        if has_redactions:
            page.apply_redactions(
                images=self.PDF_REDACT_IMAGE_PIXELS,
                graphics=self.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                text=self.PDF_REDACT_TEXT_REMOVE
            )
