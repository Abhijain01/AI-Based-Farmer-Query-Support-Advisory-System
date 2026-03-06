
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import sys

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
print(f"Testing connection to: {MONGO_URI.split('@')[1] if '@' in MONGO_URI else 'Localhost'}")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ MongoDB Connection Successful!")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")
    sys.exit(1)
