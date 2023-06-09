import requests
import time
import random

if __name__ == "__main__":
    class_id = random.randint(0, 3)
    count = 0
    while(True):
        if (count % 30) == 0:
            class_id = random.randint(0, 3)
        requests.get(f"http://localhost:8000/v1/speech/play?class_id={class_id}")
        print(f"class_id={class_id}")
        time.sleep(0.1)
        count += 1
        if 30 < count:
            count = 0
