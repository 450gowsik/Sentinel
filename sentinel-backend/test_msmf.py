import cv2

def list_cameras():
    print("Testing CAP_MSMF...")
    for i in range(2):
        print(f"Index {i}...")
        cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
        if cap.isOpened():
            print(f"  Camera {i}: OPENED (MSMF)")
            ret, frame = cap.read()
            if ret:
                print(f"    Frame: {frame.shape}")
                cap.release()
                return
            else:
                print("    No frame")
            cap.release()
        else:
            print(f"  Camera {i}: FAILED")
            
    print("No camera found with MSMF either.")

if __name__ == "__main__":
    list_cameras()
