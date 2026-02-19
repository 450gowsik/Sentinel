import cv2
import time

def find_camera():
    print("Searching for working camera...")
    for index in range(10):
        print(f"Checking index {index}...")
        
        # Try DSHOW
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ SUCCESS: Camera found at index {index} using CAP_DSHOW")
                cap.release()
                return
            cap.release()
            
        # Try MSMF
        cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ SUCCESS: Camera found at index {index} using CAP_MSMF")
                cap.release()
                return
            cap.release()
            
    print("❌ FAILURE: No working camera found on indices 0-9")

if __name__ == "__main__":
    find_camera()
