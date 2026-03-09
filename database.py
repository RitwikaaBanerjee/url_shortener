from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

MONGO_DATABASE_URL = "mongodb://localhost:27017/"
client = MongoClient(MONGO_DATABASE_URL)

try:
    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')
except ConnectionFailure:
    print("Server not available")

db = client["url_shortener"]
urls_collection = db["urls"]

def get_db():
    yield db
