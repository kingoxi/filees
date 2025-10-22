#!/usr/bin/env python3

import sounddevice as sd
import numpy as np
import threading
import time
import keyboard
import random
import sys

class SpeechJammer:
    def __init__(self, delay=0.18, feedback_gain=0.8, output_device=None):
        self.delay = delay
        self.feedback_gain = feedback_gain
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
            print(f"Ses durumu: {status}")
        
        # Kanal uyumluluğunu sağla
        try:
            if indata.shape[1] != outdata.shape[1]:
                # Kanal sayıları farklıysa uyumla
                if indata.shape[1] == 1 and outdata.shape[1] == 2:
                    # Mono -> Stereo
                    outdata[:] = np.repeat(indata, 2, axis=1)
                elif indata.shape[1] == 4 and outdata.shape[1] == 2:
                    # 4 kanal -> Stereo
                    mixed = np.mean(indata, axis=1, keepdims=True)
                    outdata[:] = np.repeat(mixed, 2, axis=1)
                else:
                    # Genel çözüm
                    min_channels = min(indata.shape[1], outdata.shape[1])
                    outdata[:, :min_channels] = indata[:, :min_channels]
            else:
                outdata[:] = indata
                
            # Gecikmeli sesi hesapla ve uygula
            for i in range(frames):
                read_pos = (self.write_position - self.buffer_size) % self.buffer_size
                delayed_sample = self.audio_buffer[read_pos] * self.feedback_gain
                self.audio_buffer[self.write_position] = outdata[i]
                outdata[i] = delayed_sample
                self.write_position = (self.write_position + 1) % self.buffer_size
                
        except Exception as e:
            print(f"Ses işleme hatası: {e}")
    
    def start(self):
        if not self.running:
            try:
                # Cihaz bilgilerini al
                input_info = sd.query_devices(sd.default.device[0])
                output_info = sd.query_devices(self.output_device)
                
                print(f"Giriş cihazı: {input_info['name']}")
                print(f"Çıkış cihazı: {output_info['name']}")
                print(f"Giriş kanalları: {input_info['max_input_channels']}")
                print(f"Çıkış kanalları: {output_info['max_output_channels']}")
                
                # Kanal sayılarını belirle
                input_channels = min(2, input_info['max_input_channels'])
                output_channels = min(2, output_info['max_output_channels'])
                
                self.stream = sd.Stream(
                    device=(sd.default.device[0], self.output_device),
                    samplerate=self.sample_rate,
                    blocksize=512,  # Daha büyük buffer daha kararlı
                    latency='high',  # Daha yüksek gecikme ama daha kararlı
                    channels=(input_channels, output_channels),
                    callback=self.callback,
                    dtype='float32'
                )
                
                self.stream.start()
                self.running = True
                self.led_status = True
                print("✅ Speech Jammer başarıyla başlatıldı!")
                return True
                
            except Exception as e:
                print(f"❌ Hata: {e}")
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
            print("⏹️ Speech Jammer durduruldu")

def find_audio_device():
    """Ses cihazlarını bul ve uygun olanı seç"""
    devices = sd.query_devices()
    
    print("Mevcut ses cihazları:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']} (IN: {device['max_input_channels']}, OUT: {device['max_output_channels']})")
    
    # Öncelikle Bluetooth cihazları ara
    bluetooth_keywords = ['bose', 'sony', 'jbl', 'airpods', 'bt', 'bluetooth', 'kulaklık']
    
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            device_name = device['name'].lower()
            for keyword in bluetooth_keywords:
                if keyword in device_name:
                    print(f"🎧 Bluetooth cihazı bulundu: {device['name']} (ID: {i})")
                    return i
    
    # Varsayılan çıkış cihazını kullan
    try:
        default_output = sd.default.device[1]
        print(f"🔊 Varsayılan çıkış cihazı: {devices[default_output]['name']} (ID: {default_output})")
        return default_output
    except:
        # Eğer varsayılan yoksa, ilk çıkış cihazını bul
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                print(f"🔊 Çıkış cihazı olarak seçildi: {device['name']} (ID: {i})")
                return i
    
    print("❌ Uygun çıkış cihazı bulunamadı!")
    return None

