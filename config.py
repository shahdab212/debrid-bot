from pydantic_settings import BaseSettings
from typing import List

class Config(BaseSettings):
    API_ID: int
    API_HASH: str
    BOT_TOKEN: str
    DEBRID_KEY: str
    ADMIN_IDS: str  # Comma-separated admin IDs

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_admin_list(self) -> List[int]:
        """Parse comma-separated admin IDs into a list of integers."""
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        return user_id in self.get_admin_list()

config = Config()
