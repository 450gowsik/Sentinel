import asyncio
import websockets
import json

async def test():
    url = "ws://localhost:8000/ws/live/cam_0"
    print(f"Connecting to {url}...")
    try:
        ws = await asyncio.wait_for(
            websockets.connect(url),
            timeout=5
        )
        print("Connected!")
        
        for i in range(3):
            try:
                data = await asyncio.wait_for(ws.recv(), timeout=15)
                msg = json.loads(data)
                print(f"Frame {i+1}: type={msg.get('type')}, idx={msg.get('frame_idx')}, "
                      f"demo={msg.get('demo_mode')}, "
                      f"person_count={msg.get('metadata', {}).get('person_count')}")
            except asyncio.TimeoutError:
                print(f"Frame {i+1}: TIMEOUT waiting for data")
                break
            except Exception as e:
                print(f"Frame {i+1}: ERROR: {e}")
                break
        
        await ws.close()
        print("Done!")
    except asyncio.TimeoutError:
        print("FAILED: Connection timed out")
    except Exception as e:
        print(f"FAILED: {e}")

asyncio.run(test())
