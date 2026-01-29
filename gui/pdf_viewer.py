"""PDF查看器"""
import customtkinter as ctk
from tkinter import Canvas, Scrollbar
from PIL import Image, ImageTk
import fitz
from pathlib import Path
from utils.window_utils import show_error, center_window


class PDFViewer:
    """PDF查看器窗口"""
    
    def __init__(self, parent, pdf_path):
        """初始化PDF查看器"""
        self.parent = parent
        self.pdf_path = pdf_path
        self.doc = None
        self.current_page = 0
        self.zoom = 1.0
        self.dpi = 150
        
        # 打开PDF文档
        try:
            self.doc = fitz.open(pdf_path)
            self.total_pages = len(self.doc)
        except Exception as e:
            show_error(parent, f"无法打开PDF文件: {e}")
            return
        
        # 创建窗口
        self.window = ctk.CTkToplevel(parent)
        self.window.title(f"PDF查看器 - {Path(pdf_path).name} (第 1 页 / 共 {self.total_pages} 页)")
        self.window.transient(parent)
        
        center_window(self.window, 1000, 800)
        
        # 创建UI
        self.create_ui()
        
        # 加载第一页
        self.load_page(0)
        
        # 绑定窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_ui(self):
        """创建UI界面"""
        # 主容器
        main_container = ctk.CTkFrame(self.window, fg_color=("white", "#F5F7FA"))
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 工具栏
        self.create_toolbar(main_container)
        
        # PDF显示区域
        self.create_viewer_area(main_container)
        
        # 状态栏
        self.create_status_bar(main_container)
        
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar_frame = ctk.CTkFrame(parent, fg_color=("white", "#FFFFFF"))
        toolbar_frame.pack(fill="x", pady=(0, 10))
        
        # 左侧：页面导航
        nav_frame = ctk.CTkFrame(toolbar_frame, fg_color=("white", "#FFFFFF"))
        nav_frame.pack(side="left", padx=15, pady=10)
        
        self.btn_prev = ctk.CTkButton(
            nav_frame,
            text="◀ 上一页",
            command=self.prev_page,
            width=100,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_prev.pack(side="left", padx=(0, 8))
        
        self.btn_next = ctk.CTkButton(
            nav_frame,
            text="下一页 ▶",
            command=self.next_page,
            width=100,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_next.pack(side="left", padx=(0, 8))
        
        self.page_label = ctk.CTkLabel(
            nav_frame,
            text="页码: 1 / 10",
            font=ctk.CTkFont(size=12)
        )
        self.page_label.pack(side="left", padx=10)
        
        self.page_entry = ctk.CTkEntry(
            nav_frame,
            width=60,
            height=30
        )
        self.page_entry.pack(side="left", padx=5)
        
        self.btn_jump = ctk.CTkButton(
            nav_frame,
            text="跳转",
            command=self.jump_to_page,
            width=60,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_jump.pack(side="left", padx=(0, 0))
        
        # 右侧：缩放控制
        zoom_frame = ctk.CTkFrame(toolbar_frame, fg_color=("white", "#FFFFFF"))
        zoom_frame.pack(side="right", padx=15, pady=10)
        
        self.btn_zoom_out = ctk.CTkButton(
            zoom_frame,
            text="🔍-",
            command=self.zoom_out,
            width=50,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_zoom_out.pack(side="left", padx=(0, 8))
        
        self.btn_zoom_in = ctk.CTkButton(
            zoom_frame,
            text="🔍+",
            command=self.zoom_in,
            width=50,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_zoom_in.pack(side="left", padx=(0, 8))
        
        self.zoom_label = ctk.CTkLabel(
            zoom_frame,
            text="缩放: 100%",
            font=ctk.CTkFont(size=12)
        )
        self.zoom_label.pack(side="left", padx=10)
        
        self.btn_fit_window = ctk.CTkButton(
            zoom_frame,
            text="适应窗口",
            command=self.fit_to_window,
            width=80,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_fit_window.pack(side="left", padx=(0, 8))
        
        self.btn_actual_size = ctk.CTkButton(
            zoom_frame,
            text="实际大小",
            command=self.actual_size,
            width=80,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        self.btn_actual_size.pack(side="left", padx=(0, 0))
        
    def create_viewer_area(self, parent):
        """创建PDF显示区域"""
        viewer_frame = ctk.CTkFrame(parent, fg_color=("white", "#FFFFFF"))
        viewer_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 使用标准Tkinter Canvas
        self.canvas = Canvas(
            viewer_frame,
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        
        v_scroll = Scrollbar(viewer_frame, orient="vertical", command=self.canvas.yview)
        h_scroll = Scrollbar(viewer_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        
        # 绑定鼠标滚轮缩放
        self.canvas.bind("<Button-4>", self.on_mousewheel)  # Linux
        self.canvas.bind("<Button-5>", self.on_mousewheel)  # Linux
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows/Mac
        
        # 绑定拖拽
        self.canvas.bind("<Button-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ctk.CTkFrame(parent, fg_color=("white", "#F8F9FA"))
        status_frame.pack(fill="x")
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="就绪",
            font=ctk.CTkFont(size=11),
            text_color="#7F8C8D"
        )
        self.status_label.pack(side="left", padx=15, pady=10)
        
    def load_page(self, page_num):
        """加载指定页面"""
        if not self.doc or page_num < 0 or page_num >= self.total_pages:
            return
        
        self.current_page = page_num
        page = self.doc[page_num]
        
        # 渲染页面
        scale = self.zoom * (self.dpi / 72.0)
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 转换为PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 显示在画布上
        self.display_image(img)
        
        # 更新页面标签
        self.page_label.configure(text=f"页码: {page_num + 1} / {self.total_pages}")
        self.page_entry.delete(0, "end")
        self.page_entry.insert(0, str(page_num + 1))
        
        # 更新窗口标题
        self.window.title(f"PDF查看器 - {Path(self.pdf_path).name} (第 {page_num + 1} 页 / 共 {self.total_pages} 页)")
        
        # 更新按钮状态
        self.btn_prev.configure(state="normal" if page_num > 0 else "disabled")
        self.btn_next.configure(state="normal" if page_num < self.total_pages - 1 else "disabled")
        
        # 更新状态栏
        self.status_label.configure(text=f"第 {page_num + 1} 页 / 共 {self.total_pages} 页")
        
    def display_image(self, img):
        """在画布上显示图像"""
        self.canvas.delete("all")
        
        # 转换为PhotoImage
        self.photo = ImageTk.PhotoImage(img)
        
        # 创建图像项
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
    def prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)
    
    def jump_to_page(self):
        """跳转到指定页"""
        try:
            page_num = int(self.page_entry.get()) - 1
            if 0 <= page_num < self.total_pages:
                self.load_page(page_num)
        except ValueError:
            pass
    
    def zoom_in(self):
        """放大"""
        self.zoom = min(self.zoom * 1.2, 5.0)
        self.update_zoom_label()
        self.load_page(self.current_page)
    
    def zoom_out(self):
        """缩小"""
        self.zoom = max(self.zoom / 1.2, 0.2)
        self.update_zoom_label()
        self.load_page(self.current_page)
    
    def fit_to_window(self):
        """适应窗口"""
        if not self.doc:
            return
        
        # 获取画布大小
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.zoom = 1.0
        else:
            # 获取页面大小
            page = self.doc[self.current_page]
            page_rect = page.rect
            
            # 计算缩放比例（90%以适应窗口）
            zoom_x = (canvas_width * 0.9) / page_rect.width
            zoom_y = (canvas_height * 0.9) / page_rect.height
            self.zoom = min(zoom_x, zoom_y)
        
        self.update_zoom_label()
        self.load_page(self.current_page)
    
    def actual_size(self):
        """实际大小"""
        self.zoom = 1.0
        self.update_zoom_label()
        self.load_page(self.current_page)
    
    def update_zoom_label(self):
        """更新缩放标签"""
        self.zoom_label.configure(text=f"缩放: {int(self.zoom * 100)}%")
    
    def on_mousewheel(self, event):
        """鼠标滚轮事件（缩放）"""
        if event.delta > 0 or event.num == 4:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def on_drag_start(self, event):
        """开始拖拽"""
        self.canvas.scan_mark(event.x, event.y)
    
    def on_drag_move(self, event):
        """拖拽移动"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.doc:
            self.doc.close()
        self.window.destroy()
    
    def run(self):
        """运行查看器"""
        self.window.mainloop()

