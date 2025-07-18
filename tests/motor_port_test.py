import pypot.dynamixel as pd
from serial.serialutil import SerialException

ports = ['/dev/ttyACM0']
baudrates = [1000000, 57600, 115200]
protocols = ['Dxl320IO', 'DxlIO']

for port in ports:
    for br in baudrates:
        for proto in protocols:
            print(f"\n Testing {proto} on {port} @ {br} bps...")
            try:
                if proto == 'Dxl320IO':
                    dxl_io = pd.Dxl320IO(port, br)
                else:
                    dxl_io = pd.DxlIO(port, br)
                ids = dxl_io.scan(range(1, 20))
                print(f"SUCCESS: Found IDs: {ids}")
            except SerialException as se:
                print(f"Serial error: {se}")
            except Exception as e:
                print(f" Failed: {e}")
