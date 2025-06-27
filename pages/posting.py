import mimetypes, os, shutil, logging
from pathlib import Path
from datetime import datetime
import flet as ft
from flet_route import Params, Basket
from apscheduler.schedulers.background import BackgroundScheduler
from utils.style import *
from utils.database import Database
from utils.telegram_bot_manager import stop_bot_by_token, is_bot_running
from utils.validation import Validation
from utils.request import sendMessage, sendMediaMessage
from utils.function import p_link_generate

# Константы
ASSETS = "assets"
POST_IMAGES_DIR = Path(ASSETS) / "post_images"
AVATARS_DIR = Path(ASSETS) / "avatars"
POST_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Логирование
logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO)


class PostingPage:
    def __init__(self):
        self.db = Database()
        self.validation = Validation()
        self.scheduler = BackgroundScheduler(timezone='Europe/Moscow')
        if not self.scheduler.running:
            try:
                self.scheduler.start()
            except Exception as e:
                print("Ошибка запуска планировщика")

        self.page_ref = None
        self.user_data = {}

        # Выбор файла и даты
        self.selected_image_path_on_disk = None
        self.selected_image_original_name = None
        self.selected_date = self.selected_time = None

        # UI Контролы
        self.message_input = ft.TextField(label="Сообщение", multiline=True, min_lines=1, max_lines=12,
                                          filled=True, border_radius=8, expand=True)
        self.clear_image_button = ft.IconButton(icon=ft.Icons.CLEAR_ROUNDED, tooltip="Убрать файл",
                                                on_click=self._clear_selected_image, visible=False)
        self.pick_files_button = ft.ElevatedButton("Выбрать файл", icon=ft.Icons.UPLOAD,
                                                   on_click=self._pick_files_handler)
        self.file_preview = ft.Container(visible=False)
        self.file_picker = ft.FilePicker(on_result=self._on_pick_files_result)

        # Отложенный постинг
        self.scheduled_post_checkbox = ft.Checkbox(label="Отложенный постинг", on_change=self._toggle_scheduled_fields)
        self.date_display_field = ft.TextField(label="Дата", read_only=True, filled=True, border_radius=8, width=130)
        self.time_display_field = ft.TextField(label="Время", read_only=True, filled=True, border_radius=8, width=130)
        self.pick_date_button = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH_ROUNDED, tooltip="Выбрать дату",
                                              on_click=self._open_date_picker)
        self.pick_time_button = ft.IconButton(icon=ft.Icons.ACCESS_TIME_ROUNDED, tooltip="Выбрать время",
                                              on_click=self._open_time_picker)
        self.date_picker = ft.DatePicker(on_change=self._on_date_selected, first_date=datetime.now())
        self.time_picker = ft.TimePicker(on_change=self._on_time_selected)

        self.datetime_selection_container = ft.Row(
            [self.date_display_field, self.pick_date_button, ft.Container(width=10),
             self.time_display_field, self.pick_time_button],
            visible=False, spacing=5)

        # Кнопки отправки
        self.submit_now_button = ft.ElevatedButton("Отправить сейчас", icon=ft.Icons.SEND_ROUNDED,
                                                   on_click=self._submit_now_handler)
        self.submit_scheduled_button = ft.ElevatedButton("Запланировать", icon=ft.Icons.SCHEDULE_SEND_ROUNDED,
                                                         on_click=self._submit_scheduled_handler, visible=False)

        # Дизайн
        self.snackbar = ft.SnackBar(content=ft.Text(""), open=False, duration=4000, action="OK",
                                    on_action=lambda _: setattr(self.snackbar, 'open', False))

        self.sidebar = self.header = None
        self.logo_text = ft.Text('CHANNEL MANAGER', expand=True, font_family=TITLE_FONT_FAMILY,
                                 size=18, weight=ft.FontWeight.BOLD)
        self.menu_title = ft.Text('МЕНЮ', size=13, font_family=TITLE_FONT_FAMILY,
                                  weight=ft.FontWeight.W_600, opacity=0.7)
        self.header_title = ft.Text('Создание Поста', size=20, font_family=TITLE_FONT_FAMILY,
                                    weight=ft.FontWeight.BOLD)
        self.display_name = ft.Text("Загрузка...", weight=ft.FontWeight.BOLD, size=14)
        self.user_avatar = ft.Image(width=36, height=36, fit=ft.ImageFit.COVER,
                                    border_radius=18, tooltip="Ваш аватар")
        self.theme_icon = None

        self.main_col = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=0, expand=True)
        self.main_container = ft.Container(expand=True, content=self.main_col, padding=20)

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
        except Exception as e:
            logger.error(f"Ошибка загрузки данных пользователя: {e}")
            self.page_ref.go('/')

    # Обновление UI пользователя
    def _update_user_ui(self):
        name = self.user_data.get('login') or self.user_data.get('email') or "User"
        self.display_name.value = name
        avatar_url = self.user_data.get('avatar_url')
        path = AVATARS_DIR.parent / avatar_url if avatar_url else None
        self.user_avatar.src = avatar_url if path and path.exists() else DEFAULT_AVATAR_FLET_PATH
        for ctrl in [self.display_name, self.user_avatar]:
            if ctrl.page:
                ctrl.update()

    # Показ сообщения
    def _show_message(self, msg: str, is_error: bool = True):
        colors = get_colors(self.page_ref.theme_mode or "light")
        self.snackbar.content = ft.Text(msg)
        self.snackbar.bgcolor = colors["error"] if is_error else colors["success"]
        if self.snackbar not in self.page_ref.overlay:
            self.page_ref.overlay.append(self.snackbar)
        self.snackbar.open = True
        self.page_ref.update()
    # Обработка выбора файла
    def _pick_files_handler(self, e): self.file_picker.pick_files(allow_multiple=False)

    def _on_pick_files_result(self, e):
        if not e.files:
            return

        file_path = Path(e.files[0].path)
        self.selected_image_original_name = file_path.name
        unique = p_link_generate(8)
        new_name = f"{file_path.stem}_{unique}{file_path.suffix}"
        self.selected_image_path_on_disk = POST_IMAGES_DIR / new_name

        try:
            shutil.copy(str(file_path), str(self.selected_image_path_on_disk))
            mime_type, _ = mimetypes.guess_type(file_path)
            file_size = os.path.getsize(self.selected_image_path_on_disk)
            size_str = self._format_file_size(file_size)

            # Формируем preview
            self.file_preview.content = None
            self.file_preview.visible = True
            is_web = getattr(self.page_ref, 'web', False)

            def text_info(extra=""): return ft.Text(f"{file_path.name} ({extra}{size_str})", size=11)

            if mime_type:
                if mime_type.startswith("image") and not mime_type.endswith("gif"):
                    self.file_preview.content = ft.Column([
                        ft.Image(src=str(self.selected_image_path_on_disk), width=150, height=150,
                                 fit=ft.ImageFit.CONTAIN, border_radius=8),
                        text_info()
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

                elif mime_type.endswith("gif"):
                    self.file_preview.content = ft.Column([
                        ft.Image(src=str(self.selected_image_path_on_disk), width=150, height=150,
                                 fit=ft.ImageFit.CONTAIN, border_radius=8),
                        text_info("GIF, ")
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

                elif mime_type.startswith("video") and is_web:
                    self.file_preview.content = ft.Column([
                        ft.Video(src=str(self.selected_image_path_on_disk), width=220, height=180,
                                 autoplay=False, controls=True, border_radius=8),
                        text_info()
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

                elif mime_type.startswith("audio") and is_web:
                    self.file_preview.content = ft.Column([
                        ft.Audio(src=str(self.selected_image_path_on_disk), autoplay=False, volume=1.0),
                        text_info()
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

                else:
                    self.file_preview.content = ft.Column([
                        ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=40, opacity=0.6),
                        ft.Text(file_path.name, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(size_str, size=11)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            else:
                self.file_preview.content = ft.Column([
                    ft.Icon(ft.Icons.HELP_OUTLINE, size=40, opacity=0.6),
                    ft.Text(file_path.name, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(size_str, size=11)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

            self.file_preview.update()
            self.clear_image_button.visible = True
            self.clear_image_button.update()

        except Exception as ex:
            self._show_message(f"Ошибка загрузки файла: {ex}")

    def _clear_selected_image(self, e):
        self.file_preview.content = None
        self.file_preview.visible = False
        self.clear_image_button.visible = False
        self.selected_image_path_on_disk = self.selected_image_original_name = None
        self.file_preview.update()
        self.clear_image_button.update()

    def _format_file_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 ** 2):.1f} MB"

    # Проверка формы
    def _validate_inputs_for_submission(self) -> bool:
        msg = self.message_input.value.strip()
        if not msg and not self.selected_image_path_on_disk:
            self._show_message("Сообщение не может быть пустым без файла.")
            return False
        if not self.user_data.get('user_telegram_token') or not self.user_data.get('user_telegram_channel'):
            self._show_message("Укажите Telegram-бота и канал в настройках TG.")
            return False
        return True

    # Немедленная отправка
    def _submit_now_handler(self, e):
        if not self._validate_inputs_for_submission():
            return
        try:
            msg = self.message_input.value.strip()
            token = self.user_data['user_telegram_token']
            channel = self.user_data['user_telegram_channel']
            res = sendMediaMessage(token, channel, str(self.selected_image_path_on_disk), msg) if self.selected_image_path_on_disk else sendMessage(token, channel, msg)
            self._show_message("Сообщение отправлено!" if res.get("ok") else f"Ошибка: {res.get('description')}", not res.get("ok"))
            if res.get("ok"):
                self._clear_form()
        except Exception as ex:
            self._show_message(f"Ошибка отправки: {ex}")

    # Планирование поста
    def _submit_scheduled_handler(self, e):
        if not self._validate_inputs_for_submission():
            return
        if not self.selected_date:
            self._show_message("Выберите дату")
            return
        if not self.selected_time:
            self._show_message("Выберите время")
            return
        try:
            send_at = datetime.combine(self.selected_date, self.selected_time)
            if send_at <= datetime.now():
                self._show_message("Дата и время должны быть в будущем.")
                return
        except Exception:
            self._show_message("Ошибка даты/времени")
            return

        user_id = self.user_data.get("id")
        if not user_id:
            self._show_message("Пользователь не найден.")
            return

        image_filename = None
        if self.selected_image_path_on_disk:
            try:
                image_filename = str(self.selected_image_path_on_disk.relative_to(Path(ASSETS)))
            except ValueError:
                image_filename = self.selected_image_path_on_disk.name

        link_post = p_link_generate(10)

        try:
            self.db.insert_pending_post(
                user_id=user_id,
                message=self.message_input.value,
                image_filename=image_filename,
                link_post=link_post,
                scheduled_datetime=send_at
            )

            self.scheduler.add_job(
                _execute_scheduled_post_wrapper,
                'date', run_date=send_at,
                args=[link_post, Database()],
                id=f"post_{link_post}", replace_existing=True
            )

            self._show_message("Пост запланирован", is_error=False)
            self._clear_form()
        except Exception as ex:
            self._show_message(f"Ошибка планирования: {ex}")

    def _clear_form(self):
        self.message_input.value = ""
        self.date_display_field.value = self.time_display_field.value = ""
        self.selected_date = self.selected_time = None
        self._clear_selected_image(None)
        self.scheduled_post_checkbox.value = False
        self._toggle_scheduled_fields(None)
        for ctrl in [self.message_input, self.date_display_field, self.time_display_field, self.scheduled_post_checkbox]:
            ctrl.update()
    # Переключение планирования
    def _toggle_scheduled_fields(self, e):
        is_scheduled = self.scheduled_post_checkbox.value
        self.datetime_selection_container.visible = is_scheduled
        self.submit_scheduled_button.visible = is_scheduled
        self.submit_now_button.visible = not is_scheduled
        self.page_ref.update()

    # Выбор даты/времени
    def _open_date_picker(self, e): self.date_picker.open = True; self.page_ref.update()
    def _open_time_picker(self, e): self.time_picker.open = True; self.page_ref.update()

    def _on_date_selected(self, e):
        self.selected_date = self.date_picker.value
        self.date_display_field.value = self.selected_date.strftime("%Y-%m-%d")
        self.date_display_field.update()

    def _on_time_selected(self, e):
        self.selected_time = self.time_picker.value
        self.time_display_field.value = self.selected_time.strftime("%H:%M")
        self.time_display_field.update()

    # Выход из системы
    def _logout_handler(self, e=None):
        if self.page_ref:
            token = self.user_data.get("user_telegram_token")
            if token and is_bot_running(token):
                stop_bot_by_token(token)
            for key in ['auth_user', 'user_email']:
                if self.page_ref.session.contains_key(key):
                    self.page_ref.session.remove(key)
            self.user_data = {}
            self.page_ref.go('/')

    # Пост-карточка
    def _build_posting_form_card(self):
        return ft.Card(
            elevation=2,
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Новый пост", weight=ft.FontWeight.BOLD, size=18),
                    ft.Divider(height=10),
                    self.message_input,
                    ft.Row([self.pick_files_button, self.clear_image_button], spacing=10),
                    self.file_preview,
                    self.scheduled_post_checkbox,
                    self.datetime_selection_container,
                    ft.Row([self.submit_now_button, self.submit_scheduled_button], alignment=ft.MainAxisAlignment.END)
                ], spacing=10),
                padding=20,
                border_radius=10
            )
        )

    # Обновление стилей страницы
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode or "light")
        page.bgcolor = colors["primary_bg"]
        self.main_container.bgcolor = colors["primary_bg"]
        self.header.bgcolor = colors["secondary_bg"]
        self.sidebar.bgcolor = colors["secondary_bg"]
        self.sidebar.border = ft.border.only(right=ft.BorderSide(1, colors["divider_color"]))
        self.theme_icon.style = ft.ButtonStyle(color={"": colors["icon_color"], "selected": colors["accent"]})

    # Показ страницы
    def view(self, page: ft.Page, params: Params, basket: Basket) -> ft.View:
        self.page_ref = page
        uid = page.session.get("auth_user")
        if not uid:
            page.go("/")
            return ft.View()
        self._fetch_user_data(uid, force=True)

        page.title = "Панель управления - Постинг"
        page.fonts = {TITLE_FONT_FAMILY: FONT_OFONT_PATH}
        page.font_family = DEFAULT_FONT_FAMILY
        page.theme_mode = page.client_storage.get("theme_mode") or "light"

        def toggle_theme(e=None):
            new_mode = "dark" if page.theme_mode == "light" else "light"
            page.theme_mode = new_mode
            page.client_storage.set("theme_mode", new_mode)
            self.theme_icon.selected = (new_mode == "dark")
            self._update_styles(page)
            page.update()

        self.theme_icon = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE, selected_icon=ft.Icons.DARK_MODE,
            selected=(page.theme_mode == "dark"), icon_size=20,
            tooltip="Сменить тему", on_click=toggle_theme
        )

        def menu_btn(icon, label, route):
            return ft.TextButton(
                content=ft.Row([ft.Icon(icon, size=18), ft.Text(label)], spacing=12),
                on_click=lambda _, r=route: page.go(r)
            )

        # Сайдбар
        self.sidebar = ft.Container(
            width=260, padding=ft.padding.only(bottom=10),
            content=ft.Column([
                ft.Container(ft.Row([ft.Image(src=LOGO_FLET_PATH, width=30, height=30), self.logo_text]), padding=20),
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
            ])
        )

        # Хедер
        user_popup = ft.PopupMenuButton(
            content=ft.Row([self.user_avatar, self.display_name,
                            ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=16, opacity=0.7)], spacing=8),
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

        self.main_col.controls.clear()
        self.main_col.controls.append(self._build_posting_form_card())
        for el in [self.file_picker, self.date_picker, self.time_picker, self.snackbar]:
            if el not in page.overlay:
                page.overlay.append(el)

        self._update_styles(page)

        return ft.View(
            route="/posting", padding=0,
            controls=[ft.Row([
                self.sidebar,
                ft.Column([self.header, ft.Divider(height=1), self.main_container], expand=True, spacing=0)
            ], expand=True)]
        )


# Отправка планированных постов
def _execute_scheduled_post_wrapper(link_post: str, db_instance: Database):
    try:
        _execute_scheduled_post_logic(link_post, db_instance)
    except Exception as ex:
        print(f"[FATAL] Ошибка выполнения задачи {link_post}: {ex}")


def _execute_scheduled_post_logic(link_post: str, db: Database):
    post = db.get_pending_post_by_link(link_post)
    if not post or post.status != "pending":
        return
    user = db.get_user_by_id(post.user_id)
    if not user:
        return
    try:
        if post.image_filename:
            image_path = Path(ASSETS) / post.image_filename
            if image_path.exists():
                sendMediaMessage(user.user_telegram_token, user.user_telegram_channel, str(image_path), post.message)
            else:
                sendMessage(user.user_telegram_token, user.user_telegram_channel, post.message)
        else:
            sendMessage(user.user_telegram_token, user.user_telegram_channel, post.message)
        db.update_pending_post_status(link_post, "sent")
    except Exception:
        db.update_pending_post_status(link_post, "failed")

