from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "A股股票数据API"
    APP_VERSION: str = "0.8.3"
    API_PREFIX: str = "/api/v1"

    # 数据库配置（必须通过环境变量设置）
    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    # CORS 配置（逗号分隔的域名列表，* 表示禁止）
    CORS_ORIGINS: str = ""

    # JWT 配置
    JWT_SECRET_KEY: str = ""  # 生产环境必须设置环境变量 JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 720  # 30天

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate(self):
        """启动时校验关键配置"""
        if not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY environment variable is required")
        if not self.DB_HOST:
            raise ValueError("DB_HOST environment variable is required")
        if not self.DB_NAME:
            raise ValueError("DB_NAME environment variable is required")
        if not self.DB_USER:
            raise ValueError("DB_USER environment variable is required")
        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD environment variable is required")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def cors_origins(self) -> list[str]:
        """解析 CORS_ORIGINS 环境变量，返回域名列表"""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
