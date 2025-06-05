import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    CORS_HEADERS = "Content-Type"
    ENV = "dev"
    API_PORT = os.getenv("API_PORT", 5000)
    DB_NAME = os.getenv("DB_NAME", "KYCExtractorDB")
    DB_URL = os.getenv("DB_URL")
    CORS_ORIGIN_WHITELIST = "*"  # any origin
    RABBIT_MQ_URL = os.getenv("RABBIT_MQ_URL")
    FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
    FIREWORKS_ACCOUNT_ID = os.getenv("FIREWORKS_ACCOUNT_ID")
    SERP_API_KEY = os.getenv("SERP_API_KEY")
