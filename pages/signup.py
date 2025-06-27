import asyncio
import flet as ft
from flet_route import Params, Basket
from utils.style import *
from utils.database import Database
from utils.validation import Validation

class SignupPage:
    # Инициализация компонентов
    def __init__(self):
        self.db = Database()
        self.email_input = ft.TextField(
            label="Email",
            border=ft.InputBorder.NONE,
            filled=True,
            autofocus=True,
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            hint_text="example@domain.com"
        )
        self.login_input = ft.TextField(
            label="Логин",
            border=ft.InputBorder.NONE,
            filled=True,
            prefix_icon=ft.Icons.PERSON_OUTLINE,
            hint_text="Ваш уникальный логин"
        )
        self.password_input = ft.TextField(
            label="Пароль",
            password=True,
            can_reveal_password=True,
            border=ft.InputBorder.NONE,
            filled=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            hint_text="Мин. 5 симв., цифра, спец.символ..."
        )
        self.confirm_password_input = ft.TextField(
            label="Подтвердите пароль",
            password=True,
            can_reveal_password=True,
            border=ft.InputBorder.NONE,
            filled=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE
        )
        self.message_text = ft.Text(
            value="",
            visible=False,
            weight=ft.FontWeight.NORMAL,
            text_align=ft.TextAlign.LEFT,
            max_lines=5
        )
        self.loading_indicator = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)
        self.signup_button = None
        self.login_link = None
        self.theme_icon_button = None
        self.title_text = None
        self.subtitle_text = None

    # Обновление стилей в зависимости от темы
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode)

        for field in [self.email_input, self.login_input, self.password_input, self.confirm_password_input]:
            field.bgcolor = colors["input_bg"]
            field.color = colors["primary_text"]
            field.border_radius = 10
            field.label_style = ft.TextStyle(color=colors["secondary_text"])
            field.hint_style = ft.TextStyle(color=colors["secondary_text"])
            field.prefix_style = ft.TextStyle(color=colors["secondary_text"])

        self.message_text.color = colors["error"]

        if self.signup_button:
            self.signup_button.bgcolor = colors["accent"]
            if isinstance(self.signup_button.content, ft.Text):
                self.signup_button.content.color = colors["button_text"]

        if self.login_link and isinstance(self.login_link.content, ft.Text):
            self.login_link.content.color = colors["accent"]

        if self.title_text:
            self.title_text.color = colors["primary_text"]
        if self.subtitle_text:
            self.subtitle_text.color = colors["secondary_text"]

        if self.theme_icon_button:
            self.theme_icon_button.style = ft.ButtonStyle(
                color={"": colors["secondary_text"], "selected": colors["accent"]}
            )

        page.bgcolor = colors["primary_bg"]

    # Очистка страницы
    def clear_items(self):
        self.email_input.value = ""
        self.login_input.value = ""
        self.password_input.value = ""
        self.confirm_password_input.value = ""
        self.message_text.visible = False
        self.message_text.value = ""
        self.loading_indicator.visible = False

    # Показ ошибки/успеха
    def _show_message(self, message: str, page: ft.Page, is_error: bool = True):
        colors = get_colors(page.theme_mode)
        self.message_text.value = message
        self.message_text.color = colors["error"] if is_error else colors["success"]
        self.message_text.weight = ft.FontWeight.NORMAL if is_error else ft.FontWeight.BOLD
        self.message_text.visible = True
        self.loading_indicator.visible = False
        self.signup_button.disabled = False
        page.update()

    # Основной метод отображения страницы
    def view(self, page: ft.Page, params: Params, basket: Basket):
        self.clear_items()
        page.title = "Страница регистрации"
        page.fonts = {TITLE_FONT_FAMILY: "fonts/ofont.ru_Uncage.ttf"}
        page.font_family = DEFAULT_FONT_FAMILY
        page.theme_mode = page.client_storage.get("theme_mode") or "light"

        # 🌗 Переключение темы
        def toggle_theme(e):
            page.theme_mode = "dark" if page.theme_mode == "light" else "light"
            page.client_storage.set("theme_mode", page.theme_mode)
            self.theme_icon_button.selected = (page.theme_mode == "dark")
            self._update_styles(page)
            page.update()

        # Валидация и регистрация
        def handle_signup(e):
            async def async_signup():
                self.message_text.visible = False
                self.loading_indicator.visible = True
                page.update()

                email = self.email_input.value.strip()
                login = self.login_input.value.strip()
                password = self.password_input.value
                confirm_password = self.confirm_password_input.value

                if not all([email, login, password, confirm_password]):
                    self._show_message("Все поля должны быть заполнены.", page)
                    return

                if not Validation.is_valid_email(email):
                    self._show_message("Некорректный формат Email.", page)
                    return

                password_errors = Validation.validate_password(password, min_length=5)
                if password_errors:
                    self._show_message("Пароль не соответствует требованиям:\n- " + "\n- ".join(password_errors), page)
                    return

                if password != confirm_password:
                    self._show_message("Пароли не совпадают.", page)
                    return

                if self.db.check_email(email):
                    self._show_message("Пользователь с таким Email уже существует.", page)
                    return

                if self.db.check_login(login):
                    self._show_message("Пользователь с таким логином уже существует.", page)
                    return

                try:
                    self.db.insert_user(login, email, password)
                    self._show_message("Регистрация прошла успешно! Теперь вы можете войти.", page, is_error=False)

                    # Очистка полей
                    self.email_input.value = ""
                    self.login_input.value = ""
                    self.password_input.value = ""
                    self.confirm_password_input.value = ""
                    self.email_input.focus()
                    page.update()
                    await asyncio.sleep(2)
                    self.message_text.visible = False
                    page.update()

                except Exception as ex:
                    print(f"Ошибка регистрации: {ex}")
                    self._show_message("Произошла ошибка при регистрации. Попробуйте позже.", page)

            # Запуск async-функции
            page.run_task(async_signup)

        # Очистка сообщений при вводе
        def clear_error_on_change(e):
            if self.message_text.visible:
                self.message_text.visible = False
                page.update()

        # Кнопки и текст
        self.theme_icon_button = ft.IconButton(
            ft.Icons.LIGHT_MODE,
            selected=(page.theme_mode == "dark"),
            selected_icon=ft.Icons.DARK_MODE,
            icon_size=24,
            tooltip="Сменить тему",
            on_click=toggle_theme
        )

        self.signup_button = ft.ElevatedButton(
            content=ft.Text("Зарегистрироваться"),
            width=250,
            height=45,
            on_click=handle_signup,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )

        self.login_link = ft.TextButton(
            content=ft.Text("Уже есть аккаунт? Войти"),
            on_click=lambda _: page.go('/')
        )

        self.title_text = ft.Text(
            "Создать аккаунт",
            font_family=TITLE_FONT_FAMILY,
            size=32,
            weight=ft.FontWeight.BOLD
        )
        self.subtitle_text = ft.Text("Присоединяйтесь к нам!", size=16)

        for field in [self.email_input, self.login_input, self.password_input, self.confirm_password_input]:
            field.on_change = clear_error_on_change
        self.confirm_password_input.on_submit = handle_signup

        self._update_styles(page)

        # Макет формы
        signup_form_content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            controls=[
                self.title_text,
                self.subtitle_text,
                self.message_text,
                self.email_input,
                self.login_input,
                self.password_input,
                self.confirm_password_input,
                ft.Row(
                    [self.loading_indicator, self.signup_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                self.login_link,
            ]
        )

        return ft.View(
            route="/signup",
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            controls=[
                ft.Row(
                    [ft.Container(content=self.theme_icon_button, alignment=ft.alignment.top_right)],
                    alignment=ft.MainAxisAlignment.END
                ),
                ft.Container(
                    content=signup_form_content,
                    width=450,
                    border_radius=15,
                    padding=ft.padding.symmetric(horizontal=30, vertical=25),
                    alignment=ft.alignment.center,
                    expand=True
                )
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
