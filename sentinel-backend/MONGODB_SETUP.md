# Quick Start - MongoDB Atlas Integration

## ✅ Configuration Complete

Your Sentinel backend is now configured to use **MongoDB Atlas** cloud database.

## Next Steps

### 1. Restart Backend Server

Your current backend needs to restart to connect to MongoDB Atlas:

```powershell
# The server will auto-restart (you're running with --reload)
# Or manually restart:
taskkill /F /IM python.exe
.\venv\Scripts\python -m uvicorn app.main:app --reload
```

### 2. Verify Connection

Watch the terminal for:
```
✅ sentinel.starting
✅ mongodb.connected (to MongoDB Atlas)
✅ mongodb.indexes_created
✅ sentinel.ready
```

### 3. Test Upload

Upload an image/video through your frontend or:
```bash
curl -X POST "http://localhost:8000/api/v1/detect/upload" -F "file=@test.jpg"
```

### 4. Check MongoDB Atlas

1. Visit [MongoDB Atlas Dashboard](https://cloud.mongodb.com)
2. Go to your Cluster → Browse Collections
3. Find `sentinel_detections` database
4. Check `detections` collection

## What Changed

- ✅ `.env` configured with MongoDB Atlas URL
- ✅ All detection results now saved to cloud
- ✅ File system still stores images (hybrid approach)
- ✅ No Docker MongoDB needed

Your detection uploads will automatically save metadata to MongoDB Atlas! 🚀
