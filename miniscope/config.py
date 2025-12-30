from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    vision_model: str = "minicpm-v"
    embedding_model: str = "nomic-embed-text:latest"
    
    class Config:
        env_file = ".env"

settings = Settings()
