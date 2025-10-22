#!/usr/bin/env python3

import sounddevice as sd
import numpy as np
import queue
import threading

class SpeechJammer:
    def __init__(self, delay=0.3, invert_phase=False, output_device=None):
        self.delay = delay  # saniye cinsinden gecikme
        self.invert_phase = invert_phase
        self.output_device = output_device
        self.sample_rate = 44100
        self.channels = 2
        self.buffer = queue.Queue()
        self.stream = None

    def callback(self, indata, outdata, frames, time, status):
        if status:
            print(status)
        
        # Giriş verisini buffer'a koy
        self.buffer.put(indata.copy())
        
        # Gecikme süresine karşılık gelen frame sayısı
        delay_frames = int(self.delay * self.sample_rate)
        
        # Buffer'da yeterli veri var mı kontrol et
        if self.buffer.qsize() > delay_frames // frames:
            try:
                # Gecikmiş veriyi al
                delayed_data = self.buffer.get()
                # Eğer kanal sayıları uyuşmuyorsa, uygun hale getir
                if delayed_data.shape[1] != outdata.shape[1]:
                    # Kanal uyumsuzluğunu gider: ilk kanalları kopyala
                    min_channels = min(delayed_data.shape[1], outdata.shape[1])
                    outdata[:, :min_channels] = delayed_data[:, :min_channels]
                    # Kalan kanalları sıfırla
                    if outdata.shape[1] > min_channels:
                        outdata[:, min_channels:] = 0
                else:
                    outdata[:] = delayed_data
                
                # İsteğe bağlı faz ters çevirme
                if self.invert_phase:
                    outdata[:] = -outdata
            except queue.Empty:
                print("Buffer yeterli değil, sıfır dolduruluyor.")
                outdata[:] = 0
        else:
            # Henüz yeterli veri yoksa, sıfır ver
            outdata[:] = 0

    def start(self):
        # Cihaz bilgilerini al
        devices = sd.query_devices()
        if self.output_device is not None:
            # Çıkış cihazının kanal sayısını al
            self.channels = devices[self.output_device]['max_output_channels']
            # Eğer çıkış cihazı 2 kanaldan az ise, 2 yapalım (genellikle stereo)
            if self.channels < 2:
                self.channels = 2
        else:
            # Varsayılan çıkış cihazının kanal sayısı
            self.channels = devices[sd.default.device[1]]['max_output_channels']
            if self.channels < 2:
                self.channels = 2

        self.sample_rate = sd.query_devices(self.output_device)['default_samplerate']

        self.stream = sd.Stream(
            device=(None, self.output_device),
            samplerate=self.sample_rate,
            blocksize=1024,
            latency='low',
            channels=(2, self.channels),  # Giriş 2 kanal (mikrofon), çıkış bulduğumuz kanal sayısı
            callback=self.callback
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

def main():
    print("Speech Jammer Programı")
    print("Mevcut cihazlar:")
    print(sd.query_devices())
    
    # Bluetooth cihazını otomatik bul
    target_output_device = "Redmi Buds 6 Play"  # Kendi cihazınızın adına göre değiştirin
    output_device = None
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if target_output_device.lower() in device['name'].lower() and device['max_output_channels'] > 0:
            output_device = i
            print(f"Bluetooth çıkış cihazı bulundu: {device['name']} (ID: {i})")
            break
    
    if output_device is None:
        print("Bluetooth çıkış cihazı bulunamadı. Varsayılan cihaz kullanılacak.")
        output_device = sd.default.device[1]  # Varsayılan çıkış cihazı
    
    jammer = SpeechJammer(delay=0.3, invert_phase=False, output_device=output_device)
    
    print("Press Enter to start/stop, 'q' to quit:")
    
    while True:
        user_input = input()
        if user_input == 'q':
            print("Program sonlandırılıyor.")
            jammer.stop()
            break
        else:
            if jammer.stream and jammer.stream.active:
                jammer.stop()
                print("Durduruldu.")
            else:
                try:
                    jammer.start()
                    print("Başlatıldı. Gecikme: {} ms".format(jammer.delay * 1000))
                except Exception as e:
                    print(f"Hata: {e}")

if __name__ == "__main__":
    main()