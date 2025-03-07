import os
import sys
import time
import math
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment

class WhisperTranscriber:
    def __init__(self):
        # Загружаем переменные окружения
        load_dotenv()
        
        # Получаем API ключ из переменных окружения
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("API ключ OpenAI не найден. Убедитесь, что он указан в файле .env")
        
        # Создаем клиента OpenAI (только новая версия API 1.x)
        self.client = OpenAI(api_key=api_key)
        print("[INFO] Инициализирован клиент OpenAI API v1.x")
    
    def transcribe_audio(self, audio_file_path, language=None):
        """
        Транскрибировать аудиофайл с использованием Whisper API
        
        Args:
            audio_file_path (str): Путь к аудиофайлу для транскрибации
            language (str, optional): Код языка для транскрибации (например, "ru", "en", "kk")
            
        Returns:
            str: Текст транскрибации
        """
        print(f"[INFO] Начало транскрибации файла: {audio_file_path}")
        if language:
            print(f"[INFO] Выбран язык для транскрибации: {language}")
        else:
            print(f"[INFO] Язык будет определен автоматически")
            
        start_time = time.time()
        
        try:
            # Проверяем размер файла
            file_size = os.path.getsize(audio_file_path) / (1024 * 1024)  # в МБ
            print(f"[INFO] Размер файла: {file_size:.2f} МБ")
            
            # Если файл больше 25 МБ, используем метод с разбивкой на части
            if file_size > 25:
                print(f"[INFO] Файл превышает 25 МБ, используется метод разбиения на части")
                return self.transcribe_audio_chunked(audio_file_path, language=language)
            
            print(f"[INFO] Отправка файла в Whisper API...")
            
            # Отправляем запрос в API
            with open(audio_file_path, "rb") as audio_file:
                # Создаем параметры для запроса
                params = {
                    "model": "whisper-1",
                    "file": audio_file
                }
                
                # Добавляем параметр языка, если он указан
                if language:
                    params["language"] = language
                
                # Отправляем запрос
                response = self.client.audio.transcriptions.create(**params)
                result = response.text
            
            elapsed_time = time.time() - start_time
            print(f"[INFO] Транскрибация завершена за {elapsed_time:.2f} секунд")
            print(f"[INFO] Результат: {result[:100]}...")
            
            return result
        
        except Exception as e:
            import traceback
            print(f"[ERROR] Ошибка при транскрибации: {e}")
            traceback.print_exc()
            return f"Ошибка транскрибации: {str(e)}"
    
    def transcribe_audio_chunked(self, audio_path, language=None, max_duration=5 * 60 * 1000):
        """
        Функция для транскрибации аудиофайла на части, чтобы соответствовать ограничениям размера API.
        
        Args:
            audio_path (str): Путь к аудиофайлу для транскрибации
            language (str, optional): Код языка для транскрибации (например, "ru", "en", "kk")
            max_duration (int): Максимальная длительность чанка в миллисекундах
            
        Returns:
            str: Объединенный текст транскрибации всех частей
        """
        try:
            print(f"[INFO] Начало транскрибации файла по частям: {audio_path}")
            if language:
                print(f"[INFO] Выбран язык для транскрибации: {language}")
            else:
                print(f"[INFO] Язык будет определен автоматически")
                
            start_time_total = time.time()
            
            # Создание временной папки для хранения аудио частей
            temp_dir = os.path.join(os.path.dirname(audio_path), "temp_audio_chunks")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"[INFO] Создана временная папка для частей: {temp_dir}")
            
            # Загрузка аудиофайла
            print(f"[INFO] Загрузка аудиофайла...")
            audio = AudioSegment.from_file(audio_path)
            audio_length_sec = len(audio) / 1000
            print(f"[INFO] Длительность аудио: {audio_length_sec:.2f} секунд")
            
            # Инициализация переменных для обработки аудио чанков
            current_start_time = 0  # Текущее время начала чанка
            chunk_index = 1         # Индекс текущего чанка
            transcriptions = []     # Список для хранения всех транскрибаций
            
            estimated_chunks = math.ceil(len(audio) / max_duration)
            print(f"[INFO] Примерное количество частей: {estimated_chunks}")
            
            # Обработка аудиофайла чанками
            while current_start_time < len(audio):
                chunk_start_time = time.time()
                print(f"[INFO] Обработка части {chunk_index}/{estimated_chunks}...")
                
                # Выделение чанка из аудиофайла
                chunk_end_time = min(current_start_time + max_duration, len(audio))
                chunk = audio[current_start_time:chunk_end_time]
                chunk_length_sec = len(chunk) / 1000
                
                print(f"[INFO] Часть {chunk_index}: {current_start_time/1000:.2f}с - {chunk_end_time/1000:.2f}с (длительность: {chunk_length_sec:.2f}с)")
                
                # Формирование имени и пути файла чанка
                chunk_name = f"chunk_{chunk_index}.wav"
                chunk_path = os.path.join(temp_dir, chunk_name)
                
                # Экспорт чанка в формате wav
                print(f"[INFO] Экспорт части {chunk_index} в {chunk_path}...")
                chunk.export(chunk_path, format="wav")
                
                # Проверка размера файла чанка на соответствие лимиту API
                chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                print(f"[INFO] Размер части {chunk_index}: {chunk_size_mb:.2f} МБ")
                
                if os.path.getsize(chunk_path) > 25 * 1024 * 1024:  # 25 MB
                    print(f"[INFO] Часть {chunk_index} превышает лимит размера API ({chunk_size_mb:.2f} МБ > 25 МБ). Уменьшаем длительность...")
                    max_duration = int(max_duration * 0.9)  # Уменьшение длительности чанка на 10%
                    print(f"[INFO] Новая максимальная длительность: {max_duration/1000:.2f} секунд")
                    os.remove(chunk_path)  # Удаление чанка, превышающего лимит
                    continue
                
                # Открытие файла чанка для чтения в двоичном режиме
                with open(chunk_path, "rb") as src_file:
                    print(f"[INFO] Отправка части {chunk_index} в Whisper API...")
                    try:
                        api_start_time = time.time()
                        
                        # Создаем параметры для запроса
                        params = {
                            "model": "whisper-1",
                            "file": src_file
                        }
                        
                        # Добавляем параметр языка, если он указан
                        if language:
                            params["language"] = language
                        
                        # Отправляем запрос
                        response = self.client.audio.transcriptions.create(**params)
                        result_text = response.text
                        
                        api_elapsed_time = time.time() - api_start_time
                        print(f"[INFO] Часть {chunk_index} транскрибирована за {api_elapsed_time:.2f} секунд")
                        print(f"[INFO] Результат части {chunk_index}: {result_text[:50]}...")
                        
                        # Добавление результата транскрибации в список транскрипций
                        transcriptions.append(result_text)
                    except Exception as e:
                        print(f"[ERROR] Произошла ошибка при транскрибации части {chunk_index}: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                
                # Удаление обработанного файла чанка
                os.remove(chunk_path)
                print(f"[INFO] Удален временный файл части {chunk_index}")
                
                # Переход к следующему чанку
                current_start_time = chunk_end_time
                chunk_index += 1
                
                chunk_elapsed_time = time.time() - chunk_start_time
                print(f"[INFO] Обработка части {chunk_index-1} завершена за {chunk_elapsed_time:.2f} секунд")
            
            # Удаление временной папки с чанками
            try:
                os.rmdir(temp_dir)
                print(f"[INFO] Удалена временная папка {temp_dir}")
            except:
                print(f"[WARNING] Не удалось удалить временную папку {temp_dir}")
            
            # Объединение всех транскрипций в одну строку
            full_transcription = " ".join(transcriptions)
            
            total_elapsed_time = time.time() - start_time_total
            print(f"[INFO] Полная транскрибация завершена за {total_elapsed_time:.2f} секунд")
            print(f"[INFO] Итоговый результат ({len(full_transcription)} символов): {full_transcription[:100]}...")
            
            return full_transcription
            
        except Exception as e:
            print(f"[ERROR] Ошибка при транскрибации в режиме частей: {e}")
            import traceback
            traceback.print_exc()
            return f"Ошибка транскрибации: {str(e)}"