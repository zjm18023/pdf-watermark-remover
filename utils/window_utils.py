"""窗口工具函数"""
import tkinter as tk
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox


def center_window(window, width=None, height=None):
    """将窗口居中显示在屏幕上"""
    window.update_idletasks()
    
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()
    
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")


def show_message(parent, title, message, message_type="info"):
    """显示居中的消息框"""
    icon_map = {
        "info": "info",
        "warning": "warning",
        "error": "cancel",
        "question": "question"
    }
    
    # 设置白色背景风格
    msg = CTkMessagebox(
        master=parent,
        title=title,
        message=message,
        icon=icon_map.get(message_type, "info"),
        width=400,
        bg_color="#FFFFFF",  # 白色背景
        fg_color="#FFFFFF",  # 白色前景
        button_color="#5B7FFF",  # 蓝色按钮（与主界面按钮一致）
        button_hover_color="#4A6EE8",  # 按钮悬停色
        button_text_color="white",  # 按钮文字白色
        text_color="#2C3E50",  # 深灰色文字
        title_color="#2C3E50",  # 标题颜色
        corner_radius=10  # 圆角
    )
    
    window = msg
    window.update_idletasks()
    center_window(window)
    
    return msg.get()


def show_info(parent, message, title="提示"):
    """显示信息消息框"""
    return show_message(parent, title, message, "info")


def show_warning(parent, message, title="警告"):
    """显示警告消息框"""
    return show_message(parent, title, message, "warning")


def show_error(parent, message, title="错误"):
    """显示错误消息框"""
    return show_message(parent, title, message, "error")


def ask_yesno(parent, message, title="确认"):
    """显示确认对话框"""
    # 设置白色背景风格
    msg = CTkMessagebox(
        master=parent,
        title=title,
        message=message,
        icon="question",
        option_1="是",
        option_2="否",
        width=400,
        bg_color="#FFFFFF",  # 白色背景
        fg_color="#FFFFFF",  # 白色前景
        button_color="#5B7FFF",  # 蓝色按钮（与主界面按钮一致）
        button_hover_color="#4A6EE8",  # 按钮悬停色
        button_text_color="white",  # 按钮文字白色
        text_color="#2C3E50",  # 深灰色文字
        title_color="#2C3E50",  # 标题颜色
        corner_radius=10  # 圆角
    )
    
    window = msg
    window.update_idletasks()
    center_window(window)
    
    response = msg.get()
    return response == "是"

