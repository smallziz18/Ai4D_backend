from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import Config
import os

# Détecter l'environnement
DOCKER_ENV = os.getenv('DOCKER_ENV', 'false').lower() == 'true'

# Choisir le bon hôte selon l'environnement
mongo_host = Config.MONGO_HOST if DOCKER_ENV else 'localhost'

# Client synchrone (legacy, pour compatibilité)
mongo_client = MongoClient(
    host=mongo_host,
    port=Config.MONGO_PORT,
    username=Config.MONGO_APP_USERNAME,
    password=Config.MONGO_APP_PASSWORD,
    authSource=Config.MONGO_DATABASE,
    serverSelectionTimeoutMS=5000
)

mongo_db = mongo_client[Config.MONGO_DATABASE]

# Client asynchrone Motor (pour les opérations async/await)
async_mongo_client = AsyncIOMotorClient(
    host=mongo_host,
    port=Config.MONGO_PORT,
    username=Config.MONGO_APP_USERNAME,
    password=Config.MONGO_APP_PASSWORD,
    authSource=Config.MONGO_DATABASE,
    serverSelectionTimeoutMS=5000
)

async_mongo_db = async_mongo_client[Config.MONGO_DATABASE]


def get_mongo_client():
    """Retourne un client MongoDB synchrone (legacy)"""
    return MongoClient(
        host=mongo_host,
        port=Config.MONGO_PORT,
        username=Config.MONGO_APP_USERNAME,
        password=Config.MONGO_APP_PASSWORD,
        authSource=Config.MONGO_DATABASE,
        serverSelectionTimeoutMS=5000,
    )


def get_mongo_db():
    """Retourne une base de données MongoDB asynchrone (Motor)"""
    return async_mongo_db


def get_sync_mongo_db():
    """Retourne une base de données MongoDB synchrone (pour tasks Celery)"""
    client = get_mongo_client()
    return client[Config.MONGO_DATABASE]