def led_indicator(jammer):
    """LED yerine konsolda görsel gösterge"""
    states = ["🔴", "⭕"]
    state_idx = 0
    while True:
        if jammer.led_status:
            print(f"{states[state_idx]} SPEECH JAMMER AKTİF - Gecikme: {jammer.delay*1000:.0f}ms - Şiddet: %{jammer.feedback_gain*100:.0f}", end="\r")
            state_idx = (state_idx + 1) % 2
        else:
            print("⚪ SPEECH JAMMER PASİF - SPACE tuşuna basın", end="\r")
        time.sleep(0.5)

def main():
    print("🎤 SPEECH JAMMER - KONUŞMA KESİCİ")
    print("=" * 50)
    
    # Ses cihazını bul
    output_device = find_audio_device()
    if output_device is None:
        print("Ses cihazı bulunamadı. Program sonlandırılıyor.")
        return
    
    # Speech Jammer'ı oluştur
    jammer = SpeechJammer(
        delay=0.18,
        feedback_gain=0.7,  # Başlangıçta daha düşük şiddet
        output_device=output_device
    )
    
    # LED göstergesi için thread
    led_thread = threading.Thread(target=led_indicator, args=(jammer,), daemon=True)
    led_thread.start()
    
    # Otomatik başlat
    print("\n🔄 Otomatik başlatılıyor...")
    time.sleep(1)
    if jammer.start():
        print("✅ Otomatik başlatma başarılı!")
    else:
        print("❌ Otomatik başlatma başarısız! Manuel başlatmayı deneyin.")
    
    print("\n🎮 KONTROLLER:")
    print("SPACE = Aç/Kapa")
    print("↑/↓ = Gecikmeyi artır/azalt")
    print("→/← = Ses şiddetini artır/azalt") 
    print("R = Rastgele gecikme (180-220ms)")
    print("ESC veya Q = Çıkış")
    
    try:
        while True:
            # SPACE tuşu - Aç/Kapa
            if keyboard.is_pressed('space'):
                if jammer.running:
                    jammer.stop()
                else:
                    jammer.start()
                time.sleep(0.5)
            
            # YUKARI ok - Gecikmeyi artır
            elif keyboard.is_pressed('up'):
                jammer.delay = min(0.3, jammer.delay + 0.01)
                print(f"⏰ Gecikme: {jammer.delay*1000:.0f}ms")
                time.sleep(0.2)
            
            # AŞAĞI ok - Gecikmeyi azalt
            elif keyboard.is_pressed('down'):
                jammer.delay = max(0.05, jammer.delay - 0.01)
                print(f"⏰ Gecikme: {jammer.delay*1000:.0f}ms")
                time.sleep(0.2)
            
            # SAĞ ok - Ses şiddetini artır
            elif keyboard.is_pressed('right'):
                jammer.feedback_gain = min(1.0, jammer.feedback_gain + 0.05)
                print(f"🔊 Ses şiddeti: %{jammer.feedback_gain*100:.0f}")
                time.sleep(0.2)
            
            # SOL ok - Ses şiddetini azalt
            elif keyboard.is_pressed('left'):
                jammer.feedback_gain = max(0.1, jammer.feedback_gain - 0.05)
                print(f"🔊 Ses şiddeti: %{jammer.feedback_gain*100:.0f}")
                time.sleep(0.2)
            
            # R - Rastgele gecikme
            elif keyboard.is_pressed('r'):
                jammer.delay = random.uniform(0.18, 0.22)
                if jammer.running:
                    jammer.stop()
                    jammer.start()
                print(f"🎲 Rastgele gecikme: {jammer.delay*1000:.0f}ms")
                time.sleep(0.5)
            
            # ESC veya Q - Çıkış
            elif keyboard.is_pressed('esc') or keyboard.is_pressed('q'):
                print("\n👋 Program sonlandırılıyor...")
                break
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n👋 Program sonlandırılıyor...")
    finally:
        jammer.stop()
        print("✅ Program başarıyla sonlandırıldı.")
        sys.exit(0)

if __name__ == "__main__":
    main()