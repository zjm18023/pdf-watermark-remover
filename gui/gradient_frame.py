"""
渐变背景框架
支持渐变蓝色背景的Frame组件
"""
import tkinter as tk


class GradientFrame(tk.Canvas):
    """渐变背景Frame类"""
    
    def __init__(self, parent, color1='#e3f2fd', color2='#bbdefb', **kwargs):
        kwargs.pop('bg', None)
        super().__init__(parent, highlightthickness=0, borderwidth=0, **kwargs)
        
        self.color1 = color1
        self.color2 = color2
        
        self.bind('<Configure>', self._draw_gradient)
        self.update_idletasks()
        self._draw_gradient(None)
    
    def _hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _rgb_to_hex(self, rgb):
        """将RGB转换为十六进制颜色"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def _interpolate_color(self, color1, color2, ratio):
        """在两个颜色之间插值"""
        rgb1 = self._hex_to_rgb(color1)
        rgb2 = self._hex_to_rgb(color2)
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
        return self._rgb_to_hex((r, g, b))
    
    def _draw_gradient(self, event):
        """绘制渐变背景"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        self.delete("gradient")
        for i in range(height):
            ratio = i / height if height > 0 else 0
            color = self._interpolate_color(self.color1, self.color2, ratio)
            self.create_line(0, i, width, i, fill=color, tags="gradient", width=1)




