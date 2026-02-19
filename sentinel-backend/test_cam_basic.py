import cv2
import time

def test_camera():
    print("Testing Camera Access...")
    # Try DirectShow first
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("DirectShow failed, trying default...")
        cap = cv2.VideoCapture(0)
        
    if cap.isOpened():
        print("Camera Successfully Opened!")
        ret, frame = cap.read()
        if ret:
            print(f"Read frame successful. Shape: {frame.shape}")
        else:
            print("Failed to read frame.")
        cap.release()
    else:
        print("Could not open camera at all.")

if __name__ == "__main__":
    test_camera()
