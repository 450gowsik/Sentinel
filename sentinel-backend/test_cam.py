import cv2
import time

print("Testing camera access with cv2.CAP_DSHOW...")

def test_cam():
    # Try multiple times as per senior advice
    for i in range(3):
        print(f"Attempt {i+1}...")
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            print("  Failed to open camera.")
            time.sleep(1)
            continue
            
        print("  Camera opened successfully!")
        
        # Read a frame
        ret, frame = cap.read()
        if ret:
            print(f"  Frame captured! Shape: {frame.shape}")
            cap.release()
            return True
        else:
            print("  Camera opened but returned empty frame.")
            cap.release()
            time.sleep(1)
            
    print("All attempts failed.")
    return False

if __name__ == "__main__":
    success = test_cam()
    exit(0 if success else 1)
