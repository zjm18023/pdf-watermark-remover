"""
配置文件管理模块
"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".qushuiyin"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "window": {
        "width": 1200,
        "height": 800,
        "x": None,
        "y": None,
        "maximized": False
    },
    "theme": {
        "mode": "light",  # dark or light
        "color_theme": "blue"  # blue, green, dark-blue
    },
    "pdf": {
        "dpi": 150,
        "default_zoom": 1.0
    },
    "recent_files": [],
    "delete_mode": {
        "region": "actual",  # actual or cover
        "text": "actual"
    }
}


def load_config():
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # 合并默认配置，但主题设置使用默认值（确保浅色主题）
                merged = DEFAULT_CONFIG.copy()
                merged.update(saved_config)
                merged["theme"] = DEFAULT_CONFIG["theme"].copy()
                return merged
        except Exception as e:
            print(f"加载配置失败: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置文件"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置失败: {e}")
