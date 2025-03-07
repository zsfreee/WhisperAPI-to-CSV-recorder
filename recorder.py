import os
import wave
import pyaudio
import threading
import time
import array
import math
from datetime import datetime

class AudioRecorder:
    def __init__(self, output_directory="recordings"):
        self.output_directory = output_directory
        self.is_recording = False
        self.is_monitoring = False
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.stream = None
        self.monitor_stream = None
        self.thread = None
        self.monitor_thread = None
        self.current_file = None
        self.callback = None
        self.current_volume = 0
        self.device_index = None
        
        # Создаем директорию для записей, если она не существует
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        # Параметры записи аудио
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024
    
    def get_available_devices(self):
        """
        Получить список доступных устройств записи
        
        Returns:
            list: Список словарей с информацией об устройствах
        """
        devices = []
        try:
            for i in range(self.audio.get_device_count()):
                try:
                    dev_info = self.audio.get_device_info_by_index(i)
                    
                    # Проверяем, является ли устройство входным (имеет входные каналы)
                    if dev_info.get('maxInputChannels') > 0:
                        # Попытка очистки имени устройства от странных символов
                        name = dev_info.get('name', 'Неизвестное устройство')
                        
                        # Очистка имени от специальных символов и кодировок
                        try:
                            # Попытка распознать кодировку
                            name = name.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                            
                            # Чистим имя от непечатаемых символов
                            import re
                            name = re.sub(r'[^\x20-\x7E\u0400-\u04FF]', '', name)
                            name = name.strip()
                            
                            # Если имя пустое после очистки, используем просто индекс
                            if not name:
                                name = f"Устройство #{i}"
                        except:
                            name = f"Устройство #{i}"
                        
                        # Добавляем информацию об устройстве
                        devices.append({
                            'index': i,
                            'name': name,
                            'channels': dev_info.get('maxInputChannels', 1),
                            'default_rate': dev_info.get('defaultSampleRate', 44100)
                        })
                except Exception as e:
                    print(f"[WARNING] Ошибка при получении информации об устройстве {i}: {e}")
                    continue
                    
            # Добавляем "Системное устройство по умолчанию" как первый элемент
            devices.insert(0, {
                'index': None,  # None означает использование устройства по умолчанию
                'name': "Системное устройство по умолчанию",
                'channels': 1,
                'default_rate': 44100
            })
            
            return devices
            
        except Exception as e:
            print(f"[ERROR] Ошибка при получении списка устройств: {e}")
            # Возвращаем хотя бы устройство по умолчанию
            return [{
                'index': None,
                'name': "Системное устройство по умолчанию",
                'channels': 1,
                'default_rate': 44100
            }]
    
    def set_device(self, device_index):
        """
        Установить устройство для записи по индексу
        
        Args:
            device_index (int): Индекс устройства
        """
        self.device_index = device_index
        print(f"[INFO] Установлено устройство записи с индексом {device_index}")
        
        # Если мониторинг активен, перезапускаем его с новым устройством
        if self.is_monitoring:
            self.stop_monitoring()
            self.start_monitoring(self.callback)
    
    def start_monitoring(self, volume_callback=None):
        """
        Начать мониторинг уровня громкости
        
        Args:
            volume_callback (callable): Функция обратного вызова для отображения уровня громкости
        """
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.callback = volume_callback
        
        # Запускаем мониторинг в отдельном потоке
        self.monitor_thread = threading.Thread(target=self._monitor_thread)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        print("[INFO] Мониторинг уровня громкости начат")
    
    def stop_monitoring(self):
        """Остановить мониторинг уровня громкости"""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        
        # Дожидаемся завершения потока мониторинга
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        # Закрываем поток мониторинга
        if self.monitor_stream:
            try:
                self.monitor_stream.stop_stream()
                self.monitor_stream.close()
            except Exception as e:
                print(f"[WARNING] Ошибка при закрытии потока мониторинга: {e}")
            self.monitor_stream = None
        
        print("[INFO] Мониторинг уровня громкости остановлен")
    
    def _monitor_thread(self):
        """Функция мониторинга, выполняемая в отдельном потоке"""
        try:
            # Открываем поток для мониторинга
            input_params = {
                'format': self.format,
                'channels': self.channels,
                'rate': self.rate,
                'input': True,
                'frames_per_buffer': self.chunk
            }
            
            # Добавляем индекс устройства, только если он не None
            if self.device_index is not None:
                input_params['input_device_index'] = self.device_index
            
            # Открываем поток с нужными параметрами
            self.monitor_stream = self.audio.open(**input_params)
            
            # Цикл мониторинга
            while self.is_monitoring:
                try:
                    # Читаем данные из потока
                    data = self.monitor_stream.read(self.chunk, exception_on_overflow=False)
                    
                    # Рассчитываем текущую громкость для визуализации
                    if self.callback:
                        volume = self._calculate_volume(data)
                        self.current_volume = volume
                        self.callback(volume)
                    
                    # Небольшая пауза для снижения нагрузки на CPU
                    time.sleep(0.01)
                except Exception as e:
                    print(f"[WARNING] Ошибка при мониторинге: {e}")
                    time.sleep(0.1)
            
        except Exception as e:
            print(f"[ERROR] Ошибка при инициализации мониторинга: {e}")
            import traceback
            traceback.print_exc()
    
    def start_recording(self, volume_callback=None):
        """
        Начать запись аудио
        
        Args:
            volume_callback (callable): Функция обратного вызова для отображения уровня громкости
        """
        if self.is_recording:
            return
        
        self.is_recording = True
        self.frames = []
        
        # Сохраняем callback, если он передан
        if volume_callback:
            self.callback = volume_callback
        
        # Формируем имя файла на основе текущего времени
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = os.path.join(self.output_directory, f"recording_{timestamp}.wav")
        
        # Если мониторинг активен, останавливаем его
        if self.is_monitoring:
            self.stop_monitoring()
        
        # Подготавливаем параметры для потока аудио
        input_params = {
            'format': self.format,
            'channels': self.channels,
            'rate': self.rate,
            'input': True,
            'frames_per_buffer': self.chunk
        }
        
        # Добавляем индекс устройства, только если он не None
        if self.device_index is not None:
            input_params['input_device_index'] = self.device_index
        
        # Открываем поток аудио для записи
        self.stream = self.audio.open(**input_params)
        
        # Запускаем запись в отдельном потоке
        self.thread = threading.Thread(target=self._record)
        self.thread.start()
        
        print(f"[INFO] Начата запись в файл {self.current_file}")
        return self.current_file
    
    def _record(self):
        """Функция записи, выполняемая в отдельном потоке"""
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
                
                # Рассчитываем текущую громкость для визуализации
                if self.callback:
                    volume = self._calculate_volume(data)
                    self.current_volume = volume
                    self.callback(volume)
            except Exception as e:
                print(f"[WARNING] Ошибка при записи: {e}")
    
    def _calculate_volume(self, data):
        """
        Рассчитать текущую громкость аудио
        
        Args:
            data (bytes): Бинарные данные аудио
            
        Returns:
            float: Нормализованная громкость от 0.0 до 1.0
        """
        try:
            # Конвертируем бинарные данные в массив
            values = array.array('h', data)
            # Берем среднеквадратичное значение амплитуды
            rms = math.sqrt(sum(float(sample * sample) for sample in values) / len(values))
            
            # Нормализуем громкость в диапазон от 0.0 до 1.0
            # Типичные значения для тихой речи - около 500, громкой - до 10000
            normalized_volume = min(1.0, rms / 10000.0)
            return normalized_volume
        except:
            return 0
    
    def get_current_volume(self):
        """
        Получить текущий уровень громкости
        
        Returns:
            float: Нормализованная громкость от 0.0 до 1.0
        """
        return self.current_volume
    
    def stop_recording(self):
        """Остановить запись и сохранить файл"""
        if not self.is_recording:
            return None
        
        print(f"[DEBUG] Остановка записи...")
        self.is_recording = False
        
        # Дожидаемся завершения потока записи
        if self.thread and self.thread.is_alive():
            print(f"[DEBUG] Ожидание завершения потока записи...")
            self.thread.join(timeout=2.0)  # Добавляем таймаут
            print(f"[DEBUG] Поток записи завершен")
        
        # Закрываем поток
        if self.stream:
            print(f"[DEBUG] Закрытие аудио-потока...")
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"[WARNING] Ошибка при закрытии аудио-потока: {e}")
            self.stream = None
        
        # Сохраняем аудио в файл
        if self.frames:
            print(f"[DEBUG] Сохранение {len(self.frames)} фреймов в файл {self.current_file}...")
            try:
                with wave.open(self.current_file, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.format))
                    wf.setframerate(self.rate)
                    wf.writeframes(b''.join(self.frames))
                
                print(f"[DEBUG] Файл успешно сохранен: {self.current_file}")
                
                # Восстанавливаем мониторинг
                if self.callback:
                    self.start_monitoring(self.callback)
                    
                return self.current_file
            except Exception as e:
                print(f"[ERROR] Ошибка при сохранении файла: {e}")
                import traceback
                traceback.print_exc()
                return None
        else:
            print(f"[WARNING] Нет фреймов для сохранения")
            
            # Восстанавливаем мониторинг
            if self.callback:
                self.start_monitoring(self.callback)
                
            return None
    
    def __del__(self):
        """Очистка ресурсов при удалении объекта"""
        self.stop_monitoring()
        
        if self.stream:
            self.stream.close()
            
        if self.monitor_stream:
            self.monitor_stream.close()
            
        if self.audio:
            self.audio.terminate()