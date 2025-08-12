from pypot.dynamixel import Dxl320IO

dxl = Dxl320IO('/dev/ttyACM0', baudrate=57600)

for motor_id in range(1, 6):
    try:
        print(dxl.ping(motor_id))

        print(f"Motor {motor_id} está ativo.")
    except Exception:
        print(f"[!] Motor {motor_id} não respondeu ao ping!")

dxl.close()
