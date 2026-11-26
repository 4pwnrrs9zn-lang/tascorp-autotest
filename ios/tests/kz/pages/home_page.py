from pages.base_page import BasePage

from ..locators import Home


class HomePage(BasePage):
    """Главная: карточка пользователя (ФИО, роль), «Өтінімдер/Заявки», нижние вкладки."""

    def wait_loaded(self):
        self.wait_visible(Home.TAB_HOME)
        return self

    def role_label(self, role):
        return self.wait_visible(Home.role(role))

    def applications_button(self):
        return self.wait_visible(Home.APPLICATIONS)
