import shutil
from pathlib import Path
import flet as ft
from flet_route import Params, Basket
from utils.style import *
from utils.database import Database
from utils.telegram_bot_manager import is_bot_running, stop_bot_by_token

# Пути и ресурсы
ASSETS = "assets"
AVATARS = "avatars"
IMAGES = "images"
DEFAULT_AVATAR = f"{IMAGES}/default_avatar.png"
LOGO = f"{IMAGES}/logo.png"
FONT = "fonts/ofont.ru_Uncage.ttf"
AVATAR_DISK_PATH = Path(ASSETS) / AVATARS


class ProfilePage:
    def __init__(self):
        self.db = Database()
        self.page_ref, self.user_data = None, {}

        # Компоненты уведомлений и загрузки
        self.snackbar = ft.SnackBar(content=ft.Text(""), open=False, duration=4000,
                                    action="OK", on_action=lambda _: setattr(self.snackbar, 'open', False))
        self.avatar_picker = ft.FilePicker(on_result=self._on_avatar_pick)

        # Компоненты аватара
        self.avatar_display = ft.Image(width=80, height=80, fit=ft.ImageFit.COVER, border_radius=40)
        self.user_avatar = ft.Image(width=36, height=36, fit=ft.ImageFit.COVER, border_radius=18, tooltip="Ваш аватар")
        self.upload_btn = ft.ElevatedButton("Сменить аватар", icon=ft.Icons.UPLOAD_FILE, on_click=self._trigger_picker)
        self.delete_btn = ft.ElevatedButton("Удалить аватар", icon=ft.Icons.DELETE_OUTLINE, on_click=self._delete_avatar)

        # Компоненты логина
        self.current_login = ft.Text("Загрузка...", weight=ft.FontWeight.BOLD, size=16)
        self.new_login_input = ft.TextField(label="Новый логин", filled=True, border_radius=8, prefix_icon=ft.Icons.PERSON_OUTLINE)
        self.login_save_btn = ft.ElevatedButton("Изменить логин", icon=ft.Icons.SAVE_OUTLINED, on_click=self._save_login)

        # Компоненты пароля
        self.current_password = ft.TextField(label="Текущий пароль", password=True, can_reveal_password=True, border_radius=8, filled=True, prefix_icon=ft.Icons.LOCK_OUTLINE)
        self.new_password = ft.TextField(label="Новый пароль", password=True, can_reveal_password=True, border_radius=8, filled=True, prefix_icon=ft.Icons.LOCK_PERSON_OUTLINED)
        self.confirm_password = ft.TextField(label="Подтвердите новый пароль", password=True, can_reveal_password=True, border_radius=8, filled=True, prefix_icon=ft.Icons.LOCK_PERSON_OUTLINED)
        self.password_btn = ft.ElevatedButton("Изменить пароль", icon=ft.Icons.KEY_ROUNDED, on_click=self._change_password)

        # Навигация и заголовки
        self.logo = ft.Text('CHANNEL MANAGER', expand=True, font_family=TITLE_FONT_FAMILY, size=18, weight=ft.FontWeight.BOLD)
        self.menu_title = ft.Text('МЕНЮ', size=13, font_family=TITLE_FONT_FAMILY, weight=ft.FontWeight.W_600, opacity=0.7)
        self.header_title = ft.Text('Настройки профиля', size=20, font_family=TITLE_FONT_FAMILY, weight=ft.FontWeight.BOLD)
        self.display_name = ft.Text("Загрузка...", weight=ft.FontWeight.BOLD, size=14)

        self.theme_icon, self.sidebar, self.header = None, None, None
        self.main_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=0, expand=True)
        self.main_container = ft.Container(expand=True, content=self.main_col, padding=20)

    # Показ уведомления
    def _show_message(self, msg, is_error=True):
        if not self.page_ref: return
        colors = get_colors(self.page_ref.theme_mode or "light")
        self.snackbar.content = ft.Text(msg)
        self.snackbar.bgcolor = colors["error"] if is_error else colors["success"]
        if self.snackbar not in self.page_ref.overlay:
            self.page_ref.overlay.append(self.snackbar)
        self.snackbar.open = True
        self.page_ref.update()

    # Получение данных пользователя
    def _fetch_user_data(self, user_id: int, force=True):
        if not force and self.user_data.get('id') == user_id:
            return
        try:
            user_row = self.db.get_user_by_id(user_id)
            self.user_data = dict(user_row._mapping) if user_row else {}
            if not self.user_data:
                self.page_ref.go('/')
            else:
                self._update_profile_ui()
        except:
            self.page_ref.go('/')

    # Обновление UI профиля
    def _update_profile_ui(self):
        if not self.user_data: return
        avatar_src = self.user_data.get('avatar_url') or DEFAULT_AVATAR
        disk_path = Path(ASSETS) / avatar_src
        src = avatar_src if disk_path.exists() else DEFAULT_AVATAR
        self.avatar_display.src = self.user_avatar.src = src
        if avatar_src != DEFAULT_AVATAR and disk_path.exists():
            self.delete_btn.visible = True
            self.delete_btn.style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
        else:
            self.delete_btn.visible = False
        self.current_login.value = self.user_data.get('login', 'Не указан')
        self.new_login_input.value = ""
        self.new_login_input.error_text = None
        for f in [self.current_password, self.new_password, self.confirm_password]:
            f.value = ""
            f.error_text = None
        self.display_name.value = self.user_data.get('login', 'User')
        self.page_ref.update()

    # Загрузка нового аватара
    def _trigger_picker(self, e):
        self.avatar_picker.pick_files(allow_multiple=False,
            allowed_extensions=["png", "jpg", "jpeg", "gif"],
            dialog_title="Выберите аватар")

    def _on_avatar_pick(self, e: ft.FilePickerResultEvent):
        if not e.files or not self.user_data: return
        file = Path(e.files[0].path)
        user_id = self.user_data['id']
        file_name = f"user_{user_id}_{file.stem[:50]}.{file.suffix.lstrip('.')}"
        dest = AVATAR_DISK_PATH / file_name

        try:
            if old := self.user_data.get('avatar_url'):
                old_path = Path(ASSETS) / old
                if old_path.exists(): old_path.unlink()
            shutil.copy(str(file), str(dest))
            saved_path = str(dest.relative_to(Path(ASSETS))).replace("\\", "/")
            if self.db.update_user_avatar(user_id, saved_path):
                self.user_data['avatar_url'] = saved_path
                self._update_profile_ui()
                self._show_message("Аватар обновлён", is_error=False)
        except Exception as ex:
            self._show_message(f"Ошибка загрузки: {str(ex)[:100]}")

    # Удаление аватара
    def _delete_avatar(self, e):
        uid = self.user_data.get("id")
        file_path = Path(ASSETS) / self.user_data.get("avatar_url", "")
        try:
            if file_path.exists(): file_path.unlink()
            if self.db.update_user_avatar(uid, None):
                self.user_data["avatar_url"] = None
                self._update_profile_ui()
                self._show_message("Аватар удалён", is_error=False)
        except Exception as ex:
            self._show_message(f"Ошибка удаления: {str(ex)}")

    # Изменение логина
    def _save_login(self, e):
        new_login = self.new_login_input.value.strip()
        uid = self.user_data.get("id")
        if not new_login:
            self.new_login_input.error_text = "Введите логин"
        elif existing := self.db.check_login(new_login):
            if existing.id != uid:
                self.new_login_input.error_text = "Логин занят"
        else:
            result = self.db.update_user_login(uid, new_login)
            if result == "login_exists":
                self._show_message("Логин уже используется")
            elif result:
                self.user_data["login"] = new_login
                self._update_profile_ui()
                self._show_message("Логин обновлён", is_error=False)
                return
        self.new_login_input.update()

    # Изменение пароля
    def _change_password(self, e):
        uid = self.user_data["id"]
        current, new, confirm = self.current_password.value, self.new_password.value, self.confirm_password.value
        if not all([current, new, confirm]):
            self._show_message("Все поля обязательны")
        elif new != confirm:
            self._show_message("Пароли не совпадают")
        elif not self.db.verify_user_password(uid, current):
            self._show_message("Неверный текущий пароль")
        elif self.db.update_user_password(uid, new):
            self._show_message("Пароль изменён", is_error=False)
            for f in [self.current_password, self.new_password, self.confirm_password]:
                f.value = ""
                f.update()

    # Компоненты карточек
    def _card(self, title, content):
        return ft.Card(elevation=2, content=ft.Container(content=content, padding=20, border_radius=10))

    def _avatar_card(self):
        return self._card("Аватар профиля", ft.Column([
            ft.Text("Аватар профиля", weight=ft.FontWeight.BOLD, size=18),
            ft.Divider(height=10),
            ft.Row([self.avatar_display], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.upload_btn, self.delete_btn], alignment=ft.MainAxisAlignment.SPACE_AROUND, spacing=10)
        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

    def _login_card(self):
        return self._card("Логин", ft.Column([
            ft.Text("Логин", weight=ft.FontWeight.BOLD, size=18),
            ft.Text("Ваш текущий логин", opacity=0.7, size=12),
            ft.Divider(height=10),
            ft.Row([ft.Text("Текущий логин:"), self.current_login], spacing=5),
            self.new_login_input,
            ft.Row([self.login_save_btn], alignment=ft.MainAxisAlignment.END)
        ], spacing=15))

    def _password_card(self):
        return self._card("Пароль", ft.Column([
            ft.Text("Смена пароля", weight=ft.FontWeight.BOLD, size=18),
            ft.Divider(height=10),
            self.current_password,
            self.new_password,
            self.confirm_password,
            ft.Row([self.password_btn], alignment=ft.MainAxisAlignment.END)
        ], spacing=15))

    # Обновление стилей
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode or "light")
        page.bgcolor = colors["primary_bg"]
        self.main_container.bgcolor = colors["primary_bg"]
        self.header.bgcolor = colors["secondary_bg"]
        self.sidebar.bgcolor = colors["secondary_bg"]
        self.sidebar.border = ft.border.only(right=ft.BorderSide(1, colors["divider_color"]))
        self.theme_icon.style = ft.ButtonStyle(color={"": colors["icon_color"], "selected": colors["accent"]})
        page.update()

    # Главная вьюха страницы
    def view(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        self.page_ref = page
        uid = page.session.get('auth_user')
        if not uid:
            page.go('/')
            return ft.View()

        self._fetch_user_data(uid, force=True)

        # Настройка темы
        page.title = 'Панель управления - Настройки профиля'
        page.fonts = {TITLE_FONT_FAMILY: FONT}
        page.font_family = DEFAULT_FONT_FAMILY
        page.theme_mode = page.client_storage.get("theme_mode") or "light"

        def toggle_theme(e=None):
            page.theme_mode = "dark" if page.theme_mode == "light" else "light"
            page.client_storage.set("theme_mode", page.theme_mode)
            self.theme_icon.selected = (page.theme_mode == "dark")
            self._update_styles(page)

        self.theme_icon = ft.IconButton(icon=ft.Icons.LIGHT_MODE, selected_icon=ft.Icons.DARK_MODE,
                                        selected=(page.theme_mode == "dark"), icon_size=20,
                                        tooltip="Сменить тему", on_click=toggle_theme)

        def menu_btn(icon, label, route):
            return ft.TextButton(content=ft.Row([ft.Icon(icon, size=18), ft.Text(label)], spacing=12),
                                 on_click=lambda _, r=route: page.go(r))

        menu = ft.Column([
            menu_btn(ft.Icons.SETTINGS_OUTLINED, "Настройки TG", "/dashboard"),
            menu_btn(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, "Профиль", "/profile"),
            menu_btn(ft.Icons.POST_ADD_ROUNDED, "Постинг", "/posting"),
            menu_btn(ft.Icons.PEOPLE_ALT_ROUNDED, "Рассылка", "/broadcast_custom")
        ], spacing=5)

        self.sidebar = ft.Container(width=260, padding=ft.padding.only(bottom=10),
            content=ft.Column([
                ft.Container(ft.Row([ft.Image(src=LOGO, width=30, height=30), self.logo]), padding=20),
                ft.Divider(height=1),
                ft.Container(self.menu_title, padding=ft.padding.only(left=20, top=20, bottom=10)),
                menu,
                ft.Divider(height=1),
                ft.Container(self.theme_icon, padding=10, alignment=ft.alignment.center_left)
            ])
        )

        user_popup = ft.PopupMenuButton(
            content=ft.Row([self.user_avatar, self.display_name, ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=16, opacity=0.7)], spacing=8),
            items=[
                ft.PopupMenuItem(text="Профиль", icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED, on_click=lambda _: page.go('/profile')),
                ft.PopupMenuItem(height=1),
                ft.PopupMenuItem(text="Выйти", icon=ft.Icons.LOGOUT_ROUNDED, on_click=self._logout_handler)
            ]
        )

        self.header = ft.Container(content=ft.Row([self.header_title, user_popup], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                   padding=ft.padding.symmetric(horizontal=25, vertical=15))

        self.main_col.controls.clear()
        self.main_col.controls.extend([
            ft.Container(self._avatar_card(), padding=20),
            ft.Container(self._login_card(), padding=20),
            ft.Container(self._password_card(), padding=20)
        ])

        if self.avatar_picker not in page.overlay:
            page.overlay.append(self.avatar_picker)
        if self.snackbar not in page.overlay:
            page.overlay.append(self.snackbar)

        self._update_styles(page)

        return ft.View(
            route="/profile", padding=0,
            controls=[ft.Row([
                self.sidebar,
                ft.Column([self.header, ft.Divider(height=1), self.main_container], expand=True, spacing=0)
            ], expand=True)]
        )

    # Выход из профиля
    def _logout_handler(self, e=None):
        if self.page_ref:
            token = self.user_data.get("user_telegram_token")
            if token and is_bot_running(token):
                stop_bot_by_token(token)
            for k in ["auth_user", "user_email", "user_login"]:
                if self.page_ref.session.contains_key(k):
                    self.page_ref.session.remove(k)
            self.user_data = {}
            self.page_ref.go('/')
