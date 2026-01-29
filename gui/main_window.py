"""主窗口模块"""
import customtkinter as ctk
from tkinter import filedialog, Label
from pathlib import Path
import config
import os
import subprocess
import platform
import webbrowser
from utils.window_utils import show_info, show_warning, show_error, ask_yesno, center_window


class MainWindow:
    def __init__(self):
        self.config = config.load_config()
        
        ctk.set_appearance_mode(self.config["theme"]["mode"])
        ctk.set_default_color_theme(self.config["theme"]["color_theme"])
        
        self.root = ctk.CTk()
        self.root.title("PDF批量去水印工具 V1.0版   原创作者：蓝胖子不胖")
        self.root.configure(fg_color="#8B7FFF")
        
        width = self.config["window"]["width"]
        height = self.config["window"]["height"]
        x = self.config["window"]["x"]
        y = self.config["window"]["y"]
        
        if x is not None and y is not None:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.root.geometry(f"{width}x{height}")
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        if self.config["window"]["maximized"]:
            self.root.state('zoomed')
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.file_list = []
        self.selected_regions = []
        self.text_to_remove = []
        self.text_input_widgets = []
        self.excluded_pages = ""
        self.file_checkboxes = {}
        self.file_status_labels = {}  # 存储文件状态标签引用 {file_path: status_label}
        self._status_update_pending = {}  # 待更新的状态 {file_path: status}
        
        self.create_ui()
        
    def create_ui(self):
        """创建UI界面"""
        self.root.configure(fg_color="#8B7FFF")
        
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True)
        
        self.create_toolbar(main_container)
        self.create_file_list_area(main_container)
        self.create_operation_panel(main_container)
        self.create_status_bar(main_container)
        
        self.root.after(50, self.create_gradient_background)
        
    def create_gradient_background(self):
        """创建渐变背景"""
        from tkinter import Canvas
        try:
            self.bg_canvas = Canvas(
                self.root,
                highlightthickness=0,
                borderwidth=0,
                bg="#8B7FFF"
            )
            self.bg_canvas.lower()
            self.bg_canvas.pack(fill="both", expand=True)
            
            self._gradient_draw_pending = False
            self._last_size = (0, 0)
            
            def on_configure(event=None):
                if hasattr(self, 'bg_canvas') and not self._gradient_draw_pending:
                    self._gradient_draw_pending = True
                    self.root.after(100, self._debounced_draw_gradient)
            
            self.root.bind("<Configure>", on_configure)
            self.root.after(200, self._draw_gradient)
        except:
            pass
    
    def _debounced_draw_gradient(self):
        """防抖绘制渐变背景"""
        self._gradient_draw_pending = False
        self._draw_gradient()
        
    def _draw_gradient(self, event=None):
        """绘制渐变背景"""
        try:
            if not hasattr(self, 'bg_canvas'):
                return
                
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            
            if width <= 1 or height <= 1:
                return
            
            if (width, height) == self._last_size:
                return
            
            self._last_size = (width, height)
            self.bg_canvas.delete("all")
            self.bg_canvas.config(width=width, height=height)
            
            start_color = (139, 127, 255)
            end_color = (91, 127, 255)
            
            step = max(10, height // 50)
            for i in range(0, height, step):
                ratio = i / height
                r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
                g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
                b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
                color = f"#{r:02x}{g:02x}{b:02x}"
                
                next_i = min(i + step, height)
                self.bg_canvas.create_rectangle(0, i, width, next_i, fill=color, outline=color)
        except:
            pass
        
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar_container = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=20, pady=(20, 20))
        
        toolbar_frame = ctk.CTkFrame(toolbar_container, fg_color=("white", "#FFFFFF"), height=70, corner_radius=10)
        toolbar_frame.pack(fill="x")
        toolbar_frame.pack_propagate(False)
        
        # 内部容器
        toolbar_inner = ctk.CTkFrame(toolbar_frame, fg_color=("white", "#FFFFFF"))
        toolbar_inner.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 左侧按钮组
        left_buttons = ctk.CTkFrame(toolbar_inner, fg_color=("white", "#FFFFFF"))
        left_buttons.pack(side="left")
        
        # 工具栏按钮 - 使用专业的蓝色
        self.btn_open = ctk.CTkButton(
            left_buttons,
            text="📂 打开文件",
            command=self.open_files,
            width=120,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        self.btn_open.pack(side="left", padx=(0, 8))
        
        # 打开文件夹按钮
        self.btn_open_folder = ctk.CTkButton(
            left_buttons,
            text="📁 打开文件夹",
            command=self.open_folder,
            width=120,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        self.btn_open_folder.pack(side="left", padx=(0, 8))
        
        self.btn_process_current = ctk.CTkButton(
            left_buttons,
            text="📄 处理选中文件",
            command=self.process_current_file,
            width=130,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white",
            state="disabled"
        )
        self.btn_process_current.pack(side="left", padx=(0, 8))
        
        self.btn_batch = ctk.CTkButton(
            left_buttons,
            text="📦 处理全部文件",
            command=self.batch_process,
            width=130,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            fg_color="#27AE60",
            hover_color="#229954",
            text_color="white"
        )
        self.btn_batch.pack(side="left", padx=(0, 8))
        
        # 右侧设置按钮（暂时隐藏，功能待实现）
        # self.btn_settings = ctk.CTkButton(
        #     toolbar_inner,
        #     text="⚙️ 设置",
        #     command=self.open_settings,
        #     width=100,
        #     height=38,
        #     font=ctk.CTkFont(size=13, weight="bold"),
        #     fg_color="#5B7FFF",
        #     hover_color="#4A6EE8",
        #     text_color="white"
        # )
        # self.btn_settings.pack(side="right", padx=(0, 0))
        
    def create_file_list_area(self, parent):
        """创建文件列表区域"""
        file_container = ctk.CTkFrame(parent, fg_color="transparent")
        file_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        file_frame = ctk.CTkFrame(file_container, fg_color=("white", "#FFFFFF"), corner_radius=10)
        file_frame.pack(fill="both", expand=True)
        
        # 内部容器
        file_inner = ctk.CTkFrame(file_frame, fg_color=("white", "#FFFFFF"))
        file_inner.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 标题和统计信息
        header_frame = ctk.CTkFrame(file_inner, fg_color=("white", "#FFFFFF"))
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="文件列表",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        )
        title_label.pack(side="left")
        
        # 清空文件列表按钮（右侧显示）
        btn_clear = ctk.CTkButton(
            header_frame,
            text="🗑️ 清空列表",
            command=self.clear_file_list,
            width=100,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white"
        )
        btn_clear.pack(side="right")
        
        # 文件列表表头
        header_frame = ctk.CTkFrame(file_inner, fg_color=("#E8EAF6", "#E8EAF6"), height=40, corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # 表头列（增加复选框列，删除路径列）
        header_labels = [
            ("", 30),  # 复选框列
            ("序号", 60),
            ("标题", 450),
            ("页数", 80),
            ("处理状态", 100),
            ("操作", 160)  # 增加宽度以容纳3个按钮
        ]
        
        for i, (text, width) in enumerate(header_labels):
            if i == 0:
                # 复选框列标题 - 添加点击事件实现全选
                checkbox_header = ctk.CTkCheckBox(
                    header_frame,
                    text="",
                    command=self.toggle_select_all,
                    width=20,
                    height=20
                )
                checkbox_header.pack(side="left", padx=(15, 10))
                self.header_checkbox = checkbox_header
            else:
                label = ctk.CTkLabel(
                    header_frame,
                    text=text,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#2C3E50",
                    width=width,
                    fg_color="transparent",
                    anchor="center"  # 居中对齐
                )
                if i == len(header_labels) - 1:
                    label.pack(side="right", padx=(10, 15))
                else:
                    label.pack(side="left", padx=(0, 10))
        
        # 文件列表容器（带滚动条）
        list_container = ctk.CTkScrollableFrame(file_inner, fg_color=("white", "#F8F9FA"))
        list_container.pack(fill="both", expand=True, pady=(0, 0))
        
        self.file_list_container = list_container
        
        # 提示信息
        self.file_list_hint = ctk.CTkLabel(
            list_container,
            text="提示: 点击\"打开文件\"或\"打开文件夹\"按钮添加PDF文件",
            font=ctk.CTkFont(size=13),
            text_color="#95A5A6"
        )
        self.file_list_hint.pack(pady=50)
        
    def create_operation_panel(self, parent):
        """创建操作面板区域"""
        panel_container = ctk.CTkFrame(parent, fg_color="transparent")
        panel_container.pack(fill="x", padx=20, pady=(0, 20))
        
        # 白色大面板
        panel_frame = ctk.CTkFrame(panel_container, fg_color=("white", "#FFFFFF"), height=360, corner_radius=10)
        panel_frame.pack(fill="x")
        panel_frame.pack_propagate(False)
        
        # 内部容器
        panel_inner = ctk.CTkFrame(panel_frame, fg_color=("white", "#FFFFFF"))
        panel_inner.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 使用三列布局，设置列间距
        panel_inner.grid_columnconfigure(0, weight=1, minsize=0)
        panel_inner.grid_columnconfigure(1, weight=1, minsize=0)
        panel_inner.grid_columnconfigure(2, weight=1, minsize=0)
        
        # 区域选择删除面板
        self.create_region_panel(panel_inner)
        
        # 文字删除面板
        self.create_text_panel(panel_inner)
        
        # 页面排除面板
        self.create_exclude_panel(panel_inner)
        
    def create_region_panel(self, parent):
        """创建区域选择面板"""
        # 创建阴影容器
        shadow_container = ctk.CTkFrame(parent, fg_color="transparent")
        shadow_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        # 阴影层（深色背景，稍微偏移）
        shadow_frame = ctk.CTkFrame(
            shadow_container,
            fg_color="#D0D0D0",
            corner_radius=8
        )
        shadow_frame.place(x=2, y=2, relwidth=1, relheight=1)
        
        # 主模块（白色，在阴影上方）- 使用pack布局确保子组件正常显示
        region_frame = ctk.CTkFrame(
            shadow_container, 
            fg_color=("white", "#FFFFFF"),
            border_width=1,
            border_color="#E0E0E0",
            corner_radius=8
        )
        region_frame.pack(fill="both", expand=True)
        
        # 标题行（标题和小标题在一行）
        title_frame = ctk.CTkFrame(region_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # 标题
        title = ctk.CTkLabel(
            title_frame,
            text="📐 区域选择删除",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50"
        )
        title.pack(side="left")
        
        # 已选区域标签（右侧显示）
        region_label = ctk.CTkLabel(
            title_frame,
            text=f"已选区域 ({len(self.selected_regions)}个):",
            font=ctk.CTkFont(size=12),
            text_color="#7F8C8D"
        )
        region_label.pack(side="right")
        self.region_count_label = region_label
        
        # 区域列表容器（使用ScrollableFrame，滚动条只在需要时显示）
        region_list_frame = ctk.CTkScrollableFrame(region_frame, height=200)
        region_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.region_list_container = region_list_frame
        
        # 按钮
        btn_frame = ctk.CTkFrame(region_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.btn_select_region = ctk.CTkButton(
            btn_frame,
            text="选择区域",
            command=self.select_region,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        self.btn_select_region.pack(side="left", padx=(0, 8))
        
        self.btn_clear_regions = ctk.CTkButton(
            btn_frame,
            text="清除全部",
            command=self.clear_all_regions,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white"
        )
        self.btn_clear_regions.pack(side="left", padx=(0, 0))
        
    def create_text_panel(self, parent):
        """创建文字删除面板"""
        # 创建阴影容器
        shadow_container = ctk.CTkFrame(parent, fg_color="transparent")
        shadow_container.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=10)
        
        # 阴影层（深色背景，稍微偏移）
        shadow_frame = ctk.CTkFrame(
            shadow_container,
            fg_color="#D0D0D0",
            corner_radius=8
        )
        shadow_frame.place(x=2, y=2, relwidth=1, relheight=1)
        
        # 主模块（白色，在阴影上方）- 使用pack布局确保子组件正常显示
        text_frame = ctk.CTkFrame(
            shadow_container, 
            fg_color=("white", "#FFFFFF"),
            border_width=1,
            border_color="#E0E0E0",
            corner_radius=8
        )
        text_frame.pack(fill="both", expand=True)
        
        # 标题行（标题和小标题在一行）
        title_frame = ctk.CTkFrame(text_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # 标题
        title = ctk.CTkLabel(
            title_frame,
            text="🗑️ 文字删除",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50"
        )
        title.pack(side="left")
        
        # 提示信息（右侧显示）
        hint_label = ctk.CTkLabel(
            title_frame,
            text="应用所有文件的所有页",
            font=ctk.CTkFont(size=11),
            text_color="#7F8C8D"
        )
        hint_label.pack(side="right")
        
        # 文字输入列表容器（可滚动）
        text_list_container = ctk.CTkScrollableFrame(text_frame, height=200)
        text_list_container.pack(fill="both", expand=True, padx=15, pady=(0, 5))
        self.text_list_container = text_list_container
        
        # 初始化文字输入列表
        self.text_input_widgets = []
        
        # 初始化时添加一个空行
        self.add_text_input_row()
        
        # 按钮容器（两个按钮放在一行）
        btn_frame = ctk.CTkFrame(text_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # 添加新行按钮
        btn_add_text = ctk.CTkButton(
            btn_frame,
            text="➕ 添加文字",
            command=self.add_text_input_row,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27AE60",
            hover_color="#229954",
            text_color="white"
        )
        btn_add_text.pack(side="left", padx=(0, 8))
        
        self.btn_remove_text_all = ctk.CTkButton(
            btn_frame,
            text="删除全部",
            command=self.remove_text_all,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        self.btn_remove_text_all.pack(side="left", padx=(0, 0))
        
    def create_exclude_panel(self, parent):
        """创建页面排除面板"""
        # 创建阴影容器
        shadow_container = ctk.CTkFrame(parent, fg_color="transparent")
        shadow_container.grid(row=0, column=2, sticky="nsew", padx=(10, 0), pady=10)
        
        # 阴影层（深色背景，稍微偏移）
        shadow_frame = ctk.CTkFrame(
            shadow_container,
            fg_color="#D0D0D0",
            corner_radius=8
        )
        shadow_frame.place(x=2, y=2, relwidth=1, relheight=1)
        
        # 主模块（白色，在阴影上方）- 使用pack布局确保子组件正常显示
        exclude_frame = ctk.CTkFrame(
            shadow_container, 
            fg_color=("white", "#FFFFFF"),
            border_width=1,
            border_color="#E0E0E0",
            corner_radius=8
        )
        exclude_frame.pack(fill="both", expand=True)
        
        # 标题行（标题和小标题在一行）
        title_frame = ctk.CTkFrame(exclude_frame, fg_color=("white", "#FFFFFF"))
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # 标题
        title = ctk.CTkLabel(
            title_frame,
            text="📋 页面排除",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50"
        )
        title.pack(side="left")
        
        # 输入提示（右侧显示）
        input_label = ctk.CTkLabel(
            title_frame,
            text="排除页面:",
            font=ctk.CTkFont(size=12),
            text_color="#7F8C8D"
        )
        input_label.pack(side="right")
        
        # 页面输入框（增大高度）
        self.page_exclude_input = ctk.CTkEntry(
            exclude_frame,
            placeholder_text="例如: 1-5, 10, 15-20",
            font=ctk.CTkFont(size=12),
            height=40
        )
        self.page_exclude_input.pack(fill="x", padx=15, pady=(0, 15))
        
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_container = ctk.CTkFrame(parent, fg_color="transparent")
        status_container.pack(fill="x", padx=20, pady=(0, 20))
        
        status_frame = ctk.CTkFrame(status_container, fg_color=("white", "#FFFFFF"), height=50, corner_radius=10)
        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="就绪 | 共 0 个文件 | 已选 0 个区域",
            font=ctk.CTkFont(size=12),
            text_color="#7F8C8D"
        )
        self.status_label.pack(side="left", padx=25, pady=15)
        
        # 版权信息（右侧）
        github_url = "https://github.com/zjm18023/pdf-watermark-remover"
        copyright_text = "原创作者：蓝胖子不胖       Github地址："
        
        # Github链接（可点击）- 先pack，显示在最右边
        def open_github_link(event):
            webbrowser.open(github_url)
        
        github_link_label = Label(
            status_frame,
            text=github_url,
            fg="#5B7FFF",
            font=("Arial", 10, "underline"),
            cursor="hand2",
            bg="white"
        )
        github_link_label.pack(side="right", padx=(0, 25), pady=15)
        github_link_label.bind("<Button-1>", open_github_link)
        
        # 文本部分 - 后pack，显示在链接左边
        self.copyright_label = ctk.CTkLabel(
            status_frame,
            text=copyright_text,
            font=ctk.CTkFont(size=10),
            text_color="black"
        )
        self.copyright_label.pack(side="right", padx=(0, 5), pady=15)
        
    def open_files(self):
        """打开文件"""
        files = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if files:
            for file_path in files:
                self.add_file(file_path)
            self.update_file_list_display()
            self.update_status()
    
    def open_folder(self):
        """打开文件夹并获取所有PDF文件"""
        folder_path = filedialog.askdirectory(title="选择文件夹")
        if folder_path:
            try:
                from pathlib import Path
                folder = Path(folder_path)
                pdf_files = list(folder.glob("*.pdf"))
                
                if not pdf_files:
                    show_info(self.root, "该文件夹中没有PDF文件", "提示")
                    return
                
                for pdf_file in pdf_files:
                    self.add_file(str(pdf_file))
                
                self.update_file_list_display()
                self.update_status()
                
                show_info(self.root, f"已添加 {len(pdf_files)} 个PDF文件", "成功")
            except Exception as e:
                show_error(self.root, f"打开文件夹失败: {e}")
            
    def add_file(self, file_path):
        """添加文件到列表"""
        if file_path not in [f["path"] for f in self.file_list]:
            # 获取PDF页数
            page_count = self.get_pdf_page_count(file_path)
            
            self.file_list.append({
                "path": file_path,
                "name": Path(file_path).name,
                "page_count": page_count,
                "status": "待处理"  # 处理状态：待处理、处理中、已完成、失败
            })
            
    def get_pdf_page_count(self, file_path):
        """获取PDF文件页数"""
        try:
            import fitz
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            print(f"获取PDF页数失败: {e}")
            return "未知"
            
    def update_file_list_display(self):
        """更新文件列表显示"""
        if not hasattr(self, 'file_list_container'):
            return
        
        for widget in self.file_list_container.winfo_children():
            widget.destroy()
        
        self.file_status_labels.clear()
            
        if not self.file_list:
            self.file_list_hint = ctk.CTkLabel(
                self.file_list_container,
                text="提示: 点击\"打开文件\"按钮添加PDF文件",
                font=ctk.CTkFont(size=12),
                text_color="#7F8C8D"
            )
            self.file_list_hint.pack(pady=50)
            return
            
        self.file_checkboxes = {}
        
        if hasattr(self, 'header_checkbox'):
            self.header_checkbox.deselect()
        
        for idx, file_info in enumerate(self.file_list):
            file_item = self.create_file_item(file_info, idx)
            file_item.pack(fill="x", padx=5, pady=0)
        
        if self.file_list:
            self.btn_process_current.configure(state="normal")
            self.btn_batch.configure(state="normal")
        else:
            self.btn_process_current.configure(state="disabled")
            self.btn_batch.configure(state="disabled")
            
    def create_file_item(self, file_info, index):
        """创建文件列表项"""
        item_frame = ctk.CTkFrame(self.file_list_container, fg_color=("white", "#FFFFFF"), height=42)
        item_frame.pack(fill="x", padx=5, pady=0)
        item_frame.pack_propagate(False)
        
        # 复选框列
        checkbox_var = ctk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(
            item_frame,
            text="",
            variable=checkbox_var,
            width=20,
            height=20,
            command=self.update_header_checkbox  # 当复选框状态改变时更新表头复选框
        )
        checkbox.pack(side="left", padx=(10, 5), pady=8)
        self.file_checkboxes[index] = checkbox_var
        
        # 序号列 - 居中对齐
        index_label = ctk.CTkLabel(
            item_frame,
            text=str(index + 1),
            font=ctk.CTkFont(size=12),
            anchor="center",  # 居中对齐
            width=60
        )
        index_label.pack(side="left", padx=(0, 10), pady=8)
        
        # 标题列（文件名）- 居中对齐
        title_label = ctk.CTkLabel(
            item_frame,
            text=f"📄 {file_info['name']}",
            font=ctk.CTkFont(size=12),
            anchor="center",  # 居中对齐
            width=450
        )
        title_label.pack(side="left", padx=(0, 10), pady=8)
        
        # 页数列 - 居中对齐
        page_count = file_info.get('page_count', '未知')
        page_label = ctk.CTkLabel(
            item_frame,
            text=f"{page_count}页" if isinstance(page_count, int) else page_count,
            font=ctk.CTkFont(size=11),
            text_color="#2C3E50",
            anchor="center",  # 居中对齐
            width=80
        )
        page_label.pack(side="left", padx=(0, 10), pady=8)
        
        # 处理状态列 - 居中对齐
        status = file_info.get('status', '待处理')
        status_colors = {
            '待处理': '#7F8C8D',
            '处理中': '#3498DB',
            '已完成': '#27AE60',
            '失败': '#E74C3C'
        }
        status_color = status_colors.get(status, '#7F8C8D')
        status_label = ctk.CTkLabel(
            item_frame,
            text=status,
            font=ctk.CTkFont(size=11),
            text_color=status_color,
            anchor="center",
            width=100
        )
        status_label.pack(side="left", padx=(0, 5), pady=8)
        
        # 保存状态标签引用，用于后续更新
        file_path = file_info.get("path")
        if file_path:
            self.file_status_labels[file_path] = status_label
        
        # 操作列（按钮）
        action_frame = ctk.CTkFrame(item_frame, fg_color=("white", "#FFFFFF"))
        action_frame.pack(side="right", padx=(0, 10), pady=8)
        
        btn_view = ctk.CTkButton(
            action_frame,
            text="查看",
            command=lambda idx=index: self.view_file_in_browser(idx),
            width=45,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        btn_view.pack(side="left", padx=(0, 5))
        
        btn_open_folder = ctk.CTkButton(
            action_frame,
            text="文件夹",
            command=lambda idx=index: self.open_file_folder(idx),
            width=45,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27AE60",
            hover_color="#229954",
            text_color="white"
        )
        btn_open_folder.pack(side="left", padx=(0, 5))
        
        btn_delete = ctk.CTkButton(
            action_frame,
            text="删除",
            command=lambda idx=index: self.remove_file(idx),
            width=45,
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white"
        )
        btn_delete.pack(side="left", padx=(0, 0))
        
        return item_frame
    
    def update_file_status(self, file_path, status):
        """更新文件处理状态（优化：只更新状态标签，不重建整个列表）"""
        for file_info in self.file_list:
            if file_info["path"] == file_path:
                file_info["status"] = status
                break
        
        # 如果状态标签存在，直接更新，避免重建整个列表
        if file_path in self.file_status_labels:
            status_label = self.file_status_labels[file_path]
            status_colors = {
                '待处理': '#7F8C8D',
                '处理中': '#3498DB',
                '已完成': '#27AE60',
                '失败': '#E74C3C'
            }
            status_color = status_colors.get(status, '#7F8C8D')
            status_label.configure(text=status, text_color=status_color)
        else:
            # 如果标签不存在，重建列表（首次加载时）
            self.update_file_list_display()
        
    def remove_file(self, index):
        """从列表中删除文件（优化：平滑删除，减少闪烁）"""
        if 0 <= index < len(self.file_list):
            # 获取要删除的文件路径
            file_path = self.file_list[index]["path"]
            
            # 先隐藏要删除的widget（平滑过渡）
            widgets = list(self.file_list_container.winfo_children())
            if index < len(widgets):
                widget = widgets[index]
                # 逐渐隐藏（可选，如果支持动画）
                widget.pack_forget()
                # 立即销毁
                widget.destroy()
            
            # 从列表中删除
            self.file_list.pop(index)
            
            # 从状态标签字典中删除
            if file_path in self.file_status_labels:
                del self.file_status_labels[file_path]
            
            # 更新复选框字典（重新索引）
            new_checkboxes = {}
            for old_idx, checkbox_var in self.file_checkboxes.items():
                if old_idx < index:
                    new_checkboxes[old_idx] = checkbox_var
                elif old_idx > index:
                    new_checkboxes[old_idx - 1] = checkbox_var
            self.file_checkboxes = new_checkboxes
            
            # 更新剩余项的序号和按钮命令
            remaining_widgets = list(self.file_list_container.winfo_children())
            for new_idx, widget in enumerate(remaining_widgets):
                if new_idx >= index:  # 只更新被删除项之后的项
                    # 更新序号标签
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkLabel):
                            try:
                                if child.cget("width") == 60:  # 序号列
                                    child.configure(text=str(new_idx + 1))
                                    break
                            except:
                                pass
                    
                    # 更新按钮命令（使用functools.partial避免闭包问题）
                    from functools import partial
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkFrame):
                            for btn in child.winfo_children():
                                if isinstance(btn, ctk.CTkButton):
                                    btn_text = btn.cget("text")
                                    if btn_text == "查看":
                                        btn.configure(command=partial(self.view_file_in_browser, new_idx))
                                    elif btn_text == "文件夹":
                                        btn.configure(command=partial(self.open_file_folder, new_idx))
                                    elif btn_text == "删除":
                                        btn.configure(command=partial(self.remove_file, new_idx))
            
            # 如果列表为空，显示提示
            if not self.file_list:
                self.file_list_hint = ctk.CTkLabel(
                    self.file_list_container,
                    text="提示: 拖拽PDF文件到此处或点击\"打开文件\"按钮",
                    font=ctk.CTkFont(size=12),
                    text_color="#7F8C8D"
                )
                self.file_list_hint.pack(pady=50)
            
            # 更新按钮状态
            if self.file_list:
                self.btn_process_current.configure(state="normal")
                self.btn_batch.configure(state="normal")
            else:
                self.btn_process_current.configure(state="disabled")
                self.btn_batch.configure(state="disabled")
            
            self.update_status()
    
    def open_file_folder(self, index):
        """打开文件所在文件夹"""
        if 0 <= index < len(self.file_list):
            file_path = self.file_list[index]["path"]
            folder_path = str(Path(file_path).parent)
            if os.path.exists(folder_path):
                try:
                    system = platform.system()
                    if system == "Windows":
                        os.startfile(folder_path)
                    elif system == "Darwin":  # macOS
                        subprocess.run(["open", folder_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_path])
                except Exception as e:
                    show_error(self.root, f"无法打开文件夹: {e}")
            else:
                show_error(self.root, "文件夹不存在")
    
    def clear_file_list(self):
        """清空文件列表"""
        if not self.file_list:
            show_info(self.root, "文件列表已经是空的", "提示")
            return
        
        if ask_yesno(self.root, "确定要清空文件列表吗？"):
            self.file_list = []
            self.file_checkboxes = {}
            self.selected_regions = []  # 同时清空已选择的区域
            self.update_file_list_display()
            self.update_region_display()
            self.update_status()
            
    def view_file_with_default_app(self, index):
        """使用系统默认工具打开文件"""
        if 0 <= index < len(self.file_list):
            file_path = self.file_list[index]["path"]
            if os.path.exists(file_path):
                try:
                    system = platform.system()
                    if system == "Windows":
                        os.startfile(file_path)
                    elif system == "Darwin":  # macOS
                        subprocess.run(["open", file_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", file_path])
                except Exception as e:
                    show_error(self.root, f"无法打开文件: {e}")
            else:
                show_error(self.root, "文件不存在")
    
    def view_file(self, index):
        """查看文件（保留原方法，用于右键菜单）"""
        self.view_file_with_default_app(index)
    
    def view_file_in_browser(self, index):
        """使用浏览器打开PDF文件"""
        if 0 <= index < len(self.file_list):
            file_path = self.file_list[index]["path"]
            if os.path.exists(file_path):
                try:
                    import webbrowser
                    # 将文件路径转换为 file:// URL
                    file_url = Path(file_path).as_uri()
                    webbrowser.open(file_url)
                except Exception as e:
                    show_error(self.root, f"无法在浏览器中打开文件: {e}")
            else:
                show_error(self.root, "文件不存在")
            
    def select_region(self):
        """选择区域"""
        if not self.file_list:
            show_warning(self.root, "请先添加PDF文件")
            return
        
        # 确定当前文件索引（如果有选中的文件，使用第一个选中的；否则使用第一个文件）
        current_file_index = 0
        selected_indices = []
        for idx, checkbox_var in self.file_checkboxes.items():
            if checkbox_var.get():
                selected_indices.append(idx)
        
        if selected_indices:
            current_file_index = selected_indices[0]
        
        # 打开区域选择弹窗，传递文件列表、当前文件索引和已选择的区域
        from gui.region_dialog import RegionDialog
        dialog = RegionDialog(
            self.root, 
            self.file_list[current_file_index]["path"],
            file_list=self.file_list,
            current_file_index=current_file_index,
            existing_regions=self.selected_regions  # 传递已选择的区域
        )
        self.root.wait_window(dialog.dialog)
        
        # 获取选择的区域
        result_regions = dialog.get_result()
        if result_regions:
            # 替换区域列表（转换格式以适配主窗口显示）
            self.selected_regions = []
            for region in result_regions:
                scope = region.get("scope", "current")
                scope_text = {
                    "current": "当前页",
                    "all_pages": "当前文件全部页",
                    "all_files": "所有文件所有页"
                }.get(scope, "当前页")
                
                region_info = {
                    "rect": region["rect"],
                    "page": region.get("page", 0),
                    "scope": scope,
                    "pages": scope_text,
                    "file_index": region.get("file_index", current_file_index)  # 保存文件索引
                }
                self.selected_regions.append(region_info)
            
            self.update_region_display()
            self.update_status()
        
    def clear_all_regions(self):
        """清除所有区域"""
        self.selected_regions = []
        self.update_region_display()
        self.update_status()
        
    def update_region_display(self):
        """更新区域显示"""
        # 清除现有区域显示
        for widget in self.region_list_container.winfo_children():
            widget.destroy()
            
        # 显示区域列表
        for idx, region in enumerate(self.selected_regions):
            region_item = self.create_region_item(region, idx)
            region_item.pack(fill="x", padx=5, pady=3)
            
        # 更新计数
        self.region_count_label.configure(
            text=f"已选区域 ({len(self.selected_regions)}个):"
        )
        
    def create_region_item(self, region, index):
        """创建区域列表项"""
        item_frame = ctk.CTkFrame(self.region_list_container, fg_color=("white", "#F8F9FA"))
        
        # 区域信息
        info_text = f"区域{index+1}"
        if "pages" in region:
            info_text += f" - {region['pages']}"
        info_label = ctk.CTkLabel(
            item_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        info_label.pack(side="left", padx=10, pady=5)
        
        # 删除按钮
        btn_delete = ctk.CTkButton(
            item_frame,
            text="删除",
            command=lambda idx=index: self.remove_region(idx),
            width=60,
            height=20,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white"
        )
        btn_delete.pack(side="right", padx=5)
        
        return item_frame
        
    def remove_region(self, index):
        """移除区域"""
        if 0 <= index < len(self.selected_regions):
            self.selected_regions.pop(index)
            self.update_region_display()
            self.update_status()
            
    def add_text_input_row(self, initial_text=""):
        """添加一行文字输入框"""
        row_frame = ctk.CTkFrame(self.text_list_container, fg_color="transparent")
        row_frame.pack(fill="x", padx=5, pady=3)
        
        # 文字输入框
        text_entry = ctk.CTkEntry(
            row_frame,
            placeholder_text="输入要删除的文字",
            font=ctk.CTkFont(size=12),
            height=32
        )
        if initial_text:
            text_entry.insert(0, initial_text)
        text_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # 删除按钮
        btn_delete = ctk.CTkButton(
            row_frame,
            text="❌",
            command=lambda: self.remove_text_input_row(row_frame),
            width=32,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white"
        )
        btn_delete.pack(side="right")
        
        # 保存引用
        self.text_input_widgets.append({
            "frame": row_frame,
            "entry": text_entry
        })
    
    def remove_text_input_row(self, row_frame):
        """删除一行文字输入框"""
        # 从列表中移除
        self.text_input_widgets = [
            item for item in self.text_input_widgets 
            if item["frame"] != row_frame
        ]
        # 销毁组件
        row_frame.destroy()
    
    def get_text_to_remove_list(self):
        """获取所有要删除的文字列表"""
        text_list = []
        for item in self.text_input_widgets:
            text = item["entry"].get().strip()
            if text:
                text_list.append(text)
        return text_list
    
    def remove_text_current(self):
        """删除当前文件文字"""
        text_list = self.get_text_to_remove_list()
        
        if not text_list:
            show_warning(self.root, "请输入要删除的文字")
            return
        
        if not self.file_list:
            show_warning(self.root, "请先添加PDF文件")
            return
        
        # 处理第一个文件
        file_path = self.file_list[0]["path"]
        try:
            from core.pdf_handler import PDFHandler
            from core.watermark_remover import WatermarkRemover
            from utils.page_parser import parse_page_range
            
            # 获取排除页面
            excluded_pages = parse_page_range(self.page_exclude_input.get())
            
            with PDFHandler(file_path) as handler:
                remover = WatermarkRemover(handler)
                # 文字删除应用到所有文件的所有页，不受排除页限制
                remover.remove_text(text_list, excluded_pages=None)
                
                # 保存文件
                from utils.file_utils import get_output_path
                output_path = get_output_path(file_path)
                handler.save(output_path, optimize=True)
            
            show_info(self.root, f"文字删除完成！\n输出文件: {output_path}", "成功")
            self.text_to_remove = text_list
            
        except Exception as e:
            show_error(self.root, f"删除文字失败: {e}")
        
    def remove_text_all(self):
        """删除所有文件文字"""
        text_list = self.get_text_to_remove_list()
        
        if not text_list:
            show_warning(self.root, "请输入要删除的文字")
            return
        
        if not self.file_list:
            show_warning(self.root, "请先添加PDF文件")
            return
        
        self.text_to_remove = text_list
        show_info(self.root, "将在批量处理时应用文字删除")
        
    def process_current_file(self):
        """处理选中的文件"""
        if not self.file_list:
            show_warning(self.root, "没有可处理的文件")
            return
        
        selected_indices = []
        for idx, checkbox_var in self.file_checkboxes.items():
            if checkbox_var.get():
                selected_indices.append(idx)
        
        if not selected_indices:
            show_warning(self.root, "请先选择要处理的文件（勾选复选框）")
            return
        
        # 如果只选中一个文件，直接处理
        if len(selected_indices) == 1:
            self.process_single_file(selected_indices[0])
        else:
            # 多个文件，使用批量处理
            selected_files = [self.file_list[idx] for idx in selected_indices]
            self.batch_process_selected(selected_files)
    
    def process_single_file(self, index):
        """处理单个文件"""
        if not self.file_list or index < 0 or index >= len(self.file_list):
            show_warning(self.root, "文件索引无效")
            return
        
        file_path = self.file_list[index]["path"]
        file_name = self.file_list[index]["name"]
        
        # 更新文件状态为"处理中"
        self.update_file_status(file_path, "处理中")
        
        try:
            from core.pdf_handler import PDFHandler
            from core.watermark_remover import WatermarkRemover
            from utils.page_parser import parse_page_range
            from utils.file_utils import get_output_path, get_file_size
            
            excluded_pages = parse_page_range(self.page_exclude_input.get())
            
            with PDFHandler(file_path) as handler:
                remover = WatermarkRemover(handler)
                
                # 应用区域删除
                if self.selected_regions:
                    remover.remove_regions(self.selected_regions, excluded_pages, mode="actual")
                
                # 应用文字删除（从输入框获取最新列表）
                # 文字删除应用到所有文件的所有页，不受排除页限制
                text_list = self.get_text_to_remove_list()
                if text_list:
                    remover.remove_text(text_list, excluded_pages=None)
                
                # 保存文件
                output_path = get_output_path(file_path)
                handler.save(output_path, optimize=True)
                
                # 获取文件大小
                input_size = get_file_size(file_path)
                output_size = get_file_size(output_path)
            
            self.update_file_status(file_path, "已完成")
            
            show_info(
                self.root,
                f"文件处理完成！\n\n文件: {file_name}\n输出文件: {output_path}\n文件大小: {input_size}MB → {output_size}MB",
                "处理成功"
            )
            
        except Exception as e:
            self.update_file_status(file_path, "失败")
            show_error(self.root, f"文件处理失败: {e}", "处理失败")
        
    def toggle_select_all(self):
        """全选/取消全选（通过表头复选框触发）"""
        if not self.file_checkboxes:
            return
        
        # 获取表头复选框状态
        if hasattr(self, 'header_checkbox'):
            new_state = self.header_checkbox.get()
        else:
            # 如果没有表头复选框，检查是否全部选中
            all_selected = all(var.get() for var in self.file_checkboxes.values())
            new_state = not all_selected
        
        # 设置所有复选框状态
        for var in self.file_checkboxes.values():
            var.set(new_state)
    
    def update_header_checkbox(self):
        """更新表头复选框状态（根据所有文件复选框状态）"""
        if not hasattr(self, 'header_checkbox') or not self.file_checkboxes:
            return
        
        # 检查是否全部选中
        all_selected = all(var.get() for var in self.file_checkboxes.values())
        if all_selected:
            self.header_checkbox.select()
        else:
            self.header_checkbox.deselect()
    
    def batch_process_selected(self, selected_files):
        """批量处理选中的文件"""
        if not selected_files:
            return
        
        # 获取排除页面
        excluded_pages_str = self.page_exclude_input.get()
        
        # 更新文字列表（从输入框获取）
        self.text_to_remove = self.get_text_to_remove_list()
        
        # 打开批量处理弹窗
        from gui.process_log_dialog import ProcessLogDialog
        dialog = ProcessLogDialog(
            self.root, 
            selected_files,
            regions=self.selected_regions,
            text_to_remove=self.text_to_remove,
            excluded_pages=excluded_pages_str,
            main_window=self  # 传递主窗口引用
        )
        self.root.wait_window(dialog.dialog)
    
    def batch_process(self):
        """批量处理所有文件"""
        if not self.file_list:
            show_warning(self.root, "请先添加PDF文件")
            return
        
        # 获取排除页面
        excluded_pages_str = self.page_exclude_input.get()
        
        # 更新文字列表（从输入框获取）
        self.text_to_remove = self.get_text_to_remove_list()
        
        # 打开批量处理弹窗
        from gui.process_log_dialog import ProcessLogDialog
        dialog = ProcessLogDialog(
            self.root, 
            self.file_list,
            regions=self.selected_regions,
            text_to_remove=self.text_to_remove,
            excluded_pages=excluded_pages_str,
            main_window=self  # 传递主窗口引用
        )
        self.root.wait_window(dialog.dialog)
        
    def view_pdf(self):
        """查看PDF"""
        if not self.file_list:
            show_warning(self.root, "请先添加PDF文件")
            return
        from gui.pdf_viewer import PDFViewer
        pdf_path = self.file_list[0]["path"]
        viewer = PDFViewer(self.root, pdf_path)
        
    def open_settings(self):
        """打开设置"""
        show_info(self.root, "设置功能待实现")
        
    def update_status(self):
        """更新状态栏"""
        file_count = len(self.file_list)
        region_count = len(self.selected_regions)
        self.status_label.configure(
            text=f"就绪 | 共 {file_count} 个文件 | 已选 {region_count} 个区域"
        )
        
    def on_closing(self):
        """窗口关闭事件"""
        # 保存窗口配置
        if not self.root.state() == 'zoomed':
            self.config["window"]["width"] = self.root.winfo_width()
            self.config["window"]["height"] = self.root.winfo_height()
            self.config["window"]["x"] = self.root.winfo_x()
            self.config["window"]["y"] = self.root.winfo_y()
        self.config["window"]["maximized"] = (self.root.state() == 'zoomed')
        config.save_config(self.config)
        
        self.root.destroy()
    
    def run(self):
        """运行主窗口"""
        self.root.mainloop()

