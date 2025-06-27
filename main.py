import flet as ft
from router import Router
from utils.style import *
from utils.telegram_bot_manager import stop_all_bots


def main(page: ft.Page):
    page.title = "Channel Manager"
    page.window.center()
    page.window.min_width = DEFAULT_WIDTH_WINDOW
    page.window.min_height = DEFAULT_HEIGHT_WINDOW
    page.window.width = DEFAULT_WIDTH_WINDOW
    page.window.height = DEFAULT_HEIGHT_WINDOW
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.update()

    def window_event(e):
        if e.data == "close":
            page.open(confirm_dialog)
            page.update()
    page.window.prevent_close = True
    page.window.on_event = window_event

    def yes_click(e):
        stop_all_bots()
        page.window.destroy()

    def no_click(e):
        page.close(confirm_dialog)
        page.update()

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Выход"),
        content=ft.Text("Вы действительно хотите выйти с приложения?"),
        actions=[
            ft.ElevatedButton("Да", on_click=yes_click),
            ft.OutlinedButton("Нет", on_click=no_click),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    Router(page)

if __name__ == '__main__':
    ft.app(target=main, assets_dir='assets')