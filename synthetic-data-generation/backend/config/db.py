from mongoengine import register_connection
from dotenv import load_dotenv
from pymongo.errors import PyMongoError
import certifi
from .config import Config


def connect_db(ssl_reqs: bool = False):
    main_db_name = (
        Config.DB_NAME if Config.ENV == "prod" else f"{Config.DB_NAME}Testing"
    )
    print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&", Config.DB_URL)
    main_db_host = f"{Config.DB_URL}/{main_db_name}?retryWrites=true&w=majority"

    ssl_kwargs = {} if not ssl_reqs else {"ssl": True, "tlsCAFile": certifi.where()}

    try:
        # Register the main connection
        register_connection(
            alias="default",
            name=main_db_name,
            host=main_db_host,
            **ssl_kwargs,
        )
        print(
            f"Connected to {'production' if Config.ENV == 'prod' else 'testing'} database at: {main_db_host}..."
        )
    except PyMongoError as e:
        print(f"Failed to connect to MongoDB: {e}")