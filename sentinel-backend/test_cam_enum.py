import cv2

def list_cameras():
    print("Scanning for cameras...")
    available = []
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"  Camera {i}: OPENED")
            ret, frame = cap.read()
            if ret:
                print(f"    Frame: {frame.shape}")
                available.append(i)
            else:
                print("    No frame")
            cap.release()
        else:
            print(f"  Camera {i}: FAILED")
            
    print(f"Available indices: {available}")

if __name__ == "__main__":
    list_cameras()
