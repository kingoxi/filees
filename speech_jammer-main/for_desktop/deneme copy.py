#!/usr/bin/env python3

import sounddevice as sd
import numpy as np
import threading
import time
import keyboard  # pip install keyboard
import random
import sys

class SpeechJammer:
    def __init__(self, delay=0.18, feedback_gain=0.8, output_device=None):
        self.delay = delay  # Gecikme süresi (saniye)
        self.feedback_gain = feedback_gain  # Geri besleme şiddeti
        self.output_device = output_device
        self.sample_rate = 44100
        self.buffer_size = int(self.delay * self.sample_rate)
        self.audio_buffer = np.zeros((self.buffer_size, 2))
        self.write_position = 0
        self.stream = None
        self.running = False
        self.led_status = False
        
    def callback(self, indata, outdata, frames, time, status):
        if status:
            print(status)
        
        # Kanal uyumluluğunu sağla
        if indata.shape[1] == 4 and outdata.shape[1] == 2:
            # 4 kanaldan 2 kanala dönüştür
            input_audio = np.mean(indata, axis=1, keepdims=True)
            input_audio = np.repeat(input_audio, 2, axis=1)
        else:
            min_channels = min(indata.shape[1], outdata.shape[1])
            input_audio = np.zeros((frames, outdata.shape[1]))
            input_audio[:, :min_channels] = indata[:, :min_channels]
        
        # Gecikmeli sesi hesapla
        delayed_audio = np.zeros((frames, 2))
        for i in range(frames):
            read_pos = (self.write_position - self.buffer_size) % self.buffer_size
            delayed_audio[i] = self.audio_buffer[read_pos]
            self.audio_buffer[self.write_position] = input_audio[i]
            self.write_position = (self.write_position + 1) % self.buffer_size
        
        # Gecikmeli sesi çıkışa ver + geri besleme
        outdata[:] = delayed_audio * self.feedback_gain
        
    def start(self):
        if not self.running:
            try:
                self.running = True
                self.stream = sd.Stream(
                    device=(None, self.output_device),
                    samplerate=self.sample_rate,
                    blocksize=256,
                    latency='low',
                    channels=2,
                    callback=self.callback,
                    dtype='float32'
                )
                self.stream.start()
                self.led_status = True
                return True
            except Exception as e:
                print(f"Hata: {e}")
                self.running = False
                return False
        return True
    
    def stop(self):
        if self.running:
            self.running = False
            self.led_status = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

def find_bluetooth_device():
    """Bluetooth kulaklığı otomatik bul"""
    devices = sd.query_devices()
    bluetooth_keywords = ['Redmi Buds 6 Play', 'K55', 'TWS', 'airpods', 'bt', 'bluetooth']
    
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 2:  # Çıkış cihazı
            device_name = device['name'].lower()
            for keyword in bluetooth_keywords:
                if keyword in device_name:
                    print(f"Bluetooth cihazı bulundu: {device['name']} (ID: {i})")
                    return i
    
    # Bluetooth bulunamazsa varsayılan çıkış cihazını kullan
    default_output = sd.default.device[1]
    print(f"Bluetooth cihazı bulunamadı. Varsayılan cihaz kullanılacak: {devices[default_output]['name']}")
    return default_output

def led_indicator(jammer):
    """LED yerine konsolda görsel gösterge"""
    while True:
        if jammer.led_status:
            print("🔴", end="\r")  # Kırmızı nokta - aktif
        else:
            print("⚪", end="\r")  # Beyaz nokta - pasif
        time.sleep(0.5)

def main():
    print("🎤 Speech Jammer - Konuşma Kesici")
    print("=" * 40)
    
    # Bluetooth cihazını bul
    output_device = find_bluetooth_device()
    
    # Speech Jammer'ı başlat
    jammer = SpeechJammer(
        delay=0.18,  # 180ms gecikme
        feedback_gain=0.9,  # Ses şiddeti
        output_device=output_device
    )
    
    # LED göstergesi için thread
    led_thread = threading.Thread(target=led_indicator, args=(jammer,), daemon=True)
    led_thread.start()
    
    print("\n🎮 Kontroller:")
    print("SPACE = Başlat/Durdur")
    print("↑/↓ = Gecikmeyi artır/azalt (+/- 10ms)")
    print("→/← = Ses şiddetini artır/azalt")
    print("ESC veya Q = Çıkış")
    print("\n⏰ Mevcut gecikme: 180ms")
    print("🔊 Ses şiddeti: %90")
    
    try:
        while True:
            # SPACE tuşu - Başlat/Durdur
            if keyboard.is_pressed('space'):
                if jammer.running:
                    jammer.stop()
                    print(f"⏹️  Durduruldu")
                else:
                    if jammer.start():
                        print(f"▶️  Başlatıldı - Gecikme: {jammer.delay*1000:.0f}ms")
                    else:
                        print("❌ Başlatılamadı!")
                time.sleep(0.5)  # Tuş baskısını önle
            
            # YUKARI ok - Gecikmeyi artır
            elif keyboard.is_pressed('up'):
                jammer.delay = min(0.5, jammer.delay + 0.01)
                if jammer.running:
                    jammer.stop()
                    jammer.start()
                print(f"⏰ Gecikme: {jammer.delay*1000:.0f}ms")
                time.sleep(0.3)
            
            # AŞAĞI ok - Gecikmeyi azalt
            elif keyboard.is_pressed('down'):
                jammer.delay = max(0.05, jammer.delay - 0.01)
                if jammer.running:
                    jammer.stop()
                    jammer.start()
                print(f"⏰ Gecikme: {jammer.delay*1000:.0f}ms")
                time.sleep(0.3)
            
            # SAĞ ok - Ses şiddetini artır
            elif keyboard.is_pressed('right'):
                jammer.feedback_gain = min(1.0, jammer.feedback_gain + 0.1)
                print(f"🔊 Ses şiddeti: %{jammer.feedback_gain*100:.0f}")
                time.sleep(0.3)
            
            # SOL ok - Ses şiddetini azalt
            elif keyboard.is_pressed('left'):
                jammer.feedback_gain = max(0.1, jammer.feedback_gain - 0.1)
                print(f"🔊 Ses şiddeti: %{jammer.feedback_gain*100:.0f}")
                time.sleep(0.3)
            
            # ESC veya Q - Çıkış
            elif keyboard.is_pressed('esc') or keyboard.is_pressed('q'):
                print("\n👋 Program sonlandırılıyor...")
                break
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n👋 Program sonlandırılıyor...")
    finally:
        jammer.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()