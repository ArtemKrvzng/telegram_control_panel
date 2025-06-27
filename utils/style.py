# style.py

# Настройки окна
DEFAULT_WIDTH_WINDOW = 1300
DEFAULT_HEIGHT_WINDOW = 800

# Пути к ресурсам
ASSETS_DIR = "assets"
IMAGES_SUBDIR_IN_ASSETS = "images"
FONTS_SUBDIR_IN_ASSETS = "fonts"

LOGO_FLET_PATH = f"{IMAGES_SUBDIR_IN_ASSETS}/logo.png"
FONT_OFONT_PATH = f"{FONTS_SUBDIR_IN_ASSETS}/ofont.ru_Uncage.ttf"
DEFAULT_AVATAR_FLET_PATH = f"{IMAGES_SUBDIR_IN_ASSETS}/default_avatar.png"

# Шрифты
DEFAULT_FONT_FAMILY = "Roboto"
TITLE_FONT_FAMILY = "ofont"

# Цвета для светлой темы
light_theme_colors = {
    "primary_bg": "#f4f6f8",
    "secondary_bg": "#ffffff",
    "card_bg": "#ffffff",
    "input_bg": "#e9ecef",
    "border_color_input": "#ced4da",
    "primary_text": "#212529",
    "secondary_text": "#6c757d",
    "accent": "#007bff",
    "accent_subtle": "#cfe2ff",
    "button_text": "#ffffff",
    "error": "#dc3545",
    "success": "#198754",
    "icon_color": "#495057",
    "divider_color": "#dee2e6",
    "menu_item_text": "#495057",
    "menu_item_active_bg": "#e0e9f1",
    "menu_item_hover_bg": "#f0f4f8",
}

# Цвета для тёмной темы
dark_theme_colors = {
    "primary_bg": "#121212",
    "secondary_bg": "#1e1e1e",
    "card_bg": "#1e1e1e",
    "input_bg": "#2c2c2c",
    "border_color_input": "#424242",
    "primary_text": "#e0e0e0",
    "secondary_text": "#a0a0a0",
    "accent": "#64b5f6",
    "accent_subtle": "#1e3a5f",
    "button_text": "#000000",
    "error": "#f48fb1",
    "success": "#81c784",
    "icon_color": "#b0b0b0",
    "divider_color": "#424242",
    "menu_item_text": "#b0b0b0",
    "menu_item_active_bg": "#2a2a2a",
    "menu_item_hover_bg": "#333333",
}

# Выбор палитры по теме
def get_colors(page_theme_mode: str):
    if page_theme_mode == "dark":
        return dark_theme_colors
    return light_theme_colors
