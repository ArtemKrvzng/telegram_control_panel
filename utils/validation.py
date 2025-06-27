import re
from datetime import datetime

class Validation:

    @staticmethod
    def is_valid_email(email: str) -> bool:
        # Проверка email на соответствие формату
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.fullmatch(pattern, email) is not None

    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> list[str]:
        # Проверка пароля по критериям безопасности
        errors = []
        if not password:
            errors.append("Пароль не может быть пустым.")
            return errors

        if len(password) < min_length:
            errors.append(f"Пароль должен содержать не менее {min_length} символов.")
        if not any(c.isdigit() for c in password):
            errors.append("Пароль должен содержать хотя бы одну цифру.")
        if not any(c.islower() for c in password):
            errors.append("Пароль должен содержать хотя бы одну строчную букву.")
        if not any(c.isupper() for c in password):
            errors.append("Пароль должен содержать хотя бы одну заглавную букву.")
        if not re.search(r'[@_!#$%^&*()<>/\\|}{~:;.,?=\-+`\'"]', password):
            errors.append("Пароль должен содержать хотя бы один специальный символ (например, @, #, $, !).")

        return errors

    @staticmethod
    def validate_datetime_str(datetime_str: str) -> datetime | None:
        # Валидация строки даты-времени в формате 'ГГГГ-ММ-ДД ЧЧ:ММ'
        if not datetime_str:
            return None
        if not re.fullmatch(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', datetime_str):
            return None
        try:
            return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        except ValueError:
            return None

    @staticmethod
    def is_valid_time_hh_mm(time_str: str, strict_values: bool = True) -> bool:
        # Проверка строки времени 'ЧЧ:ММ', с опцией строгой валидации
        if not time_str:
            return False
        if not re.fullmatch(r'^\d{2}:\d{2}$', time_str):
            return False

        if strict_values:
            try:
                hours, minutes = map(int, time_str.split(':'))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    return False
            except ValueError:
                return False

        return True

