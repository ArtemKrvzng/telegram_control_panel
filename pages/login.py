import flet as ft
from flet_route import Params, Basket
from utils.style import *
from utils.database import Database

class LoginPage:
    # Инициализация компонентов
    def __init__(self):
        self.db = Database()
        self.email_input = ft.TextField(
            label="Email",
            border=ft.InputBorder.NONE,
            filled=True,
            autofocus=True,
            prefix_icon=ft.Icons.EMAIL_OUTLINED
        )
        self.password_input = ft.TextField(
            label="Пароль",
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
        self.login_button = None
        self.signup_link = None
        self.reset_link = None
        self.title_text = None
        self.subtitle_text = None
        self.theme_icon_button = None

    # Обновление стилей в зависимости от темы
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode)

        for field in [self.email_input, self.password_input]:
            field.bgcolor = colors["input_bg"]
            field.color = colors["primary_text"]
            field.border_radius = 10
            field.label_style = ft.TextStyle(color=colors["secondary_text"])
            field.hint_style = ft.TextStyle(color=colors["secondary_text"])
            field.prefix_style = ft.TextStyle(color=colors["secondary_text"])

        self.message_text.color = colors["error"]

        if self.login_button:
            self.login_button.bgcolor = colors["accent"]
            if isinstance(self.login_button.content, ft.Text):
                self.login_button.content.color = colors["button_text"]

        if self.signup_link and isinstance(self.signup_link.content, ft.Text):
            self.signup_link.content.color = colors["accent"]

        if self.reset_link and isinstance(self.reset_link.content, ft.Text):
            self.reset_link.content.color = colors["accent"]

        if self.title_text:
            self.title_text.color = colors["primary_text"]
        if self.subtitle_text:
            self.subtitle_text.color = colors["secondary_text"]

        if self.theme_icon_button:
            self.theme_icon_button.style = ft.ButtonStyle(
                color={"": colors["secondary_text"], "selected": colors["accent"]}
            )

        page.bgcolor = colors["primary_bg"]

    # Показ ошибки/успеха
    def _show_message(self, message: str, page: ft.Page):
        self.message_text.value = message
        self.message_text.visible = True
        self.loading_indicator.visible = False
        self.login_button.disabled = False
        page.update()

    # Очистка страницы
    def clear_items(self):
        self.email_input.value = ""
        self.password_input.value = ""
        self.message_text.visible = False
        self.message_text.value = ""
        self.loading_indicator.visible = False

    def view(self, page: ft.Page, params: Params, basket: Basket):
        self.clear_items()
        page.title = "Страница авторизации"
        page.fonts = {TITLE_FONT_FAMILY: "fonts/ofont.ru_Uncage.ttf"}
        page.font_family = DEFAULT_FONT_FAMILY
        page.theme_mode = page.client_storage.get("theme_mode") or "light"

        # Смена темы
        def toggle_theme(e):
            page.theme_mode = "dark" if page.theme_mode == "light" else "light"
            page.client_storage.set("theme_mode", page.theme_mode)
            self.theme_icon_button.selected = (page.theme_mode == "dark")
            self._update_styles(page)
            page.update()

        self.theme_icon_button = ft.IconButton(
            ft.Icons.LIGHT_MODE,
            selected=(page.theme_mode == "dark"),
            selected_icon=ft.Icons.DARK_MODE,
            icon_size=24,
            tooltip="Сменить тему",
            on_click=toggle_theme
        )

        # Логика авторизации
        def handle_authorization(e):
            self.message_text.visible = False
            self.loading_indicator.visible = True
            self.login_button.disabled = True
            page.update()

            email = self.email_input.value.strip()
            password = self.password_input.value

            if not email or not password:
                self._show_message("Email и пароль не могут быть пустыми.", page)
                return


            user = self.db.authorization(email, password)

            self.loading_indicator.visible = False
            self.login_button.disabled = False

            if user:
                page.session.set('auth_user', user.id)
                page.session.set('user_email', user.email)
                page.go('/dashboard')
            else:
                self._show_message("Неверный email или пароль.", page)

        # Очистка сообщений при вводе
        def clear_error_on_change(e):
            if self.message_text.visible:
                self.message_text.visible = False
                page.update()

        self.email_input.on_change = clear_error_on_change
        self.password_input.on_change = clear_error_on_change
        self.password_input.on_submit = handle_authorization

        # Кнопки и текст
        self.login_button = ft.ElevatedButton(
            content=ft.Text("Войти"),
            width=250,
            height=45,
            on_click=handle_authorization,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )
        self.reset_link = ft.TextButton(
            content=ft.Text("Забыли пароль?"),
            on_click=lambda _: page.go('/reset')
        )
        self.signup_link = ft.TextButton(
            content=ft.Text("Нет аккаунта? Зарегистрироваться"),
            on_click=lambda _: page.go('/signup')
        )
        self.title_text = ft.Text(
            "Добро пожаловать!",
            font_family=TITLE_FONT_FAMILY,
            size=32,
            weight=ft.FontWeight.BOLD
        )
        self.subtitle_text = ft.Text("Войдите, чтобы продолжить", size=16)

        self._update_styles(page)

        # Макет формы
        login_form_content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                self.title_text,
                self.subtitle_text,
                self.message_text,
                self.email_input,
                self.password_input,
                ft.Row(
                    [self.loading_indicator, self.login_button],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                self.signup_link,
                self.reset_link,
            ]
        )

        return ft.View(
            route="/",
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            controls=[
                ft.Row(
                    [ft.Container(content=self.theme_icon_button, alignment=ft.alignment.top_right)],
                    alignment=ft.MainAxisAlignment.END
                ),
                ft.Container(
                    content=login_form_content,
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


