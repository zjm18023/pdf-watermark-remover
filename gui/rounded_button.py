"""
圆角按钮组件
自定义圆角按钮类
"""
import tkinter as tk


class RoundedButton(tk.Canvas):
    """圆角按钮类"""
    
    def __init__(self, parent, text="", command=None, bg='#007bff', fg='white', 
                 font=('Microsoft YaHei UI', 9), padx=15, pady=6, radius=8, 
                 hover_bg=None, **kwargs):
        self.command = command
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg or self._darken_color(bg)
        self.font = font
        self.radius = radius
        self.padx = padx
        self.pady = pady
        self.is_hover = False
        
        # 计算按钮大小
        temp_label = tk.Label(parent, text=text, font=font)
        width = temp_label.winfo_reqwidth() + padx * 2
        height = temp_label.winfo_reqheight() + pady * 2
        temp_label.destroy()
        
        # 获取父容器背景色
        try:
            parent_bg = parent.cget('bg') if hasattr(parent, 'cget') else parent.get('bg', '#ffffff')
        except:
            parent_bg = '#ffffff'
        
        super().__init__(parent, width=width, height=height, highlightthickness=0, 
                        borderwidth=0, bg=parent_bg, **kwargs)
        
        self.text = text
        self.setup_button()
        self.bind_events()
    
    def _darken_color(self, color):
        """使颜色变深"""
        if color.startswith('#'):
            try:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                r = max(0, r - 30)
                g = max(0, g - 30)
                b = max(0, b - 30)
                return f"#{r:02x}{g:02x}{b:02x}"
            except:
                return color
        return color
    
    def setup_button(self):
        """设置按钮外观"""
        self.draw_button(self.bg)
    
    def draw_button(self, color):
        """绘制圆角按钮"""
        self.delete("all")
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        r = self.radius
        
        # 绘制圆角矩形
        self.create_rectangle(r, 0, width - r, height, fill=color, outline=color)
        self.create_rectangle(0, r, width, height - r, fill=color, outline=color)
        
        # 绘制四个圆角
        self.create_oval(0, 0, r * 2, r * 2, fill=color, outline=color)
        self.create_oval(width - r * 2, 0, width, r * 2, fill=color, outline=color)
        self.create_oval(0, height - r * 2, r * 2, height, fill=color, outline=color)
        self.create_oval(width - r * 2, height - r * 2, width, height, fill=color, outline=color)
        
        # 添加文字
        self.create_text(width // 2, height // 2, text=self.text, fill=self.fg, font=self.font)
    
    def bind_events(self):
        """绑定事件"""
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.config(cursor='hand2')
    
    def on_click(self, event):
        """点击事件"""
        if self.command:
            self.command()
    
    def on_enter(self, event):
        """鼠标进入"""
        self.is_hover = True
        self.draw_button(self.hover_bg)
    
    def on_leave(self, event):
        """鼠标离开"""
        self.is_hover = False
        self.draw_button(self.bg)




