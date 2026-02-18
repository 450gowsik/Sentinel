import cv2
import time

url = "http://10.1.3.175:8080/video"
# Try both /video and /video.mjpeg as some apps use different endpoints
urls = [
    "http://10.1.3.175:8080/video",
    "http://10.1.3.175:8080/video.mjpeg",
    "http://10.1.3.175:8080/shot.jpg"
]

print("Testing OpenCV VideoCapture...")
for u in urls:
    print(f"Trying: {u}")
    cap = cv2.VideoCapture(u)
    if cap.isOpened():
        print(f"SUCCESS: Connected to {u}")
        ret, frame = cap.read()
        if ret:
            print(f"SUCCESS: Read frame {frame.shape}")
        else:
            print("FAILED: Could not read frame")
        cap.release()
    else:
        print("FAILED: Could not open stream")
    print("-" * 20)
