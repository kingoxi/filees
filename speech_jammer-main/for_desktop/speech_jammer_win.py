#!/usr/bin/env python3

import sounddevice as sd
import random
import threading

def callback(indata, outdata, frames, time, status):
    if status:
        print(status)
    outdata[:] = indata[:, :2]

def main():
    random.seed()
    print("Press Return to start/stop or 'q' for terminate:")
    
    stream = None
    while True:
        user_input = input()
        if user_input == 'q':
            print("Program terminated.")
            if stream is not None and stream.active:
                stream.stop()
            break
        elif user_input == '':
            if stream is None or not stream.active:
                # Stream başlat
                latency = random.randint(180, 200) / 1000
                stream = sd.Stream(latency=latency, callback=callback)
                stream.start()
                print("Program started.")
            else:
                # Stream durdur
                stream.stop()
                print("Program stopped...")

if __name__ == "__main__":
    main()