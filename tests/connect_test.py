from pypot.dynamixel import Dxl320IO

dxl = Dxl320IO('/dev/ttyACM0', baudrate=1_000_000)
print("[OK] Conectado!")
dxl.disable_torque([1,2,3,4,5])
dxl.close()