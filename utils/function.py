import random
import string
import bcrypt

#Хеширует пароль с использованием bcrypt
def hash_password_bcrypt(password: str) -> bytes:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

#Сравнивает обычный пароль с хешем из базы данных
def verify_password_bcrypt(plain_password: str, hashed_password_from_db: bytes) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_from_db)

#Генерирует случайную строку из букв и цифр заданной длины
def p_link_generate(length: int) -> str:
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
