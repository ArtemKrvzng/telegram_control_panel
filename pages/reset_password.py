import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import flet as ft
import random
import string
from flet_route import Params, Basket
from utils.style import *
from utils.database import Database
from utils.validation import Validation


class ResetPasswordPage:
    def __init__(self):
        # Инициализация компонентов
        self.db = Database()
        self.email_input = ft.TextField(
            label="Email",
            hint_text="example@domain.com",
            border=ft.InputBorder.NONE,
            filled=True,
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            width=300
        )
        self.code_input = ft.TextField(
            label="Введите код",
            hint_text="6-значный код",
            border=ft.InputBorder.NONE,
            filled=True,
            prefix_icon=ft.Icons.CHECK_CIRCLE,
            width=300
        )
        self.password_input = ft.TextField(
            label="Новый пароль",
            hint_text="Мин. 8 симв., цифра, спец.символ...",
            password=True, can_reveal_password=True,
            border=ft.InputBorder.NONE,
            filled=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            width=300
        )
        self.confirm_password_input = ft.TextField(
            label="Подтвердите новый пароль",
            password=True, can_reveal_password=True,
            border=ft.InputBorder.NONE, filled=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            width=300
        )
        self.message_text = ft.Text(
            value="",
            visible=False,
            weight=ft.FontWeight.NORMAL,
            text_align=ft.TextAlign.LEFT,
            max_lines=5
        )
        self.loading_indicator = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)


        # Динамические компоненты
        self.generated_code = None
        self.reset_button = None
        self.send_code_button = None
        self.theme_icon_button = None
        self.title_text = None
        self.subtitle_text = None
        self.login_link = None

    # Очистка формы
    def _clear_items(self, page: ft.Page):
        self.email_input.value = ""
        self.code_input.value = ""
        self.password_input.value = ""
        self.confirm_password_input.value = ""
        self.code_input.visible = False
        self.reset_button.visible = False
        self.loading_indicator.visible = False
        self.email_input.disabled = False
        self.send_code_button.visible = True
        self.send_code_button.disabled = False
        self.generated_code = None
        page.update()

    # Обновление стилей
    def _update_styles(self, page: ft.Page):
        colors = get_colors(page.theme_mode)
        for field in [self.email_input, self.code_input, self.password_input, self.confirm_password_input]:
            field.bgcolor = colors["input_bg"]
            field.color = colors["primary_text"]
            field.border_radius = 10
            field.label_style = ft.TextStyle(color=colors["secondary_text"])
            field.hint_style = ft.TextStyle(color=colors["secondary_text"])
            field.prefix_style = ft.TextStyle(color=colors["secondary_text"])

        if self.reset_button:
            self.reset_button.bgcolor = colors["accent"]
            self.reset_button.content.color = colors["button_text"]

        if self.send_code_button:
            self.send_code_button.bgcolor = colors["accent"]
            self.send_code_button.content.color = colors["button_text"]

        if self.login_link:
            self.login_link.content.color = colors["accent"]

        if self.theme_icon_button:
            self.theme_icon_button.style = ft.ButtonStyle(color={"": colors["secondary_text"], "selected": colors["accent"]})

        if self.title_text:
            self.title_text.color = colors["primary_text"]
        if self.subtitle_text:
            self.subtitle_text.color = colors["secondary_text"]

        page.bgcolor = colors["primary_bg"]

    # Отображение сообщений
    def _show_message(self, text: str, is_error: bool = True):
        colors = get_colors(self.message_text.page.theme_mode)
        self.message_text.value = text
        self.message_text.color = colors["error"] if is_error else colors["success"]
        self.message_text.weight = ft.FontWeight.NORMAL if is_error else ft.FontWeight.BOLD
        self.message_text.visible = True

    def view(self, page: ft.Page, params: Params, basket: Basket):
        self.message_text.visible = False
        self.message_text.value = ""
        page.title = "Сброс пароля"
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

        # Генерация кода
        def generate_code():
            self.generated_code = "".join(random.choices(string.digits, k=6))
            return self.generated_code

        # Отправка письма
        def send_email(recipient_email, code):
            sender_email = "strangeluvxx@gmail.com"
            sender_password = "bquj omth uspe qlvw"
            msg = MIMEMultipart()
            msg['From'] = "TG CONTROL PANEL"
            msg['To'] = recipient_email
            msg['Subject'] = "Ваш код подтверждения"
            msg.attach(MIMEText(code, 'plain'))

            try:
                smtp = smtplib.SMTP('smtp.gmail.com', 587)
                smtp.starttls()
                smtp.login(sender_email, sender_password)
                smtp.sendmail(sender_email, recipient_email, msg.as_string())
                smtp.quit()
            except Exception as e:
                print(f"Ошибка отправки: {e}")

        # Отправка кода
        def handle_send_code(e):
            self.message_text.visible = False
            self.loading_indicator.visible = True
            page.update()

            email = self.email_input.value.strip()
            if not email or not Validation.is_valid_email(email):
                self._show_message("Некорректный email.")
            elif not self.db.get_user_by_email(email):
                self._show_message("E-mail не зарегистрирован.")
            else:
                code = generate_code()
                send_email(email, code)
                self.email_input.disabled = True
                self.password_input.disabled = False
                self.confirm_password_input.disabled = False
                self.send_code_button.visible = False
                self.send_code_button.disabled = True
                self.code_input.visible = True
                self.reset_button.visible = True
                self.code_input.focus()
                self._show_message("Код отправлен на ваш email.", False)

            self.loading_indicator.visible = False
            page.update()

        # Сброс пароля
        def handle_reset_password(e):
            self.message_text.visible = False
            self.loading_indicator.visible = True
            page.update()

            email = self.email_input.value.strip()
            code = self.code_input.value.strip()
            password = self.password_input.value
            confirm_password = self.confirm_password_input.value

            if code != self.generated_code:
                self._show_message("Неверный код.")
            elif not all([email, password, confirm_password]):
                self._show_message("Все поля должны быть заполнены.")
            elif not Validation.is_valid_email(email):
                self._show_message("Некорректный формат Email.")
            elif password != confirm_password:
                self._show_message("Пароли не совпадают.")
            else:
                errors = Validation.validate_password(password, min_length=5)
                if errors:
                    self._show_message("Пароль не соответствует требованиям:\n- " + "\n- ".join(errors))
                else:
                    self.db.update_user_password_by_email(email, password)
                    self._show_message("Пароль успешно изменен.", False)
                    self._clear_items(page)
                    return

            self.loading_indicator.visible = False
            page.update()

        # Кнопки и текст
        self.login_link = ft.TextButton(content=ft.Text("Авторизация"), on_click=lambda _: page.go('/'))
        self.theme_icon_button = ft.IconButton(ft.Icons.LIGHT_MODE, selected_icon=ft.Icons.DARK_MODE, selected=(page.theme_mode == "dark"), icon_size=24, tooltip="Сменить тему", on_click=toggle_theme)

        self.send_code_button = ft.ElevatedButton(content=ft.Text("Отправить код"), width=250, height=45, on_click=handle_send_code, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))
        self.reset_button = ft.ElevatedButton(content=ft.Text("Подтвердить код и сменить пароль"), width=250, height=45, on_click=handle_reset_password, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)), visible=False)

        self.title_text = ft.Text("Сбросить пароль", font_family=TITLE_FONT_FAMILY, size=32, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text("Введите ваш email для сброса пароля.", size=16)

        self.code_input.visible = False
        self.password_input.disabled = True
        self.confirm_password_input.disabled = True

        self._update_styles(page)
        self._clear_items(page)

        # Макет формы
        form = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            controls=[
                self.title_text,
                self.subtitle_text,
                self.message_text,
                self.email_input,
                self.code_input,
                self.password_input,
                self.confirm_password_input,
                self.loading_indicator,
                self.reset_button,
                self.send_code_button,
                self.login_link,
            ]
        )

        return ft.View(
            route="/reset-password",
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            controls=[
                ft.Row([ft.Container(content=self.theme_icon_button, alignment=ft.alignment.top_right)], alignment=ft.MainAxisAlignment.END),
                ft.Container(
                    content=form,
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
