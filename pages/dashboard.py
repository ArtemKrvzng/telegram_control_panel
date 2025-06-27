import flet as ft
from flet_route import Params, Basket
from utils.telegram_bot_manager import start_bot_for_user, is_bot_running, stop_bot_by_token
from utils.style import *
from utils.database import Database

DEFAULT_AVATAR = "images/default_avatar.png"
LOGO = "images/logo.png"
FONT = "fonts/ofont.ru_Uncage.ttf"


class DashboardPage:
    def __init__(self):
        self.db = Database()
        self.page_ref = None
        self.user_data = {}
        self.tg_settings_edit_mode = False

        # Telegram поля
        self.token_input = ft.TextField(label="Токен Telegram-бота", password=True, can_reveal_password=True,
                                        filled=True, border_radius=8, disabled=True, prefix_icon=ft.Icons.KEY_ROUNDED)
        self.channel_input = ft.TextField(label="ID или @username канала", filled=True,
                                          border_radius=8, disabled=True, prefix_icon=ft.Icons.LINK_ROUNDED)
        self.edit_btn = ft.IconButton(icon=ft.Icons.EDIT_ROUNDED, tooltip="Редактировать", on_click=self._toggle_edit)
        self.save_btn = ft.ElevatedButton(text="Сохранить", icon=ft.Icons.SAVE_OUTLINED,
                                          on_click=self._save_tg_settings, visible=False)
        self.cancel_btn = ft.TextButton(text="Отмена", on_click=self._cancel_edit, visible=False)

        # Прочее
        self.snackbar = ft.SnackBar(content=ft.Text(""), open=False, duration=4000, action="OK",
                                    on_action=lambda _: setattr(self.snackbar, 'open', False))
        self.logo = ft.Text('CHANNEL MANAGER', expand=True, font_family=TITLE_FONT_FAMILY, size=18, weight=ft.FontWeight.BOLD)
        self.menu_title = ft.Text('МЕНЮ', size=13, font_family=TITLE_FONT_FAMILY, weight=ft.FontWeight.W_600, opacity=0.7)
        self.header_title = ft.Text('Настройки Telegram', size=20, font_family=TITLE_FONT_FAMILY, weight=ft.FontWeight.BOLD)
        self.user_name = ft.Text("Загрузка...", weight=ft.FontWeight.BOLD, size=14)
        self.user_avatar = ft.Image(width=36, height=36, fit=ft.ImageFit.COVER, border_radius=18, tooltip="Ваш аватар")

        self.theme_icon = None
        self.sidebar = None
        self.header = None
        self.main_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=0, expand=True)
        self.main_container = ft.Container(expand=True, content=self.main_col, padding=20)

    # Показ сообщений
    def _show_message(self, msg, is_error=True):
        if not self.page_ref: return
        colors = get_colors(self.page_ref.theme_mode or "light")
        self.snackbar.content = ft.Text(msg)
        self.snackbar.bgcolor = colors["error"] if is_error else colors["success"]
        if self.snackbar not in self.page_ref.overlay:
            self.page_ref.overlay.append(self.snackbar)
        self.snackbar.open = True
        self.page_ref.update()

    # Загрузка данных пользователя
    def _fetch_user_data(self, user_id: int, force=False):
        if not force and self.user_data.get('id') == user_id:
            return
        try:
            user_row = self.db.get_user_by_id(user_id)
            self.user_data = dict(user_row._mapping) if user_row else {}
            if not self.user_data:
                self.page_ref.go('/')
            else:
                self._update_user_ui()
        except:
            self.page_ref.go('/')

    # Обновление UI пользователя
    def _update_user_ui(self):
        if not self.user_data: return
        self.user_name.value = self.user_data.get('login') or self.user_data.get('email', "User")
        self.user_avatar.src = self.user_data.get('avatar_url') or DEFAULT_AVATAR

    # Загрузка TG настроек
    def _load_tg_settings(self):
        self.token_input.value = self.user_data.get('user_telegram_token', '')
        self.channel_input.value = self.user_data.get('user_telegram_channel', '')
        self._set_disabled(True)

    # Блокировка/разблокировка полей
    def _set_disabled(self, state: bool):
        self.token_input.disabled = state
        self.channel_input.disabled = state
        self.tg_settings_edit_mode = not state
        self.edit_btn.visible = state
        self.save_btn.visible = not state
        self.cancel_btn.visible = not state
        self.page_ref.update()

    def _toggle_edit(self, e=None): self._set_disabled(False)
    def _cancel_edit(self, e=None): self._load_tg_settings()

    # Сохранение TG настроек
    def _save_tg_settings(self, e=None):
        if not self.page_ref or not self.user_data:
            return

        uid = self.user_data['id']
        token_new = self.token_input.value.strip()
        channel_new = self.channel_input.value.strip()
        token_old = self.user_data.get('user_telegram_token')

        # Обработка: приведение к виду "@channel"
        if channel_new.startswith("https://t.me/"):
            channel_new = channel_new.replace("https://t.me/", "@")
        elif channel_new.startswith("t.me/"):
            channel_new = channel_new.replace("t.me/", "@")
        elif not channel_new.startswith("@"):
            channel_new = f"@{channel_new}"

        try:
            if self.db.update_user_telegram_settings(uid, token_new, channel_new):
                self.user_data.update({
                    'user_telegram_token': token_new,
                    'user_telegram_channel': channel_new
                })
                self._show_message("Telegram настройки сохранены.", is_error=False)
                self._set_disabled(True)
                if token_old != token_new:
                    stop_bot_by_token(token_old)
                if not is_bot_running(token_new):
                    if not start_bot_for_user(token_new, uid):
                        self._show_message("❌ Бот не запущен. Проверьте токен.")
            else:
                self._show_message("Не удалось сохранить настройки Telegram.")
        except Exception as ex:
            self._show_message(f"Ошибка: {str(ex)[:100]}")

    # Карточка Telegram
    def _build_tg_card(self) -> ft.Card:
        return ft.Card(
            elevation=2,
            content=ft.Container(
                content=ft.Column([
                    ft.Row([ft.Text("Настройки Telegram API", weight=ft.FontWeight.BOLD, size=18),
                            ft.Row([self.edit_btn], alignment=ft.MainAxisAlignment.END, expand=True)]),
                    ft.Text("Укажите токен и канал/чат для интеграции.", opacity=0.7, size=12),
                    ft.Divider(height=15),
                    self.token_input,
                    self.channel_input,
                    ft.Container(
                        content=ft.Row([self.cancel_btn, self.save_btn], alignment=ft.MainAxisAlignment.END, spacing=10),
                        padding=ft.padding.only(top=15)
                    )
                ], spacing=15), padding=20, border_radius=10
            )
        )

    # Обновление стилей
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode or "light")
        page.bgcolor = colors["primary_bg"]
        if self.main_container: self.main_container.bgcolor = colors["primary_bg"]
        if self.header: self.header.bgcolor = colors["secondary_bg"]
        if self.sidebar:
            self.sidebar.bgcolor = colors["secondary_bg"]
            self.sidebar.border = ft.border.only(right=ft.BorderSide(1, colors["divider_color"]))
        if self.theme_icon:
            self.theme_icon.style = ft.ButtonStyle(color={"": colors["icon_color"], "selected": colors["accent"]})
        page.update()

    def _logout_handler(self, e=None):
        if not self.page_ref: return
        token = self.user_data.get("user_telegram_token")
        if token and is_bot_running(token):
            stop_bot_by_token(token)
        for key in ['auth_user', 'user_email']:
            if self.page_ref.session.contains_key(key):
                self.page_ref.session.remove(key)
        self.page_ref.go('/')

    def view(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        self.page_ref = page
        uid = page.session.get('auth_user')
        if not uid:
            page.go('/')
            return ft.View()

        self._fetch_user_data(uid, force=True)
        token = self.user_data.get("user_telegram_token")
        if token and not is_bot_running(token):
            try:
                if not start_bot_for_user(token, uid):
                    self._show_message("❌ Бот не запущен. Проверьте токен.")
            except Exception as e:
                self._show_message(f"❌ Ошибка запуска бота: {e}")

        page.title = 'Панель управления - Telegram'
        page.fonts = {TITLE_FONT_FAMILY: FONT}
        page.font_family = DEFAULT_FONT_FAMILY
        page.theme_mode = page.client_storage.get("theme_mode") or "light"

        def toggle_theme(e=None):
            page.theme_mode = "dark" if page.theme_mode == "light" else "light"
            page.client_storage.set("theme_mode", page.theme_mode)
            if self.theme_icon:
                self.theme_icon.selected = (page.theme_mode == "dark")
            self._update_styles(page)

        self.theme_icon = ft.IconButton(icon=ft.Icons.LIGHT_MODE, selected_icon=ft.Icons.DARK_MODE,
                                        selected=(page.theme_mode == "dark"), icon_size=20,
                                        tooltip="Сменить тему", on_click=toggle_theme)

        def menu_btn(icon, label, route):
            return ft.TextButton(
                content=ft.Row([ft.Icon(icon, size=18), ft.Text(label)], spacing=12),
                on_click=lambda _, r=route: page.go(r)
            )

        menu = ft.Column([
            menu_btn(ft.Icons.SETTINGS_OUTLINED, "Настройки TG", "/dashboard"),
            menu_btn(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, "Профиль", "/profile"),
            menu_btn(ft.Icons.POST_ADD_ROUNDED, "Постинг", "/posting"),
            menu_btn(ft.Icons.PEOPLE_ALT_ROUNDED, "Рассылка", "/broadcast_custom")
        ], spacing=5)

        # Сайдбар
        self.sidebar = ft.Container(
            width=260, padding=ft.padding.only(bottom=10),
            content=ft.Column([
                ft.Container(content=ft.Row([ft.Image(src=LOGO, width=30, height=30), self.logo]), padding=20),
                ft.Divider(height=1),
                ft.Container(self.menu_title, padding=ft.padding.only(left=20, top=20, bottom=10)),
                menu,
                ft.Divider(height=1),
                ft.Container(self.theme_icon, padding=10, alignment=ft.alignment.center_left)
            ])
        )

        # Хедер
        user_popup = ft.PopupMenuButton(
            content=ft.Row([self.user_avatar, self.user_name, ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=16, opacity=0.7)], spacing=8),
            items=[
                ft.PopupMenuItem(text="Профиль", icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED, on_click=lambda _: page.go('/profile')),
                ft.PopupMenuItem(height=1),
                ft.PopupMenuItem(text="Выйти", icon=ft.Icons.LOGOUT_ROUNDED, on_click=self._logout_handler)
            ]
        )

        self.header = ft.Container(
            content=ft.Row([self.header_title, user_popup], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=25, vertical=15)
        )

        # Основной блок
        self.main_col.controls.clear()
        self.main_col.controls.append(ft.Container(content=self._build_tg_card(), padding=20))
        self._load_tg_settings()
        self._update_styles(page)

        return ft.View(
            route="/dashboard", padding=0,
            controls=[
                ft.Row([
                    self.sidebar,
                    ft.Column([self.header, ft.Divider(height=1), self.main_container], expand=True, spacing=0)
                ], expand=True)
            ]
        )
