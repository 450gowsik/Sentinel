import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from dotenv import load_dotenv
import dns.resolver

# Configure DNS to use Google DNS (bypass local DNS issues)
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

# Load environment variables (force reload)
load_dotenv(".env", override=True)

def test_connection():
    print("--- MongoDB Connection Test ---")
    
    # Use the original cloud connection string
    mongo_url = "mongodb+srv://gowsikbabubabu_db_user:sentinel@cluster0.1g1pkb2.mongodb.net/?appName=Cluster0"
    
    print(f"URL: {mongo_url.split('@')[-1]}")  # Print sanitized URL for verification
    
    try:
        # Create client with short timeout
        client = MongoClient(
            mongo_url, 
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test 1: Ping
        print("\n1. Pinging server...")
        client.admin.command('ping')
        print("✅ Ping successful! Server is reachable.")
        
        # Test 2: Write Permission
        print("\n2. Testing write permission...")
        db_name = os.getenv("MONGODB_DB", "sentinel_detections")
        db = client[db_name]
        collection = db.test_connection
        
        result = collection.insert_one({"status": "test", "message": "Sentinel connection check"})
        print(f"✅ Write successful! Inserted ID: {result.inserted_id}")
        
        # Test 3: Read
        print("\n3. Testing read permission...")
        doc = collection.find_one({"_id": result.inserted_id})
        if doc:
            print("✅ Read successful! Document retrieved.")
        else:
            print("❌ Read failed! Document not found.")
            
        # Cleanup
        collection.delete_one({"_id": result.inserted_id})
        print("\n✅ Test completed successfully.")
        
    except ConnectionFailure:
        import traceback
        traceback.print_exc()
        print("\n❌ Connectivity Error:")
        print("\nPossible causes:")
        print("1. IP Whitelist: Have you added your current IP to MongoDB Atlas Network Access?")
        print("2. Password: Is the password in .env correct?")
        
        # Try again with disabled SSL verify
        print("\n⚠️ Retrying with SSL verification disabled...")
        try:
            client_insecure = MongoClient(
                mongo_url, 
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=2000,
                tlsAllowInvalidCertificates=True
            )
            client_insecure.admin.command('ping')
            print("✅ Connection succeeded with SSL verification disabled! (Certificate issue)")
        except Exception:
            print("❌ Retry failed even without SSL verification.")
        
    except OperationFailure as e:
        print(f"\n❌ Authentication/Permission Error: {e}")
        print("Check your username/password and user roles in Atlas.")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_connection()
