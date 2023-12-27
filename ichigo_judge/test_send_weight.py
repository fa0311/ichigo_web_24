import serial
import time
import random

# ----------------------------------------------------------------
# 重量データテスト用プログラム
# ----------------------------------
# 下記socatコマンドで仮想シリアル作成し, 対向テストを行う
# socat -d -d pty,raw,echo=0 pty,raw,echo=0

if __name__ == "__main__":
    ser = serial.Serial('/dev/pts/18', 115200, timeout=3)

    while (True):
        # 100グラム ±5 でデータ送信を行う
        weight = 100.0 + 5.0*random.random()
        ser.write(f"{weight}\n".encode())
        print(f"weight={weight}")
        time.sleep(0.1)
