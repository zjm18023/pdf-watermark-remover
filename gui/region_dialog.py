"""区域选择弹窗"""
import customtkinter as ctk
from tkinter import Canvas, Scrollbar, Menu
from PIL import Image, ImageTk
import fitz
from pathlib import Path
from utils.window_utils import show_error, center_window


class RegionDialog:
    def __init__(self, parent, pdf_path, file_list=None, current_file_index=0, existing_regions=None):
        self.parent = parent
        self.pdf_path = pdf_path
        self.file_list = file_list or [{"path": pdf_path, "name": Path(pdf_path).name}]
        self.current_file_index = current_file_index
        self.doc = None
        self.current_page = 0
        self.zoom = 0.9  # 默认90%显示
        # 加载已存在的区域（如果有）
        self.selected_regions = []
        if existing_regions:
            for region in existing_regions:
                # 确保 rect 对象存在且有效
                rect = region.get("rect")
                if rect is None:
                    continue  # 跳过无效的区域
                
                # 转换区域格式，确保包含所有必要字段
                region_copy = {
                    "rect": rect,
                    "page": region.get("page", 0),
                    "scope": region.get("scope", "current"),
                    "file_index": region.get("file_index", current_file_index)  # 如果没有file_index，使用当前文件索引
                }
                self.selected_regions.append(region_copy)
        self.selecting = False
        self.select_start = None
        self.select_rect = None
        self.result_regions = []  # 返回的区域列表
        self.page_image = None  # 当前页面的图像对象
        self.original_photo = None  # 保存原图的PhotoImage引用，防止被垃圾回收
        self.preview_photo = None  # 保存预览图的PhotoImage引用，防止被垃圾回收
        self.dragging = False  # 是否正在拖拽原图
        self.preview_dragging = False  # 是否正在拖拽预览图
        self.drag_start_x = 0  # 拖拽起始X坐标
        self.drag_start_y = 0  # 拖拽起始Y坐标
        self.pending_region = None  # 待确认的区域（等待右键菜单选择）
        
        # 打开PDF文档
        try:
            self.doc = fitz.open(pdf_path)
            self.total_pages = len(self.doc)
        except Exception as e:
            show_error(parent, f"无法打开PDF文件: {e}")
            return
            
        # 创建弹窗
        self.dialog = ctk.CTkToplevel(parent)
        self.update_title()
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        center_window(self.dialog, 1400, 950)
        
        # 创建UI
        self.create_ui()
        
        # 绑定窗口关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # 等待窗口完全显示后再加载第一页（确保画布大小已计算）
        self.dialog.update_idletasks()
        self.dialog.update()
        self.load_page(0)
    
    def update_title(self):
        """更新窗口标题"""
        current_file = self.file_list[self.current_file_index]
        file_name = current_file.get("name", Path(current_file["path"]).name)
        page_info = f"第 {self.current_page + 1} 页 / 共 {self.total_pages} 页" if hasattr(self, 'current_page') and hasattr(self, 'total_pages') else "第 1 页 / 共 1 页"
        file_info = f" - 文件 {self.current_file_index + 1}/{len(self.file_list)}" if len(self.file_list) > 1 else ""
        self.dialog.title(f"区域选择工具 - {file_name} ({page_info}){file_info}")
    
    def create_top_controls(self, parent):
        """创建顶部控制面板（应用范围和确认按钮）"""
        top_frame = ctk.CTkFrame(parent, fg_color=("white", "#FFFFFF"))
        top_frame.pack(fill="x", pady=(0, 8))
        
        # 左侧：使用说明
        left_frame = ctk.CTkFrame(top_frame, fg_color=("white", "#FFFFFF"))
        left_frame.pack(side="left", padx=10, pady=8)
        
        # 使用说明（放大并加粗）
        usage_label = ctk.CTkLabel(
            left_frame,
            text="使用说明：左键长按拖动位置 | 右键框选区域 | Del删除框选",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#2C3E50"
        )
        usage_label.pack(side="left", padx=(0, 0))
        
        # 中间：文件切换按钮（如果有多个文件）
        if len(self.file_list) > 1:
            center_frame = ctk.CTkFrame(top_frame, fg_color=("white", "#FFFFFF"))
            center_frame.pack(side="left", padx=10, pady=8, expand=True)
            
            self.btn_prev_file = ctk.CTkButton(
                center_frame,
                text="◀ 上一个文件",
                command=self.switch_to_prev_file,
                width=100,
                height=30,
                fg_color="#27AE60",
                hover_color="#229954",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white"
            )
            self.btn_prev_file.pack(side="left", padx=(0, 5))
            
            self.file_info_label = ctk.CTkLabel(
                center_frame,
                text=f"文件 {self.current_file_index + 1}/{len(self.file_list)}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#2C3E50"
            )
            self.file_info_label.pack(side="left", padx=5)
            
            self.btn_next_file = ctk.CTkButton(
                center_frame,
                text="下一个文件 ▶",
                command=self.switch_to_next_file,
                width=100,
                height=30,
                fg_color="#27AE60",
                hover_color="#229954",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white"
            )
            self.btn_next_file.pack(side="left", padx=(5, 0))
            
            # 更新按钮状态
            self.update_file_switch_buttons()
        
        # 右侧：确认和取消按钮
        right_frame = ctk.CTkFrame(top_frame, fg_color=("white", "#FFFFFF"))
        right_frame.pack(side="right", padx=10, pady=8)
        
        self.btn_cancel = ctk.CTkButton(
            right_frame,
            text="取消",
            command=self.cancel,
            width=80,
            height=30,
            fg_color="#95A5A6",
            hover_color="#7F8C8D",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.btn_cancel.pack(side="left", padx=(0, 8))
        
        self.btn_confirm = ctk.CTkButton(
            right_frame,
            text="确认并应用",
            command=self.confirm,
            width=120,
            height=30,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.btn_confirm.pack(side="left", padx=(0, 0))
        
    def create_ui(self):
        """创建UI界面"""
        # 主容器 - 使用浅色背景
        main_container = ctk.CTkFrame(self.dialog, fg_color=("white", "#F5F7FA"))
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 顶部：应用范围和确认按钮
        self.create_top_controls(main_container)
        
        # 中间：原图和预览并排显示
        self.create_image_panels(main_container)
        
        # 底部：页面导航和缩放控制
        self.create_navigation_panel(main_container)
        
    def create_image_panels(self, parent):
        """创建原图和预览面板"""
        image_frame = ctk.CTkFrame(parent, fg_color=("white", "#FFFFFF"))
        image_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 使用PanedWindow实现可调整大小的分栏
        paned = ctk.CTkFrame(image_frame, fg_color=("white", "#FFFFFF"))
        paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 左侧：原图显示区域
        left_frame = ctk.CTkFrame(paned, fg_color=("white", "#FFFFFF"))
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        left_label = ctk.CTkLabel(
            left_frame,
            text="原图显示区域",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        left_label.pack(pady=5)
        
        # 原图画布容器
        original_container = ctk.CTkFrame(left_frame, fg_color=("white", "#FFFFFF"))
        original_container.pack(fill="both", expand=True)
        
        # 使用标准Tkinter Canvas（CustomTkinter的Canvas功能有限）
        self.original_canvas = Canvas(
            original_container,
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        # 创建滚动条但不显示（保留滚动功能）
        original_v_scroll = Scrollbar(original_container, orient="vertical", command=self.original_canvas.yview)
        original_h_scroll = Scrollbar(original_container, orient="horizontal", command=self.original_canvas.xview)
        self.original_canvas.configure(yscrollcommand=original_v_scroll.set, xscrollcommand=original_h_scroll.set)
        
        self.original_canvas.pack(side="left", fill="both", expand=True)
        # 不显示滚动条，但保留滚动功能
        # original_v_scroll.pack(side="right", fill="y")
        # original_h_scroll.pack(side="bottom", fill="x")
        
        # 绑定选择事件
        self.original_canvas.bind("<Button-3>", self.on_right_click_start)  # 右键按下
        self.original_canvas.bind("<B3-Motion>", self.on_right_click_drag)  # 右键拖拽
        self.original_canvas.bind("<ButtonRelease-3>", self.on_right_click_end)  # 右键释放
        
        # 绑定拖拽事件（左键）
        self.original_canvas.bind("<Button-1>", self.on_left_click_start)  # 左键按下
        self.original_canvas.bind("<B1-Motion>", self.on_left_click_drag)  # 左键拖拽
        self.original_canvas.bind("<ButtonRelease-1>", self.on_left_click_end)  # 左键释放
        
        # 绑定鼠标滚轮缩放
        self.original_canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows/Mac
        self.original_canvas.bind("<Button-4>", self.on_mousewheel)  # Linux
        self.original_canvas.bind("<Button-5>", self.on_mousewheel)  # Linux
        
        # 设置画布可以获取焦点（用于鼠标滚轮事件和键盘事件）
        self.original_canvas.bind("<Enter>", lambda e: self.original_canvas.focus_set())
        self.original_canvas.bind("<Leave>", lambda e: self.original_canvas.master.focus_set())
        
        # 绑定Delete键删除最后一个区域
        self.original_canvas.bind("<KeyPress-Delete>", self.delete_last_region)
        self.original_canvas.bind("<KeyPress-BackSpace>", self.delete_last_region)
        
        # 右侧：实时预览区域
        right_frame = ctk.CTkFrame(paned, fg_color=("white", "#FFFFFF"))
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        right_label = ctk.CTkLabel(
            right_frame,
            text="实时预览区域 (显示删除后的效果)",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        right_label.pack(pady=5)
        
        # 预览画布容器
        preview_container = ctk.CTkFrame(right_frame, fg_color=("white", "#FFFFFF"))
        preview_container.pack(fill="both", expand=True)
        
        self.preview_canvas = Canvas(
            preview_container,
            bg="white",
            highlightthickness=1,
            highlightbackground="gray"
        )
        # 创建滚动条但不显示（保留滚动功能）
        preview_v_scroll = Scrollbar(preview_container, orient="vertical", command=self.preview_canvas.yview)
        preview_h_scroll = Scrollbar(preview_container, orient="horizontal", command=self.preview_canvas.xview)
        self.preview_canvas.configure(yscrollcommand=preview_v_scroll.set, xscrollcommand=preview_h_scroll.set)
        
        self.preview_canvas.pack(side="left", fill="both", expand=True)
        # 不显示滚动条，但保留滚动功能
        # preview_v_scroll.pack(side="right", fill="y")
        # preview_h_scroll.pack(side="bottom", fill="x")
        
        # 绑定预览图的拖拽事件（左键）
        self.preview_canvas.bind("<Button-1>", self.on_preview_left_click_start)
        self.preview_canvas.bind("<B1-Motion>", self.on_preview_left_click_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.on_preview_left_click_end)
        
    def create_navigation_panel(self, parent):
        """创建页面导航和缩放控制面板"""
        nav_frame = ctk.CTkFrame(parent, fg_color=("white", "#F8F9FA"))
        nav_frame.pack(fill="x", pady=(0, 8))
        
        # 页面导航（居中显示）
        nav_center = ctk.CTkFrame(nav_frame, fg_color=("white", "#F8F9FA"))
        nav_center.pack(expand=True, pady=6)
        
        self.btn_prev = ctk.CTkButton(
            nav_center,
            text="◀ 上一页",
            command=self.prev_page,
            width=80,
            height=28,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.btn_prev.pack(side="left", padx=(0, 5))
        
        self.btn_next = ctk.CTkButton(
            nav_center,
            text="下一页 ▶",
            command=self.next_page,
            width=80,
            height=28,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.btn_next.pack(side="left", padx=(0, 5))
        
        self.page_label = ctk.CTkLabel(
            nav_center,
            text="页码: 1 / 10",
            font=ctk.CTkFont(size=11)
        )
        self.page_label.pack(side="left", padx=8)
        
        self.page_entry = ctk.CTkEntry(
            nav_center,
            width=50,
            height=26
        )
        self.page_entry.pack(side="left", padx=3)
        
        self.btn_jump = ctk.CTkButton(
            nav_center,
            text="跳转",
            command=self.jump_to_page,
            width=50,
            height=28,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.btn_jump.pack(side="left", padx=(0, 5))
        
        # 适应窗口按钮放在跳转按钮后面
        self.btn_fit_window = ctk.CTkButton(
            nav_center,
            text="适应窗口",
            command=self.fit_to_window,
            width=70,
            height=28,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.btn_fit_window.pack(side="left", padx=(0, 0))
        
        
    def load_page(self, page_num, preserve_position=False):
        """加载指定页面"""
        if not self.doc or page_num < 0 or page_num >= self.total_pages:
            return
            
        old_page = self.current_page
        self.current_page = page_num
        page = self.doc[page_num]
        
        # 渲染页面
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 转换为PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 显示在原图画布
        self.display_image(self.original_canvas, img)
        
        # 显示预览（应用已选区域）
        self.update_preview(sync_scroll=False)
        
        # 更新页面标签
        self.page_label.configure(text=f"页码: {page_num + 1} / {self.total_pages}")
        self.page_entry.delete(0, "end")
        self.page_entry.insert(0, str(page_num + 1))
        
        # 更新按钮状态
        self.btn_prev.configure(state="normal" if page_num > 0 else "disabled")
        self.btn_next.configure(state="normal" if page_num < self.total_pages - 1 else "disabled")
        
        # 更新窗口标题
        self.update_title()
        
    def display_image(self, canvas, img):
        """在画布上显示图像"""
        canvas.delete("all")
        
        # 保存图像对象
        self.page_image = img
        
        # 转换为PhotoImage并保存引用（防止被垃圾回收）
        photo = ImageTk.PhotoImage(img)
        
        # 根据画布类型保存引用
        if canvas == self.original_canvas:
            self.original_photo = photo  # 保存引用
        elif canvas == self.preview_canvas:
            self.preview_photo = photo  # 保存引用
        
        # 获取画布大小（确保窗口已完全显示）
        canvas.update_idletasks()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        # 如果画布大小无效，尝试多次更新并获取
        if canvas_width <= 1 or canvas_height <= 1:
            # 强制更新并等待
            canvas.update()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            # 如果还是无效，使用父容器的大小估算
            if canvas_width <= 1 or canvas_height <= 1:
                parent = canvas.master
                if parent:
                    parent.update_idletasks()
                    canvas_width = parent.winfo_width() - 20  # 减去一些边距
                    canvas_height = parent.winfo_height() - 50  # 减去标题等高度
        
        # 获取图像尺寸
        img_width = img.width
        img_height = img.height
        
        # 计算居中位置（当图像小于画布时）
        if canvas_width > 1 and canvas_height > 1 and img_width < canvas_width and img_height < canvas_height:
            # 图像小于画布，居中显示
            x = (canvas_width - img_width) / 2
            y = (canvas_height - img_height) / 2
            # 保存偏移量（用于绘制选择框）
            if canvas == self.original_canvas:
                self.original_img_offset_x = x
                self.original_img_offset_y = y
            elif canvas == self.preview_canvas:
                self.preview_img_offset_x = x
                self.preview_img_offset_y = y
            # 设置scrollregion包含画布大小（确保可以滚动到边缘）
            canvas.config(scrollregion=(0, 0, max(canvas_width, img_width), max(canvas_height, img_height)))
        else:
            # 图像大于等于画布，从(0,0)开始显示
            x = 0
            y = 0
            # 保存偏移量
            if canvas == self.original_canvas:
                self.original_img_offset_x = 0
                self.original_img_offset_y = 0
            elif canvas == self.preview_canvas:
                self.preview_img_offset_x = 0
                self.preview_img_offset_y = 0
            canvas.config(scrollregion=(0, 0, img_width, img_height))
        
        # 创建图像项
        canvas.create_image(x, y, anchor="nw", image=photo)
        
        # 绘制图像边界虚线框
        canvas.create_rectangle(
            x, y, x + img_width - 1, y + img_height - 1,
            outline="gray", width=1, dash=(3, 3), tags="image_border"
        )
        
        # 如果是原图画布，绘制所有已选择的区域框（需要调整坐标）
        if canvas == self.original_canvas:
            self.draw_selected_regions()
        
    def draw_selected_regions(self):
        """在原图画布上绘制所有已选择的区域框"""
        if not self.doc or not self.page_image:
            return
        
        # 先删除所有旧的区域框
        self.original_canvas.delete("region_box")
        
        page = self.doc[self.current_page]
        page_rect = page.rect
        
        # 获取图像尺寸
        img_width = self.page_image.width
        img_height = self.page_image.height
        
        # 重新绘制所有区域框
        for idx, region in enumerate(self.selected_regions):
            region_page = region.get("page")
            scope = region.get("scope", "current")
            region_file_index = region.get("file_index", self.current_file_index)  # 获取区域所属的文件索引
            
            # 根据应用范围判断是否应该显示在当前页面
            should_show = False
            
            if scope == "all_files":
                # 所有文件所有页：始终显示
                should_show = True
            elif scope == "all_pages":
                # 当前文件所有页：只在当前文件时显示
                should_show = (region_file_index == self.current_file_index)
            elif scope == "current":
                # 当前页：只在当前文件且当前页时显示
                should_show = (
                    region_file_index == self.current_file_index and 
                    region_page == self.current_page
                )
            
            if should_show:
                rect = region["rect"]
                # 将PDF坐标转换为图像坐标
                x1 = int((rect.x0 / page_rect.width) * img_width)
                y1 = int((rect.y0 / page_rect.height) * img_height)
                x2 = int((rect.x1 / page_rect.width) * img_width)
                y2 = int((rect.y1 / page_rect.height) * img_height)
                
                # 确保坐标在图像范围内
                x1 = max(0, min(x1, img_width))
                y1 = max(0, min(y1, img_height))
                x2 = max(0, min(x2, img_width))
                y2 = max(0, min(y2, img_height))
                
                # 绘制红色虚线框（需要加上图像偏移量）
                canvas_x1 = x1 + self.original_img_offset_x
                canvas_y1 = y1 + self.original_img_offset_y
                canvas_x2 = x2 + self.original_img_offset_x
                canvas_y2 = y2 + self.original_img_offset_y
                
                self.original_canvas.create_rectangle(
                    canvas_x1, canvas_y1,
                    canvas_x2, canvas_y2,
                    outline="red", width=2, dash=(5, 5), tags="region_box"
                )
                
                # 在区域框正中心显示序号和应用范围信息
                label_x = (canvas_x1 + canvas_x2) / 2  # 水平居中
                label_y = (canvas_y1 + canvas_y2) / 2  # 垂直居中
                
                # 根据应用范围生成文本
                scope_text_map = {
                    "current": "当前页",
                    "all_pages": "当前文件所有页",
                    "all_files": "所有文件所有页"
                }
                scope_text = scope_text_map.get(scope, "当前页")
                label_text = f"{idx + 1} - {scope_text}"
                
                # 估算文字大小并绘制白色背景矩形（使文字更清晰）
                # 根据文字长度估算宽度（每个字符约8像素，加上一些边距）
                text_width = len(label_text) * 8 + 10
                text_height = 18
                bg_x1 = label_x - text_width / 2
                bg_y1 = label_y - text_height / 2
                bg_x2 = label_x + text_width / 2
                bg_y2 = label_y + text_height / 2
                
                # 绘制白色背景矩形
                self.original_canvas.create_rectangle(
                    bg_x1, bg_y1, bg_x2, bg_y2,
                    fill="white", outline="white", tags="region_box"
                )
                
                # 创建序号和应用范围文字（红色，加粗）
                self.original_canvas.create_text(
                    label_x, label_y,
                    text=label_text,
                    fill="red",
                    font=("Arial", 11, "bold"),
                    anchor="center",  # 居中对齐
                    tags="region_box"
                )
    
    def update_preview(self, sync_scroll=True):
        """更新预览"""
        if not self.doc:
            return
            
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 转换为PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 应用已选区域（用白色填充）
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # 获取页面大小
        page = self.doc[self.current_page]
        page_rect = page.rect
        
        for region in self.selected_regions:
            region_page = region.get("page")
            scope = region.get("scope", "current")
            region_file_index = region.get("file_index", self.current_file_index)  # 获取区域所属的文件索引
            
            # 根据应用范围判断是否应该应用到当前页面
            apply_to_current = False
            
            if scope == "all_files":
                # 所有文件所有页：始终应用
                apply_to_current = True
            elif scope == "all_pages":
                # 当前文件所有页：只在当前文件时应用
                apply_to_current = (region_file_index == self.current_file_index)
            elif scope == "current":
                # 当前页：只在当前文件且当前页时应用
                apply_to_current = (
                    region_file_index == self.current_file_index and 
                    region_page == self.current_page
                )
            
            if apply_to_current:
                rect = region["rect"]
                # 将PDF坐标转换为图像坐标
                img_width = img.width
                img_height = img.height
                
                x1 = int((rect.x0 / page_rect.width) * img_width)
                y1 = int((rect.y0 / page_rect.height) * img_height)
                x2 = int((rect.x1 / page_rect.width) * img_width)
                y2 = int((rect.y1 / page_rect.height) * img_height)
                
                # 确保坐标在图像范围内
                x1 = max(0, min(x1, img_width))
                y1 = max(0, min(y1, img_height))
                x2 = max(0, min(x2, img_width))
                y2 = max(0, min(y2, img_height))
                
                # 绘制白色矩形（填充）
                draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255), outline=(255, 255, 255))
        
        # 保存原图的滚动位置
        if sync_scroll:
            orig_xview = self.original_canvas.xview()
            orig_yview = self.original_canvas.yview()
        
        self.display_image(self.preview_canvas, img)
        
        # 同步预览图的滚动位置
        if sync_scroll:
            self.preview_canvas.xview_moveto(orig_xview[0])
            self.preview_canvas.yview_moveto(orig_yview[0])
        
    def on_right_click_start(self, event):
        """右键按下开始选择"""
        self.selecting = True
        self.select_start = (self.original_canvas.canvasx(event.x), self.original_canvas.canvasy(event.y))
        
    def on_right_click_drag(self, event):
        """右键拖拽"""
        if not self.selecting:
            return
            
        cur_x = self.original_canvas.canvasx(event.x)
        cur_y = self.original_canvas.canvasy(event.y)
        
        # 删除旧的选择框
        if self.select_rect:
            self.original_canvas.delete(self.select_rect)
            
        # 绘制新的选择框
        self.select_rect = self.original_canvas.create_rectangle(
            self.select_start[0], self.select_start[1],
            cur_x, cur_y,
            outline="red", width=2, dash=(5, 5)
        )
        
    def on_right_click_end(self, event):
        """右键释放完成选择"""
        if not self.selecting:
            return
            
        self.selecting = False
        end_x = self.original_canvas.canvasx(event.x)
        end_y = self.original_canvas.canvasy(event.y)
        
        # 检查选择区域是否足够大
        if abs(end_x - self.select_start[0]) < 5 or abs(end_y - self.select_start[1]) < 5:
            # 区域太小，取消选择
            if self.select_rect:
                self.original_canvas.delete(self.select_rect)
                self.select_rect = None
            return
        
        # 获取页面对象以获取页面大小
        page = self.doc[self.current_page]
        page_rect = page.rect
        
        # 计算区域（转换为PDF坐标）
        # 获取画布上的图像坐标，需要减去图像偏移量（居中时）
        canvas_x1 = min(self.select_start[0], end_x) - self.original_img_offset_x
        canvas_y1 = min(self.select_start[1], end_y) - self.original_img_offset_y
        canvas_x2 = max(self.select_start[0], end_x) - self.original_img_offset_x
        canvas_y2 = max(self.select_start[1], end_y) - self.original_img_offset_y
        
        # 获取图像尺寸
        if self.page_image:
            img_width = self.page_image.width
            img_height = self.page_image.height
        else:
            # 如果没有图像，使用默认值
            img_width = int(page_rect.width * self.zoom)
            img_height = int(page_rect.height * self.zoom)
        
        # 转换为PDF坐标
        pdf_x1 = (canvas_x1 / img_width) * page_rect.width
        pdf_y1 = (canvas_y1 / img_height) * page_rect.height
        pdf_x2 = (canvas_x2 / img_width) * page_rect.width
        pdf_y2 = (canvas_y2 / img_height) * page_rect.height
        
        # 确保坐标在页面范围内
        pdf_x1 = max(0, min(pdf_x1, page_rect.width))
        pdf_y1 = max(0, min(pdf_y1, page_rect.height))
        pdf_x2 = max(0, min(pdf_x2, page_rect.width))
        pdf_y2 = max(0, min(pdf_y2, page_rect.height))
        
        # 创建区域对象（PDF坐标），暂时不设置scope，等待用户选择
        rect = fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
        self.pending_region = {
            "rect": rect,
            "page": self.current_page,
            "scope": None  # 等待用户选择
        }
        
        # 清除临时选择框
        if self.select_rect:
            self.original_canvas.delete(self.select_rect)
            self.select_rect = None
        
        # 先绘制待确认区域的框线（临时显示，让用户知道选择了哪个区域）
        self.draw_pending_region()
        
        # 显示右键菜单让用户选择应用范围
        self.show_scope_menu(event)
    
    def draw_pending_region(self):
        """绘制待确认的区域框线（临时显示）"""
        if not self.pending_region or not self.doc or not self.page_image:
            return
        
        # 删除之前的待确认区域框
        self.original_canvas.delete("pending_region")
        
        page = self.doc[self.current_page]
        page_rect = page.rect
        rect = self.pending_region["rect"]
        
        # 获取图像尺寸
        img_width = self.page_image.width
        img_height = self.page_image.height
        
        # 将PDF坐标转换为图像坐标
        x1 = int((rect.x0 / page_rect.width) * img_width)
        y1 = int((rect.y0 / page_rect.height) * img_height)
        x2 = int((rect.x1 / page_rect.width) * img_width)
        y2 = int((rect.y1 / page_rect.height) * img_height)
        
        # 确保坐标在图像范围内
        x1 = max(0, min(x1, img_width))
        y1 = max(0, min(y1, img_height))
        x2 = max(0, min(x2, img_width))
        y2 = max(0, min(y2, img_height))
        
        # 绘制待确认区域的框线（蓝色虚线，区别于已确认的红色）
        canvas_x1 = x1 + self.original_img_offset_x
        canvas_y1 = y1 + self.original_img_offset_y
        canvas_x2 = x2 + self.original_img_offset_x
        canvas_y2 = y2 + self.original_img_offset_y
        
        self.original_canvas.create_rectangle(
            canvas_x1, canvas_y1,
            canvas_x2, canvas_y2,
            outline="blue", width=2, dash=(5, 5), tags="pending_region"
        )
    
    def show_scope_menu(self, event):
        """显示右键菜单选择应用范围"""
        menu = Menu(self.original_canvas, tearoff=0)
        menu.add_command(label="应用当前页", command=lambda: self.confirm_region("current"))
        menu.add_command(label="应用当前文件所有页", command=lambda: self.confirm_region("all_pages"))
        if len(self.file_list) > 1:
            menu.add_command(label="应用所有文件所有页", command=lambda: self.confirm_region("all_files"))
        
        # 在鼠标位置显示菜单
        try:
            menu.tk_popup(event.x_root, event.y_root)
            # 等待菜单关闭
            self.dialog.wait_window(menu)
        except:
            pass
        finally:
            menu.grab_release()
            # 如果菜单关闭后还有待确认的区域（用户点击了菜单外），清除它
            if self.pending_region:
                self.original_canvas.delete("pending_region")
                self.pending_region = None
    
    def confirm_region(self, scope):
        """确认区域并添加到列表"""
        if self.pending_region:
            # 删除待确认区域的临时框线
            self.original_canvas.delete("pending_region")
            
            self.pending_region["scope"] = scope
            self.pending_region["file_index"] = self.current_file_index  # 记录区域是在哪个文件选择的
            self.selected_regions.append(self.pending_region)
            self.pending_region = None
            
            # 重新绘制所有选择框（包括新添加的）
            self.draw_selected_regions()
            self.update_preview()
    
    def delete_last_region(self, event=None):
        """删除指定的区域（支持输入序号或全部删除）"""
        if not self.selected_regions:
            return
        
        # 创建输入对话框
        input_dialog = ctk.CTkToplevel(self.dialog)
        input_dialog.title("删除区域")
        input_dialog.transient(self.dialog)
        input_dialog.grab_set()
        center_window(input_dialog, 450, 250)
        
        # 主容器
        main_frame = ctk.CTkFrame(input_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 提示信息
        info_text = f"共 {len(self.selected_regions)} 个区域\n\n"
        info_text += "输入方式：\n"
        info_text += "• 单个数字：如 1\n"
        info_text += "• 多个数字：如 1,3,5\n"
        info_text += "• 全部删除：输入 all 或 全部"
        
        info_label = ctk.CTkLabel(
            main_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        info_label.pack(pady=(10, 15))
        
        # 输入框
        entry = ctk.CTkEntry(
            main_frame,
            width=300,
            height=35,
            font=ctk.CTkFont(size=12)
        )
        entry.pack(pady=(0, 15))
        entry.focus_set()
        
        # 按钮容器
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack()
        
        result = {"value": None}
        
        def on_confirm():
            result["value"] = entry.get().strip()
            input_dialog.destroy()
        
        def on_cancel():
            input_dialog.destroy()
        
        # 确认按钮
        btn_confirm = ctk.CTkButton(
            btn_frame,
            text="确认",
            command=on_confirm,
            width=100,
            height=32,
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        btn_confirm.pack(side="left", padx=(0, 10))
        
        # 取消按钮
        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="取消",
            command=on_cancel,
            width=100,
            height=32,
            fg_color="#95A5A6",
            hover_color="#7F8C8D",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        btn_cancel.pack(side="left")
        
        # 绑定回车键
        entry.bind("<Return>", lambda e: on_confirm())
        entry.bind("<Escape>", lambda e: on_cancel())
        
        # 等待对话框关闭
        self.dialog.wait_window(input_dialog)
        
        user_input = result["value"]
        
        if not user_input:
            return  # 用户取消或输入为空
        
        # 处理全部删除
        if user_input.lower() in ['all', '全部']:
            self.selected_regions.clear()
            self.draw_selected_regions()
            self.update_preview()
            return
        
        # 解析数字列表
        try:
            # 分割逗号，提取数字
            numbers = [int(x.strip()) for x in user_input.split(',') if x.strip()]
            
            if not numbers:
                show_error(self.dialog, "请输入有效的区域序号")
                return
            
            # 验证序号范围并排序（从大到小删除，避免索引变化）
            valid_indices = []
            for num in numbers:
                if 1 <= num <= len(self.selected_regions):
                    valid_indices.append(num - 1)  # 转换为0-based索引
                else:
                    show_error(self.dialog, f"区域序号 {num} 超出范围（1-{len(self.selected_regions)}）")
                    return
            
            # 去重并排序（从大到小）
            valid_indices = sorted(set(valid_indices), reverse=True)
            
            # 删除区域（从大到小删除，避免索引变化）
            for idx in valid_indices:
                self.selected_regions.pop(idx)
            
            # 重新绘制选择框和预览
            self.draw_selected_regions()
            self.update_preview()
            
        except ValueError:
            show_error(self.dialog, "请输入有效的数字，多个数字用逗号分隔")
            
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
            
    def zoom_in(self, center_x=None, center_y=None):
        """放大（以中心点或指定点）"""
        old_zoom = self.zoom
        self.zoom = min(self.zoom * 1.2, 5.0)
        self.zoom_at_point(old_zoom, center_x, center_y)
        
    def zoom_out(self, center_x=None, center_y=None):
        """缩小（以中心点或指定点）"""
        old_zoom = self.zoom
        self.zoom = max(self.zoom / 1.2, 0.2)
        self.zoom_at_point(old_zoom, center_x, center_y)
    
    def zoom_at_point(self, old_zoom, center_x=None, center_y=None):
        """以指定点为中心进行缩放"""
        if not self.doc:
            return
        
        # 获取当前图像的bbox
        bbox = self.original_canvas.bbox("all")
        if not bbox:
            # 如果没有图像，直接加载页面
            self.load_page(self.current_page)
            return
        
        old_img_width = bbox[2] - bbox[0]
        old_img_height = bbox[3] - bbox[1]
        
        # 确定中心点（画布坐标）
        canvas_width = self.original_canvas.winfo_width()
        canvas_height = self.original_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = self.original_canvas.winfo_reqwidth()
            canvas_height = self.original_canvas.winfo_reqheight()
        
        if center_x is None or center_y is None:
            if canvas_width > 1 and canvas_height > 1:
                center_x = canvas_width / 2
                center_y = canvas_height / 2
            else:
                center_x = 0
                center_y = 0
        
        # 获取当前中心点对应的图像坐标（canvas坐标）
        img_x = self.original_canvas.canvasx(center_x)
        img_y = self.original_canvas.canvasy(center_y)
        
        # 计算在旧图像中的比例（相对于图像尺寸）
        if old_img_width > 0 and old_img_height > 0:
            ratio_x = img_x / old_img_width
            ratio_y = img_y / old_img_height
        else:
            ratio_x = 0.5
            ratio_y = 0.5
        
        # 加载新页面
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 显示图像
        self.display_image(self.original_canvas, img)
        
        # 获取新图像尺寸
        new_img_width = img.width
        new_img_height = img.height
        
        # 计算新图像中该比例对应的位置（canvas坐标）
        new_img_x = ratio_x * new_img_width
        new_img_y = ratio_y * new_img_height
        
        # 调整滚动位置，使新图像中的该位置出现在画布的中心点
        if new_img_width > canvas_width:
            # 计算滚动位置，使new_img_x出现在center_x位置
            # scroll_x表示滚动位置（0-1），new_img_x / new_img_width表示该点在图像中的位置
            # 我们需要让(new_img_x - scroll_x * new_img_width) = center_x
            scroll_x = (new_img_x - center_x) / new_img_width
            scroll_x = max(0, min(1, scroll_x))
            self.original_canvas.xview_moveto(scroll_x)
        else:
            # 图像小于画布，居中显示
            self.original_canvas.xview_moveto(0)
        
        if new_img_height > canvas_height:
            # 计算滚动位置，使new_img_y出现在center_y位置
            scroll_y = (new_img_y - center_y) / new_img_height
            scroll_y = max(0, min(1, scroll_y))
            self.original_canvas.yview_moveto(scroll_y)
        else:
            # 图像小于画布，居中显示
            self.original_canvas.yview_moveto(0)
        
        # 更新预览（同步滚动位置）
        self.update_preview(sync_scroll=True)
        
    def fit_to_window(self):
        """适应窗口"""
        if not self.doc:
            return
        
        # 获取画布大小
        self.original_canvas.update_idletasks()
        canvas_width = self.original_canvas.winfo_width()
        canvas_height = self.original_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.zoom = 0.9
        else:
            # 获取页面大小
            page = self.doc[self.current_page]
            page_rect = page.rect
            
            # 计算缩放比例（90%以适应窗口）
            zoom_x = (canvas_width * 0.9) / page_rect.width
            zoom_y = (canvas_height * 0.9) / page_rect.height
            self.zoom = min(zoom_x, zoom_y)
        
        self.load_page(self.current_page)
    
    def on_left_click_start(self, event):
        """左键按下开始拖拽"""
        # 如果右键正在选择区域，则不响应左键拖拽
        if self.selecting:
            return
        
        self.dragging = True
        self.original_canvas.scan_mark(event.x, event.y)
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_left_click_drag(self, event):
        """左键拖拽"""
        if self.dragging and not self.selecting:
            self.original_canvas.scan_dragto(event.x, event.y, gain=1)
            # 同步预览图的滚动位置
            orig_xview = self.original_canvas.xview()
            orig_yview = self.original_canvas.yview()
            self.preview_canvas.xview_moveto(orig_xview[0])
            self.preview_canvas.yview_moveto(orig_yview[0])
    
    def on_left_click_end(self, event):
        """左键释放结束拖拽"""
        self.dragging = False
    
    def on_preview_left_click_start(self, event):
        """预览图左键按下开始拖拽"""
        self.preview_dragging = True
        self.preview_canvas.scan_mark(event.x, event.y)
    
    def on_preview_left_click_drag(self, event):
        """预览图左键拖拽"""
        if self.preview_dragging:
            self.preview_canvas.scan_dragto(event.x, event.y, gain=1)
            # 同步原图的滚动位置
            preview_xview = self.preview_canvas.xview()
            preview_yview = self.preview_canvas.yview()
            self.original_canvas.xview_moveto(preview_xview[0])
            self.original_canvas.yview_moveto(preview_yview[0])
            # 重新绘制选择框（因为滚动位置改变了）
            self.draw_selected_regions()
    
    def on_preview_left_click_end(self, event):
        """预览图左键释放结束拖拽"""
        self.preview_dragging = False
    
    def on_mousewheel(self, event):
        """鼠标滚轮缩放"""
        # 如果右键正在选择区域，则不响应滚轮缩放
        if self.selecting:
            return
        
        # 获取鼠标位置（画布坐标）
        canvas_x = event.x
        canvas_y = event.y
        
        # 判断滚动方向
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            # 向上滚动 - 放大
            self.zoom_in(canvas_x, canvas_y)
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            # 向下滚动 - 缩小
            self.zoom_out(canvas_x, canvas_y)
        
    def confirm(self):
        """确认并应用"""
        # 返回选中的区域（每个区域的scope已经在右键菜单确认时设置好了）
        self.result_regions = self.selected_regions.copy()
        if self.doc:
            self.doc.close()
        self.dialog.destroy()
    
    def get_result(self):
        """获取选择结果"""
        return self.result_regions
        
    def switch_to_prev_file(self):
        """切换到上一个文件"""
        if self.current_file_index > 0:
            self.switch_to_file(self.current_file_index - 1)
    
    def switch_to_next_file(self):
        """切换到下一个文件"""
        if self.current_file_index < len(self.file_list) - 1:
            self.switch_to_file(self.current_file_index + 1)
    
    def switch_to_file(self, file_index):
        """切换到指定文件"""
        if file_index < 0 or file_index >= len(self.file_list):
            return
        
        # 关闭当前文档
        if self.doc:
            self.doc.close()
        
        # 切换到新文件
        self.current_file_index = file_index
        new_file_path = self.file_list[file_index]["path"]
        self.pdf_path = new_file_path
        
        # 打开新文档
        try:
            self.doc = fitz.open(new_file_path)
            self.total_pages = len(self.doc)
            self.current_page = 0
            self.zoom = 0.9  # 重置缩放
            
            # 更新标题
            self.update_title()
            
            # 更新文件切换按钮状态
            if len(self.file_list) > 1:
                self.update_file_switch_buttons()
            
            # 加载第一页
            self.load_page(0)
        except Exception as e:
            show_error(self.parent, f"无法打开PDF文件: {e}")
    
    def update_file_switch_buttons(self):
        """更新文件切换按钮状态"""
        if len(self.file_list) <= 1:
            return
        
        # 更新上一个文件按钮
        self.btn_prev_file.configure(state="normal" if self.current_file_index > 0 else "disabled")
        
        # 更新下一个文件按钮
        self.btn_next_file.configure(state="normal" if self.current_file_index < len(self.file_list) - 1 else "disabled")
        
        # 更新文件信息标签
        current_file = self.file_list[self.current_file_index]
        file_name = current_file.get("name", Path(current_file["path"]).name)
        self.file_info_label.configure(text=f"文件 {self.current_file_index + 1}/{len(self.file_list)}: {file_name}")
    
    def cancel(self):
        """取消"""
        if self.doc:
            self.doc.close()
        self.dialog.destroy()

