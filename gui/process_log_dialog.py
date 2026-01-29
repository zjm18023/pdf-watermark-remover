"""批量处理日志弹窗"""
import customtkinter as ctk
from tkinter import Text, Scrollbar
import threading
import time
from pathlib import Path
import os
import subprocess
import platform
from utils.window_utils import show_error, show_warning, center_window


class ProcessLogDialog:
    def __init__(self, parent, file_list, regions=None, text_to_remove=None, excluded_pages="", main_window=None):
        self.parent = parent
        self.file_list = file_list
        self.regions = regions or []
        self.text_to_remove = text_to_remove or []
        self.excluded_pages = excluded_pages
        self.main_window = main_window  # 保存主窗口引用，用于更新文件状态
        self.is_processing = False
        self.is_paused = False
        self.is_stopped = False
        self.process_thread = None
        self.output_dir = None
        self.processed_files = {}
        self._log_queue = []
        self._log_update_scheduled = False
        
        self.stats = {
            "success": 0,
            "failed": 0,
            "processing": 0,
            "waiting": len(file_list)
        }
        
        # 创建弹窗
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"批量处理进度 - 正在处理 {len(file_list)} 个文件")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)  # 允许调整大小
        self.dialog.minsize(1000, 700)  # 设置最小尺寸
        
        center_window(self.dialog, 1000, 700)
        
        # 创建UI
        self.create_ui()
        
        # 强制更新窗口以确保所有组件正确渲染
        self.dialog.update_idletasks()
        self.dialog.update()
        
        # 记录初始位置并禁止移动
        self._original_geometry = self.dialog.geometry()
        self._lock_position()
        
        # 开始处理
        self.start_processing()
    
    def _lock_position(self):
        """锁定窗口位置（处理过程中不允许移动）"""
        if self._original_geometry:
            # 绑定配置事件，阻止窗口移动
            def prevent_move(event=None):
                if self.is_processing and self._original_geometry:
                    try:
                        current_geom = self.dialog.geometry()
                        if current_geom != self._original_geometry:
                            self.dialog.geometry(self._original_geometry)
                    except:
                        pass
            
            self.dialog.bind("<Configure>", prevent_move)
        
    def create_ui(self):
        """创建UI界面"""
        # 主容器 - 使用浅色背景
        main_container = ctk.CTkFrame(self.dialog, fg_color=("white", "#F5F7FA"))
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 处理进度区域
        self.create_progress_panel(main_container)
        
        # 处理日志区域
        self.create_log_panel(main_container)
        
        # 处理统计区域
        self.create_stats_panel(main_container)
        
        # 操作按钮
        self.create_action_buttons(main_container)
        
    def create_progress_panel(self, parent):
        """创建进度显示面板"""
        progress_frame = ctk.CTkFrame(parent, fg_color=("white", "#FFFFFF"))
        progress_frame.pack(fill="x", pady=(0, 10))
        
        # 标题
        title_label = ctk.CTkLabel(
            progress_frame,
            text="处理进度",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 10))
        self.progress_bar.set(0)
        
        # 进度文本
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="0% (0/0)",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(anchor="w", padx=15, pady=(0, 15))
        
        # 当前文件信息
        self.current_file_label = ctk.CTkLabel(
            progress_frame,
            text="等待开始...",
            font=ctk.CTkFont(size=11),
            text_color="#7F8C8D"
        )
        self.current_file_label.pack(anchor="w", padx=15, pady=(0, 15))
        
    def create_log_panel(self, parent):
        """创建日志显示面板"""
        log_frame = ctk.CTkFrame(parent, fg_color=("white", "#FFFFFF"))
        log_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 标题和操作按钮
        header_frame = ctk.CTkFrame(log_frame, fg_color=("white", "#FFFFFF"))
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="处理日志",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(side="left")
        
        # 日志显示区域（使用标准Text组件以支持更好的格式化）
        log_container = ctk.CTkFrame(log_frame, fg_color=("white", "#FFFFFF"))
        log_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # 使用标准Tkinter Text组件
        from tkinter import Text, Scrollbar, Frame
        # 创建一个内部Frame来放置Text和Scrollbar
        text_frame = Frame(log_container)
        text_frame.pack(fill="both", expand=True)
        
        self.log_text = Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#1e1e1e" if ctk.get_appearance_mode() == "dark" else "#ffffff",
            fg="#ffffff" if ctk.get_appearance_mode() == "dark" else "#000000",
            insertbackground="#ffffff" if ctk.get_appearance_mode() == "dark" else "#000000"
        )
        
        log_scrollbar = Scrollbar(
            text_frame,
            orient="vertical",
            command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # 使用pack布局
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # 配置文本标签颜色
        self.log_text.tag_config("success", foreground="#28a745")
        self.log_text.tag_config("error", foreground="#dc3545")
        self.log_text.tag_config("warning", foreground="#ffc107")
        self.log_text.tag_config("info", foreground="#17a2b8")
        self.log_text.tag_config("waiting", foreground="#6c757d")
        
        # 文件卡片容器
        self.file_cards = {}
        
    def create_stats_panel(self, parent):
        """创建统计信息面板"""
        stats_frame = ctk.CTkFrame(parent, fg_color=("white", "#F8F9FA"))
        stats_frame.pack(fill="x", pady=(0, 10))
        
        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="成功: 0  失败: 0  进行中: 0  等待: 0",
            font=ctk.CTkFont(size=12)
        )
        self.stats_label.pack(padx=15, pady=15)
        
    def create_action_buttons(self, parent):
        """创建操作按钮"""
        btn_frame = ctk.CTkFrame(parent, fg_color=("white", "#F8F9FA"))
        btn_frame.pack(fill="x")
        
        self.btn_pause = ctk.CTkButton(
            btn_frame,
            text="⏸️ 暂停",
            command=self.toggle_pause,
            width=100,
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        self.btn_pause.pack(side="left", padx=15, pady=15)
        
        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹️ 停止",
            command=self.stop_processing,
            width=100,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="white"
        )
        self.btn_stop.pack(side="left", padx=15, pady=15)
        
    def start_processing(self):
        """开始处理"""
        self.is_processing = True
        self.process_thread = threading.Thread(target=self.process_files, daemon=True)
        self.process_thread.start()
        
    def process_files(self):
        """处理文件（在后台线程中运行）"""
        total_files = len(self.file_list)
        
        # 获取处理参数（从父窗口传递）
        regions = getattr(self, 'regions', [])
        text_to_remove = getattr(self, 'text_to_remove', [])
        excluded_pages_str = getattr(self, 'excluded_pages', "")
        
        for idx, file_info in enumerate(self.file_list):
            if self.is_stopped:
                break
                
            # 等待暂停恢复
            while self.is_paused and not self.is_stopped:
                time.sleep(0.1)
                
            if self.is_stopped:
                break
                
            file_path = file_info["path"]
            file_name = file_info["name"]
            
            self.update_current_file(f"{file_name} (第 {idx + 1} 个 / 共 {total_files} 个)")
            self.create_file_card(file_name, "processing")
            
            if self.main_window:
                self.dialog.after_idle(lambda fp=file_path: self.main_window.update_file_status(fp, "处理中"))
            
            self.stats["waiting"] = max(0, self.stats["waiting"] - 1)
            self.stats["processing"] = 1
            self.update_stats()
            
            try:
                from core.pdf_handler import PDFHandler
                from core.watermark_remover import WatermarkRemover
                from utils.page_parser import parse_page_range
                from utils.file_utils import get_output_path
                
                # 添加日志
                self.add_log_to_card(file_name, "✅ 开始处理...", "success")
                
                excluded_pages = parse_page_range(excluded_pages_str)
                
                with PDFHandler(file_path) as handler:
                    remover = WatermarkRemover(handler)
                    
                    # 应用区域删除（根据区域的应用范围智能过滤）
                    region_count = 0
                    if regions:
                        file_regions = []
                        current_file_index = idx  # 当前处理的文件索引
                        
                        for region in regions:
                            scope = region.get("scope", "current")
                            region_file_index = region.get("file_index", 0)  # 区域所属的文件索引
                            region_page = region.get("page", 0)  # 区域所属的页面索引
                            
                            # 根据应用范围判断是否应该应用到当前文件
                            should_apply = False
                            
                            if scope == "all_files":
                                # 所有文件所有页：应用到所有文件
                                should_apply = True
                            elif scope == "all_pages":
                                # 当前文件所有页：只在区域所属的文件时应用
                                should_apply = (region_file_index == current_file_index)
                            elif scope == "current":
                                # 当前页：只在区域所属的文件时应用
                                # remove_regions 会根据 region_page 只应用到对应页面
                                should_apply = (region_file_index == current_file_index)
                            
                            if should_apply:
                                file_regions.append(region)
                                region_count += 1
                        
                        if file_regions:
                            remover.remove_regions(file_regions, excluded_pages, mode="actual")
                            self.add_log_to_card(file_name, f"✅ 应用区域删除: {region_count}个区域", "success")
                    
                    # 应用文字删除（文字删除应用到所有文件的所有页，不受排除页限制）
                    if text_to_remove:
                        text_match_counts = remover.remove_text(text_to_remove, excluded_pages=None)
                        
                        # 显示每个文字的匹配数量
                        if text_match_counts:
                            self.add_log_to_card(file_name, "✅ 应用文字删除:", "success")
                            for text, count in text_match_counts.items():
                                if count > 0:
                                    self.add_log_to_card(file_name, f"   • \"{text}\": 匹配到 {count} 处", "info")
                                else:
                                    self.add_log_to_card(file_name, f"   • \"{text}\": 未匹配到", "warning")
                        else:
                            self.add_log_to_card(file_name, "✅ 应用文字删除: 无匹配文字", "warning")
                    
                    # 排除页面信息
                    if excluded_pages:
                        from utils.page_parser import format_page_range
                        excluded_str = format_page_range(excluded_pages)
                        self.add_log_to_card(file_name, f"✅ 排除页面: {excluded_str}", "success")
                    
                    # 保存文件
                    output_path = get_output_path(file_path)
                    handler.save(output_path, optimize=True)
                    output_name = Path(output_path).name
                    self.add_log_to_card(file_name, f"✅ 保存文件: {output_name}", "success")
                    
                    if self.output_dir is None:
                        self.output_dir = str(Path(output_path).parent)
                    
                    self.add_log_to_card(file_name, "✅ 处理完成！", "success")
                
                # 更新状态为成功
                self.update_file_card_status(file_name, "success")
                self.stats["success"] += 1
                self.stats["processing"] = 0
                
                # 记录处理结果
                self.processed_files[file_path] = "已完成"
                
                if self.main_window:
                    self.dialog.after_idle(lambda fp=file_path: self.main_window.update_file_status(fp, "已完成"))
                
            except Exception as e:
                import traceback
                error_msg = str(e)
                self.add_log_to_card(file_name, f"❌ 处理失败: {error_msg}", "error")
                self.update_file_card_status(file_name, "error")
                self.stats["failed"] += 1
                self.stats["processing"] = 0
                
                # 记录处理结果
                self.processed_files[file_path] = "失败"
                
                if self.main_window:
                    self.dialog.after_idle(lambda fp=file_path: self.main_window.update_file_status(fp, "失败"))
                
            # 更新进度
            progress = (idx + 1) / total_files
            self.update_progress(progress, idx + 1, total_files)
            
        # 处理完成
        self.is_processing = False
        
        # 处理完成后允许移动和调整大小
        self.dialog.unbind("<Configure>")
        self.dialog.resizable(True, True)
        
        if not self.is_stopped:
            self.add_log("", "=" * 60, "info")
            self.add_log("", "✅ 所有文件处理完成！", "success")
            
            # 确保所有文件状态都已更新（在主线程中执行）
            if self.main_window:
                def finalize_status():
                    for file_info in self.file_list:
                        file_path = file_info["path"]
                        # 如果状态还是"处理中"，根据处理结果更新
                        if file_info.get("status") == "处理中":
                            if file_path in self.processed_files:
                                status = self.processed_files[file_path]
                                self.main_window.update_file_status(file_path, status)
                            else:
                                # 如果没有记录，默认为已完成（因为处理完成了）
                                self.main_window.update_file_status(file_path, "已完成")
                self.dialog.after(100, finalize_status)
            
            # 弹出成功提示对话框
            self.dialog.after(500, self.show_completion_dialog)
            
    def create_file_card(self, file_name, status):
        """创建文件卡片"""
        # 卡片框架
        card_frame = ctk.CTkFrame(self.log_text)
        self.file_cards[file_name] = {
            "frame": card_frame,
            "status": status,
            "content": []
        }
        
        # 文件名和图标
        icon_map = {
            "waiting": "⏸️",
            "processing": "⏳",
            "success": "✅",
            "error": "❌"
        }
        icon = icon_map.get(status, "📄")
        
        name_label = ctk.CTkLabel(
            card_frame,
            text=f"{icon} {file_name}",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        name_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # 步骤容器
        steps_frame = ctk.CTkFrame(card_frame)
        steps_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.file_cards[file_name]["steps_frame"] = steps_frame
        
        # 将卡片插入到日志文本中（使用window_create）
        # 由于Text组件不支持直接嵌入CTkFrame，我们使用文本方式显示
        self.add_log("", f"\n{'='*60}", "info")
        self.add_log("", f"📄 {file_name}", "info")
        
    def add_log_to_card(self, file_name, message, tag="info"):
        """添加日志到文件卡片"""
        self.add_log("", f"   {message}", tag)
        
    def update_file_card_status(self, file_name, status):
        """更新文件卡片状态"""
        if file_name in self.file_cards:
            self.file_cards[file_name]["status"] = status
            
    def add_log(self, prefix, message, tag="info"):
        """添加日志（批量更新优化）"""
        full_message = f"{prefix}{message}\n"
        self._log_queue.append((full_message, tag))
        
        if not self._log_update_scheduled:
            self._log_update_scheduled = True
            self.dialog.after(50, self._flush_log_queue)
    
    def _flush_log_queue(self):
        """批量刷新日志队列"""
        if not self._log_queue:
            self._log_update_scheduled = False
            return
        
        batch = self._log_queue[:20]
        self._log_queue = self._log_queue[20:]
        
        for message, tag in batch:
            self.log_text.insert("end", message, tag)
        
        self.log_text.see("end")
        
        if self._log_queue:
            self.dialog.after(50, self._flush_log_queue)
        else:
            self._log_update_scheduled = False
        
    def update_progress(self, progress, current, total):
        """更新进度"""
        self.dialog.after_idle(lambda: self._do_update_progress(progress, current, total))
    
    def _do_update_progress(self, progress, current, total):
        """实际执行进度更新（在主线程中）"""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"{int(progress * 100)}% ({current}/{total})")
        
    def update_current_file(self, text):
        """更新当前文件信息"""
        self.dialog.after_idle(lambda t=text: self.current_file_label.configure(text=f"当前文件: {t}"))
        
    def update_stats(self):
        """更新统计信息"""
        self.dialog.after_idle(lambda: self._do_update_stats())
    
    def _do_update_stats(self):
        """实际执行统计更新（在主线程中）"""
        self.stats_label.configure(
            text=f"成功: {self.stats['success']}  失败: {self.stats['failed']}  "
                 f"进行中: {self.stats['processing']}  等待: {self.stats['waiting']}"
        )
        
    def toggle_pause(self):
        """切换暂停状态"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.configure(text="▶️ 继续")
        else:
            self.btn_pause.configure(text="⏸️ 暂停")
            
    
    def stop_processing(self):
        """停止处理"""
        self.is_stopped = True
        self.is_paused = False
        self.add_log("", "⏹️ 处理已停止", "warning")
        
    def show_completion_dialog(self):
        """显示处理完成对话框"""
        # 创建自定义对话框
        dialog = ctk.CTkToplevel(self.dialog)
        dialog.title("处理完成")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        # 设置最小尺寸并居中显示
        dialog_width = 420
        dialog_height = 250
        dialog.minsize(dialog_width, dialog_height)
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # 主容器
        main_frame = ctk.CTkFrame(dialog, fg_color=("white", "#F5F7FA"))
        main_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # 内容容器（垂直布局）
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        
        # 成功图标
        icon_label = ctk.CTkLabel(
            content_frame,
            text="✅",
            font=ctk.CTkFont(size=50)
        )
        icon_label.pack(pady=(10, 15))
        
        # 消息文本
        message_label = ctk.CTkLabel(
            content_frame,
            text="所有文件处理完成！",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#2C3E50"
        )
        message_label.pack(pady=(0, 25))
        
        # 按钮容器（水平布局）
        btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 0))
        
        # 确定按钮（关闭日志窗口）
        btn_ok = ctk.CTkButton(
            btn_frame,
            text="确定",
            command=lambda: self.close_dialog(dialog),
            width=130,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#5B7FFF",
            hover_color="#4A6EE8",
            text_color="white"
        )
        btn_ok.pack(side="left", padx=(0, 15))
        
        # 打开文件夹按钮（打开输出文件夹并关闭对话框）
        btn_open = ctk.CTkButton(
            btn_frame,
            text="打开文件夹",
            command=lambda: self.open_output_folder_and_close(dialog),
            width=130,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#27AE60",
            hover_color="#229954",
            text_color="white"
        )
        btn_open.pack(side="left", padx=(15, 0))
    
    def close_dialog(self, completion_dialog):
        """关闭处理完成对话框和日志窗口"""
        completion_dialog.destroy()
        
        # 确保所有文件状态都已更新（处理中 -> 已完成/失败）
        if self.main_window:
            for file_info in self.file_list:
                file_path = file_info["path"]
                # 如果状态还是"处理中"，根据处理结果更新
                if file_info.get("status") == "处理中":
                    if file_path in self.processed_files:
                        status = self.processed_files[file_path]
                        self.main_window.update_file_status(file_path, status)
                    else:
                        # 如果没有记录，默认为已完成（因为处理完成了）
                        self.main_window.update_file_status(file_path, "已完成")
        
        self.dialog.destroy()
    
    def open_output_folder_and_close(self, completion_dialog):
        """打开输出文件夹并关闭对话框"""
        completion_dialog.destroy()
        
        if self.output_dir is None and self.file_list:
            from utils.file_utils import get_output_path
            first_file = self.file_list[0]["path"]
            output_path = get_output_path(first_file)
            self.output_dir = str(Path(output_path).parent)
        
        if self.output_dir and os.path.exists(self.output_dir):
            try:
                system = platform.system()
                if system == "Windows":
                    os.startfile(self.output_dir)
                elif system == "Darwin":
                    subprocess.run(["open", self.output_dir])
                else:
                    subprocess.run(["xdg-open", self.output_dir])
            except Exception as e:
                show_error(self.dialog, f"无法打开文件夹: {e}")
        else:
            show_warning(self.dialog, "输出文件夹不存在")
        
        self.dialog.destroy()
    
    def open_output_folder(self, completion_dialog=None):
        """打开输出文件夹"""
        if completion_dialog:
            completion_dialog.destroy()
        
        if self.output_dir is None and self.file_list:
            from utils.file_utils import get_output_path
            first_file = self.file_list[0]["path"]
            output_path = get_output_path(first_file)
            self.output_dir = str(Path(output_path).parent)
        
        if self.output_dir and os.path.exists(self.output_dir):
            try:
                system = platform.system()
                if system == "Windows":
                    os.startfile(self.output_dir)
                elif system == "Darwin":
                    subprocess.run(["open", self.output_dir])
                else:
                    subprocess.run(["xdg-open", self.output_dir])
            except Exception as e:
                show_error(self.dialog, f"无法打开文件夹: {e}")
        else:
            show_warning(self.dialog, "输出文件夹不存在")

