"""
圆角框架组件
支持圆角边框的Frame组件
"""
import tkinter as tk


class RoundedFrame(tk.Canvas):
    """圆角Frame类"""
    
    def __init__(self, parent, bg='white', radius=10, borderwidth=0, 
                 relief=tk.FLAT, **kwargs):
        kwargs.pop('bg', None)
        kwargs.pop('borderwidth', None)
        kwargs.pop('relief', None)
        
        super().__init__(parent, highlightthickness=0, borderwidth=0, **kwargs)
        
        self.bg = bg
        self.radius = radius
        self.borderwidth = borderwidth
        self.relief = relief
        self.inner_frame = None
        
        self.bind('<Configure>', self._draw_rounded)
        self._create_inner_frame()
    
    def _create_inner_frame(self):
        """创建内部Frame"""
        if self.inner_frame is None:
            self.inner_frame = tk.Frame(self, bg=self.bg)
            self._update_inner_frame()
    
    def _update_inner_frame(self):
        """更新内部Frame位置和大小"""
        if self.inner_frame:
            width = self.winfo_width()
            height = self.winfo_height()
            if width > 1 and height > 1:
                padding = max(self.radius // 2, 2)
                self.inner_frame.place(
                    x=padding, y=padding,
                    width=width - padding * 2,
                    height=height - padding * 2
                )
    
    def _draw_rounded(self, event=None):
        """绘制圆角边框"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        self.delete("rounded_bg")
        r = self.radius
        
        # 绘制背景
        self.create_rectangle(r, 0, width - r, height, fill=self.bg, outline=self.bg, tags="rounded_bg")
        self.create_rectangle(0, r, width, height - r, fill=self.bg, outline=self.bg, tags="rounded_bg")
        
        # 四个圆角
        self.create_oval(0, 0, r * 2, r * 2, fill=self.bg, outline=self.bg, tags="rounded_bg")
        self.create_oval(width - r * 2, 0, width, r * 2, fill=self.bg, outline=self.bg, tags="rounded_bg")
        self.create_oval(0, height - r * 2, r * 2, height, fill=self.bg, outline=self.bg, tags="rounded_bg")
        self.create_oval(width - r * 2, height - r * 2, width, height, fill=self.bg, outline=self.bg, tags="rounded_bg")
        
        # 绘制边框
        if self.borderwidth > 0:
            border_color = '#cccccc' if self.relief == tk.RAISED else '#888888'
            self.create_line(r, 0, width - r, 0, fill=border_color, width=self.borderwidth, tags="rounded_bg")
            self.create_line(width, r, width, height - r, fill=border_color, width=self.borderwidth, tags="rounded_bg")
            self.create_line(width - r, height, r, height, fill=border_color, width=self.borderwidth, tags="rounded_bg")
            self.create_line(0, height - r, 0, r, fill=border_color, width=self.borderwidth, tags="rounded_bg")
            
            self.create_arc(0, 0, r * 2, r * 2, start=90, extent=90, outline=border_color, width=self.borderwidth, style=tk.ARC, tags="rounded_bg")
            self.create_arc(width - r * 2, 0, width, r * 2, start=0, extent=90, outline=border_color, width=self.borderwidth, style=tk.ARC, tags="rounded_bg")
            self.create_arc(0, height - r * 2, r * 2, height, start=180, extent=90, outline=border_color, width=self.borderwidth, style=tk.ARC, tags="rounded_bg")
            self.create_arc(width - r * 2, height - r * 2, width, height, start=270, extent=90, outline=border_color, width=self.borderwidth, style=tk.ARC, tags="rounded_bg")
        
        self._update_inner_frame()
    
    def pack(self, **kwargs):
        """pack布局方法"""
        result = super().pack(**kwargs)
        self.after(10, self._draw_rounded)
        return result
    
    def grid(self, **kwargs):
        """grid布局方法"""
        result = super().grid(**kwargs)
        self.after(10, self._draw_rounded)
        return result
    
    def place(self, **kwargs):
        """place布局方法"""
        result = super().place(**kwargs)
        self.after(10, self._draw_rounded)
        return result




