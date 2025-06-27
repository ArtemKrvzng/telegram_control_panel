import os, time, shutil, mimetypes, logging
from pathlib import Path
import flet as ft
from flet_route import Params, Basket
from utils.style import *
from utils.database import Database
from utils.request import sendMessage, sendMediaMessage
from utils.function import p_link_generate
from utils.telegram_bot_manager import start_bot_for_user, is_bot_running, stop_bot_by_token

# Константы путей
ASSETS = Path("assets")
BROADCAST_IMAGES_DIR = ASSETS / "post_images"
BROADCAST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_DIR = ASSETS / "avatars"

class BroadcastPage:
    def __init__(self):
        self.db, self.logger = Database(), logging.getLogger(__name__)
        self.page_ref, self.user_data = None, {}
        self.selected_image_path = None

        # Элементы интерфейса
        self.snackbar = ft.SnackBar(content=ft.Text(""), open=False, duration=4000, action="OK", on_action=lambda _: setattr(self.snackbar, 'open', False))
        self.message_input = ft.TextField(label="Сообщение", multiline=True, min_lines=1, max_lines=12, filled=True, border_radius=8, expand=True)
        self.image_preview = ft.Container(visible=False)
        self.clear_image_button = ft.IconButton(icon=ft.Icons.CLEAR, tooltip="Убрать файл", visible=False, on_click=self._clear_selected_image)
        self.pick_files_button = ft.ElevatedButton("Выбрать файл", icon=ft.Icons.UPLOAD, on_click=self._pick_file_handler)
        self.file_picker = ft.FilePicker(on_result=self._on_file_selected)
        self.delay_checkbox = ft.Checkbox(label="Задержка между отправками (1 сек)", value=True)
        self.send_button = ft.ElevatedButton("Разослать подписчикам", icon=ft.Icons.SEND_ROUNDED, on_click=self._broadcast_all_handler)
        self.status_text = ft.Text("", size=12, color="green")

        # Элементы навигации
        self.logo = ft.Text('CHANNEL MANAGER', expand=True, font_family=TITLE_FONT_FAMILY, size=18, weight=ft.FontWeight.BOLD)
        self.menu_title = ft.Text('МЕНЮ', size=13, font_family=TITLE_FONT_FAMILY, weight=ft.FontWeight.W_600, opacity=0.7)
        self.header_title = ft.Text('Рассылка', size=20, font_family=TITLE_FONT_FAMILY, weight=ft.FontWeight.BOLD)
        self.user_avatar = ft.Image(width=36, height=36, fit=ft.ImageFit.COVER, border_radius=18, tooltip="Ваш аватар")
        self.display_name = ft.Text("Загрузка...", weight=ft.FontWeight.BOLD, size=14)

        self.theme_icon = None
        self.sidebar = self.header = None
        self.main_col = ft.Column(spacing=15, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.main_container = ft.Container(expand=True, content=self.main_col, padding=20)

    # Получение данных пользователя
    def _fetch_user_data(self, user_id: int, force: bool = False):
        if not force and self.user_data.get("id") == user_id:
            return
        try:
            user_row = self.db.get_user_by_id(user_id)
            self.user_data = dict(user_row._mapping) if user_row else {}
            if not self.user_data:
                self.page_ref.go("/")
            else:
                self._update_user_info_ui()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки пользователя: {e}")
            self.page_ref.go("/")

    # Обновление UI с данными пользователя
    def _update_user_info_ui(self):
        name = self.user_data.get('login') or self.user_data.get('email') or "User"
        self.display_name.value = name
        avatar_url = self.user_data.get('avatar_url')
        path = AVATARS_DIR.parent / avatar_url if avatar_url else None
        self.user_avatar.src = avatar_url if path and path.exists() else DEFAULT_AVATAR_FLET_PATH
        for ctrl in [self.display_name, self.user_avatar]:
            if ctrl.page:
                ctrl.update()

    # Шаблон карточки
    def _card(self, title, content):
        return ft.Card(elevation=2, content=ft.Container(content=content, padding=20, border_radius=10))

    # Форма рассылки
    def _broadcast_form(self):
        return self._card("Сообщение для рассылки", ft.Column([
            ft.Text("Сообщение для рассылки", weight=ft.FontWeight.BOLD, size=18),
            self.message_input,
            ft.Row([self.pick_files_button, self.clear_image_button], spacing=10),
            self.image_preview,
            self.delay_checkbox,
            self.send_button,
            self.status_text
        ], spacing=15))

    # Обновление стилей
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode or "light")
        page.bgcolor = self.main_container.bgcolor = colors["primary_bg"]
        self.header.bgcolor = self.sidebar.bgcolor = colors["secondary_bg"]
        self.sidebar.border = ft.border.only(right=ft.BorderSide(1, colors["divider_color"]))
        self.theme_icon.style = ft.ButtonStyle(color={"": colors["icon_color"], "selected": colors["accent"]})

    # Показ сообщений
    def _show_message(self, msg: str, is_error: bool = True):
        colors = get_colors(self.page_ref.theme_mode or "light")
        self.snackbar.content = ft.Text(msg)
        self.snackbar.bgcolor = colors["error"] if is_error else colors["success"]
        if self.snackbar not in self.page_ref.overlay:
            self.page_ref.overlay.append(self.snackbar)
        self.snackbar.open = True
        self.page_ref.update()

    # Обработчик выбора файла
    def _pick_file_handler(self, e):
        self.file_picker.pick_files(allow_multiple=False)

    # Действия при выборе файла
    def _on_file_selected(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return

        file_path = Path(e.files[0].path)
        new_name = f"{file_path.stem}_{p_link_generate(6)}{file_path.suffix}"
        self.selected_image_path = BROADCAST_IMAGES_DIR / new_name

        try:
            shutil.copy(file_path, self.selected_image_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            size_str = self._format_file_size(os.path.getsize(self.selected_image_path))

            is_web = getattr(self.page_ref, 'web', False)
            preview = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)

            if mime_type:
                if mime_type.startswith("image"):
                    preview.controls.append(ft.Image(src=str(self.selected_image_path), width=150, height=150, fit=ft.ImageFit.CONTAIN, border_radius=8))
                elif mime_type.startswith("video") and is_web:
                    preview.controls.append(ft.Video(src=str(self.selected_image_path), width=220, height=180, autoplay=False, controls=True, border_radius=8))
                elif mime_type.startswith("audio") and is_web:
                    preview.controls.append(ft.Audio(src=str(self.selected_image_path), autoplay=False, volume=1.0))
                else:
                    preview.controls.append(ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=40, opacity=0.6))
                preview.controls.append(ft.Text(f"{file_path.name} ({size_str})", size=11))
            else:
                preview.controls.append(ft.Text(file_path.name, size=12, overflow=ft.TextOverflow.ELLIPSIS))
                preview.controls.append(ft.Text(size_str, size=11))

            self.image_preview.content = preview
            self.image_preview.visible = True
            self.clear_image_button.visible = True
            self.image_preview.update()
            self.clear_image_button.update()

        except Exception as ex:
            self._show_message(f"Ошибка загрузки: {ex}")

    # Очистка выбранного файла
    def _clear_selected_image(self, e):
        self.image_preview.content = None
        self.image_preview.visible = self.clear_image_button.visible = False
        self.selected_image_path = None
        self.image_preview.update()
        self.clear_image_button.update()

    # Основной обработчик рассылки
    def _broadcast_all_handler(self, e):
        msg = self.message_input.value.strip()
        if not msg and not self.selected_image_path:
            self._show_message("Введите сообщение или прикрепите изображение.")
            return
        user_id, token = self.user_data.get("id"), self.user_data.get("user_telegram_token")
        if not user_id or not token:
            self._show_message("Ваш бот не настроен.")
            return
        if not is_bot_running(token):
            start_bot_for_user(token, user_id)

        subscribers = self.db.get_subscribers_by_user(user_id)
        if not subscribers:
            self._show_message("У вашего бота пока нет подписчиков.")
            return

        count = 0
        for sub in subscribers:
            chat_id = str(sub.telegram_chat_id)
            try:
                resp = sendMediaMessage(token, chat_id, str(self.selected_image_path), msg) if self.selected_image_path else sendMessage(token, chat_id, msg)
                if resp.get("ok"): count += 1
            except Exception as ex:
                self.logger.warning(f"Ошибка отправки {chat_id}: {ex}")
            if self.delay_checkbox.value:
                time.sleep(1)

        self._show_message(f"Отправлено: {count} из {len(subscribers)}", is_error=False)
        self._clear_form()

    # Обработчик выхода
    def _logout_handler(self, e=None):
        token = self.user_data.get("user_telegram_token")
        if token and is_bot_running(token):
            stop_bot_by_token(token)
        for key in ['auth_user', 'user_email']:
            if self.page_ref.session.contains_key(key):
                self.page_ref.session.remove(key)
        self.page_ref.go("/")

    # Форматирование размера файла
    def _format_file_size(self, size_bytes: int) -> str:
        return f"{size_bytes:.1f} B" if size_bytes < 1024 else f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024**2 else f"{size_bytes / 1024**2:.1f} MB"

    # Очистка формы
    def _clear_form(self):
        self.message_input.value = ""
        self.selected_image_path = None
        self.image_preview.content = None
        self.image_preview.visible = False
        self.clear_image_button.visible = False
        for ctrl in [self.message_input, self.image_preview, self.clear_image_button]:
            ctrl.update()

    # Основная страница
    def view(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        self.page_ref = page
        uid = page.session.get("auth_user")
        if not uid:
            page.go("/")
            return ft.View()

        self._fetch_user_data(uid, force=True)
        token = self.user_data.get("user_telegram_token")
        if token and not is_bot_running(token):
            start_bot_for_user(token, uid)

        page.title = "Панель управления - Рассылка"
        page.fonts = {TITLE_FONT_FAMILY: FONT_OFONT_PATH}
        page.font_family = DEFAULT_FONT_FAMILY
        page.theme_mode = page.client_storage.get("theme_mode") or "light"

        def toggle_theme(e=None):
            page.theme_mode = "dark" if page.theme_mode == "light" else "light"
            page.client_storage.set("theme_mode", page.theme_mode)
            self.theme_icon.selected = (page.theme_mode == "dark")
            self._update_styles(page)
            page.update()

        self.theme_icon = ft.IconButton(icon=ft.Icons.LIGHT_MODE, selected_icon=ft.Icons.DARK_MODE, selected=(page.theme_mode == "dark"), icon_size=20, tooltip="Сменить тему", on_click=toggle_theme)

        def menu_btn(icon, label, route):
            return ft.TextButton(content=ft.Row([ft.Icon(icon, size=18), ft.Text(label)], spacing=10), on_click=lambda _: page.go(route))

        self.sidebar = ft.Container(width=260, content=ft.Column([
            ft.Container(ft.Row([ft.Image(src=LOGO_FLET_PATH, width=30, height=30), self.logo]), padding=20),
            ft.Divider(height=1),
            ft.Container(self.menu_title, padding=ft.padding.only(left=20, top=20, bottom=10)),
            ft.Column([
                menu_btn(ft.Icons.SETTINGS_OUTLINED, "Настройки TG", "/dashboard"),
                menu_btn(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, "Профиль", "/profile"),
                menu_btn(ft.Icons.POST_ADD_ROUNDED, "Постинг", "/posting"),
                menu_btn(ft.Icons.PEOPLE_ALT_ROUNDED, "Рассылка", "/broadcast_custom")
            ], spacing=5),
            ft.Divider(height=1),
            ft.Container(self.theme_icon, padding=10)
        ]))

        user_popup = ft.PopupMenuButton(
            content=ft.Row([self.user_avatar, self.display_name, ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=16, opacity=0.7)], spacing=8),
            items=[
                ft.PopupMenuItem(text="Профиль", icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED, on_click=lambda _: page.go('/profile')),
                ft.PopupMenuItem(height=1),
                ft.PopupMenuItem(text="Выйти", icon=ft.Icons.LOGOUT_ROUNDED, on_click=self._logout_handler)
            ]
        )

        self.header = ft.Container(content=ft.Row([self.header_title, user_popup], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=ft.padding.symmetric(horizontal=25, vertical=15))

        self.main_col.controls.clear()
        self.main_col.controls.append(self._broadcast_form())

        for el in [self.file_picker, self.snackbar]:
            if el not in page.overlay:
                page.overlay.append(el)

        self._update_styles(page)

        return ft.View(route="/broadcast_custom", padding=0, controls=[
            ft.Row([
                self.sidebar,
                ft.Column([self.header, ft.Divider(height=1), self.main_container], expand=True, spacing=0)
            ], expand=True)
        ])
