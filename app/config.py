from decouple import config
from pydantic import BaseSettings


class Settings(BaseSettings):
    # Auth
    sms_api_key: str = config("SMS_API_KEY")
    auth_secret_key: str = config("SECRET_KEY")
    auth_salt: str = config("SALT")

    # ChatGPT
    gpt_api_key: str = config("CHATGPT_API_KEY")
    gpt_model: str = config("CHATGPT_MODEL")

    # Database
    db_host: str = config("DB_HOST")
    db_port: int = config("DB_PORT")
    db_user: str = config("DB_USER")
    db_pass: str = config("DB_PASS")

    # Payments
    tinkoff_password: str = config("TINKOFF_PASSWORD")

    # App Info
    app_version: str = "1.0.0"


CONFIG = Settings()
