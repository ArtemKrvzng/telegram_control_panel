import flet as ft
from flet_route import Routing, path

from pages.broadcast import BroadcastPage
from pages.login import LoginPage
from pages.posting import PostingPage
from pages.profile import ProfilePage
from pages.reset_password import ResetPasswordPage
from pages.signup import SignupPage
from pages.dashboard import DashboardPage

class Router:
    def __init__(self, page: ft.Page):
        self.page = page
        self.app_routes = [
            path(url='/', clear=True, view=LoginPage().view),
            path(url='/signup', clear=True, view=SignupPage().view),
            path(url='/dashboard', clear=True, view=DashboardPage().view),
            path(url='/posting', clear=True, view=PostingPage().view),
            path(url='/profile', clear=True, view=ProfilePage().view),
            path(url='/broadcast_custom', clear=True, view=BroadcastPage().view),
            path(url='/reset', clear=True, view=ResetPasswordPage().view)

        ]

        Routing(
            page=self.page,
            app_routes=self.app_routes,
        )
        if self.page.route == "" or self.page.route is None:
            self.page.go('/')
        else:
            self.page.go(self.page.route)