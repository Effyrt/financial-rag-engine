import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # FastAPI settings
    FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
    
    # Development mode
    USE_MOCK_API = os.getenv("USE_MOCK_API", "True").lower() == "true"
    
    # Streamlit settings
    APP_TITLE = "Financial Concepts RAG System"
    APP_ICON = "📊"
    
    # Cache settings
    ENABLE_CACHE = True
    CACHE_TTL = 3600  # 1 hour
    
    # Query settings
    MAX_SEARCH_HISTORY = 50
    DEFAULT_TIMEOUT = 30  # API request timeout (seconds)
    
    @classmethod
    def get_api_url(cls):
        """Get API URL"""
        return cls.FASTAPI_URL
    
    @classmethod
    def is_development_mode(cls):
        """Check if in development mode"""
        return cls.USE_MOCK_API


# Environment variables template (create .env file)
ENV_TEMPLATE = """
# FastAPI settings
FASTAPI_URL=http://localhost:8000

# Development mode (True: use Mock API, False: use real API)
USE_MOCK_API=True
"""

if __name__ == "__main__":
    print("=== Current Configuration ===")
    print(f"FastAPI URL: {Config.FASTAPI_URL}")
    print(f"Use Mock API: {Config.USE_MOCK_API}")
    print(f"Development Mode: {Config.is_development_mode()}")