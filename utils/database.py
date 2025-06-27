from sqlalchemy import (
    create_engine, Table, MetaData, select, insert, update,
    Column, LargeBinary, Integer, String, Text, DateTime, ForeignKey, and_
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from datetime import datetime as dt
from utils.function import hash_password_bcrypt, verify_password_bcrypt, p_link_generate
import os

load_dotenv()

class Database:
    def __init__(self):
        self._load_env()
        self.engine = self._connect()
        self.metadata = MetaData()
        self._define_tables()
        self.Session = sessionmaker(bind=self.engine)

    def _load_env(self):
        self.db_host = os.getenv("DB_HOST")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_name = os.getenv("DB_NAME")
        if not all([self.db_host, self.db_user, self.db_name]):
            raise ValueError("Не все переменные окружения БД определены.")

    def _connect(self):
        url = f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}?charset=utf8mb4"
        try:
            engine = create_engine(url)
            with engine.connect():
                pass
            return engine
        except Exception as e:
            raise ConnectionError(f"Ошибка подключения к БД: {e}")

    def _define_tables(self):
        self.adminUserTable = Table(
            'admin_users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('login', String(50), nullable=False, unique=True),
            Column('email', String(255), nullable=False, unique=True),
            Column('password_hash', LargeBinary(60), nullable=False),
            Column('avatar_url', String(255)),
            Column('user_telegram_token', String(255)),
            Column('user_telegram_channel', String(255)),
            Column('created_at', DateTime, default=dt.utcnow),
            Column('updated_at', DateTime, default=dt.utcnow, onupdate=dt.utcnow),
        )
        self.postPendingTable = Table(
            'pending_posts', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('admin_users.id', ondelete="CASCADE"), nullable=False),
            Column('message', Text, nullable=False),
            Column('image_filename', String(255)),
            Column('link_post', String(50), nullable=False, unique=True),
            Column('scheduled_datetime', DateTime, nullable=False),
            Column('status', String(20), nullable=False, default='pending'),
            Column('created_at', DateTime, default=dt.utcnow),
        )
        self.botSubscribersTable = Table(
            'bot_subscribers', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('admin_users.id', ondelete="CASCADE"), nullable=False),
            Column('telegram_chat_id', String(64), nullable=False),
            Column('joined_at', DateTime, default=dt.utcnow),
        )

    def _get_session(self):
        return self.Session()

    # Пользователи

    def authorization(self, email: str, plain_password: str):
        with self._get_session() as session:
            user = session.execute(
                select(self.adminUserTable).where(self.adminUserTable.c.email == email)
            ).fetchone()
            return user if user and verify_password_bcrypt(plain_password, user.password_hash) else None

    def insert_user(self, login: str, email: str, password: str, avatar_url: str = None):
        session = self._get_session()
        try:
            session.execute(
                insert(self.adminUserTable).values(
                    login=login,
                    email=email,
                    password_hash=hash_password_bcrypt(password),
                    avatar_url=avatar_url,
                    created_at=dt.utcnow(),
                    updated_at=dt.utcnow()
                )
            )
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Ошибка добавления пользователя: {e}")
            raise
        finally:
            session.close()

    def get_user_by_id(self, user_id: int):
        with self._get_session() as session:
            return session.execute(
                select(self.adminUserTable).where(self.adminUserTable.c.id == user_id)
            ).fetchone()

    def get_user_by_email(self, email: str):
        with self._get_session() as session:
            return session.execute(
                select(self.adminUserTable).where(self.adminUserTable.c.email == email)
            ).fetchone()

    def check_email(self, email: str):
        return self.get_user_by_email(email)

    def check_login(self, login: str):
        with self._get_session() as session:
            return session.execute(
                select(self.adminUserTable).where(self.adminUserTable.c.login == login)
            ).fetchone()

    def get_admin_by_token(self, token: str):
        with self._get_session() as session:
            return session.execute(
                select(self.adminUserTable).where(self.adminUserTable.c.user_telegram_token == token)
            ).fetchone()

    def update_user_avatar(self, user_id: int, avatar_url: str | None):
        return self._update_user(user_id, {"avatar_url": avatar_url})

    def update_user_password(self, user_id: int, new_password_plain: str):
        return self._update_user(user_id, {
            "password_hash": hash_password_bcrypt(new_password_plain)
        })

    def update_user_password_by_email(self, email: str, new_password_plain: str):
        return self._update_user_by_email(email, {
            "password_hash": hash_password_bcrypt(new_password_plain)
        })

    def update_user_login(self, user_id: int, new_login: str):
        try:
            return self._update_user(user_id, {"login": new_login})
        except IntegrityError:
            return "login_exists"
        except Exception as e:
            print(f"Ошибка обновления логина: {e}")
            return False

    def update_user_telegram_settings(self, user_id: int, token: str | None, channel: str | None):
        return self._update_user(user_id, {
            "user_telegram_token": token,
            "user_telegram_channel": channel
        })

    def verify_user_password(self, user_id: int, plain_password: str) -> bool:
        user = self.get_user_by_id(user_id)
        return verify_password_bcrypt(plain_password, user.password_hash) if user else False

    def _update_user(self, user_id: int, fields: dict):
        session = self._get_session()
        try:
            fields['updated_at'] = dt.utcnow()
            session.execute(
                update(self.adminUserTable).where(self.adminUserTable.c.id == user_id).values(**fields)
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Ошибка обновления пользователя: {e}")
            return False
        finally:
            session.close()

    def _update_user_by_email(self, email: str, fields: dict):
        session = self._get_session()
        try:
            fields['updated_at'] = dt.utcnow()
            session.execute(
                update(self.adminUserTable).where(self.adminUserTable.c.email == email).values(**fields)
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Ошибка обновления пользователя: {e}")
            return False
        finally:
            session.close()

    # Подписчики

    def insert_subscriber(self, user_id: int, chat_id: str):
        session = self._get_session()
        try:
            session.execute(
                insert(self.botSubscribersTable).values(
                    user_id=user_id,
                    telegram_chat_id=chat_id,
                    joined_at=dt.utcnow()
                ).prefix_with("IGNORE")
            )
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Ошибка добавления подписчика: {e}")
        finally:
            session.close()

    def get_subscribers_by_user(self, user_id: int):
        with self._get_session() as session:
            return session.execute(
                select(self.botSubscribersTable).where(self.botSubscribersTable.c.user_id == user_id)
            ).fetchall()

    def remove_subscriber(self, user_id: int, chat_id: str):
        session = self._get_session()
        try:
            session.execute(
                self.botSubscribersTable.delete().where(
                    and_(
                        self.botSubscribersTable.c.user_id == user_id,
                        self.botSubscribersTable.c.telegram_chat_id == chat_id
                    )
                )
            )
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Ошибка удаления подписчика: {e}")
        finally:
            session.close()

    # Посты

    def insert_pending_post(self, user_id: int, message: str, scheduled_datetime: dt,
                            image_filename: str | None = None, link_post: str | None = None):
        session = self._get_session()
        try:
            if not link_post:
                link_post = p_link_generate(10)
            session.execute(
                insert(self.postPendingTable).values(
                    user_id=user_id,
                    message=message,
                    image_filename=image_filename,
                    link_post=link_post,
                    scheduled_datetime=scheduled_datetime,
                    status='pending',
                    created_at=dt.utcnow()
                )
            )
            session.commit()
            return link_post
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()

    def get_pending_post_by_link(self, link_post_val: str):
        with self._get_session() as session:
            return session.execute(
                select(self.postPendingTable).where(self.postPendingTable.c.link_post == link_post_val)
            ).fetchone()

    def update_pending_post_status(self, link_post_val: str, new_status: str):
        session = self._get_session()
        try:
            session.execute(
                update(self.postPendingTable).where(
                    self.postPendingTable.c.link_post == link_post_val
                ).values(status=new_status)
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Ошибка обновления статуса поста: {e}")
            return False
        finally:
            session.close()
