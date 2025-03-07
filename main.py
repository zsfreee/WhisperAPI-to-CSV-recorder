import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime
import threading
import time

from recorder import AudioRecorder
from transcriber import WhisperTranscriber
from csv_handler import CSVHandler

# Устанавливаем тему для customtkinter
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Настройка основного окна
        self.title("Система записи резюме переговоров")
        self.geometry("800x600")
        
        # Добавляем иконку приложения
        if os.path.exists("icon.ico"):
            self.iconbitmap("icon.ico")
        else:
            print("[WARNING] Файл иконки icon.ico не найден")
            
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Инициализация компонентов
        self.recorder = AudioRecorder()
        self.transcriber = WhisperTranscriber()
        self.csv_handler = CSVHandler()
        
        # Переменные для отслеживания состояния
        self.is_recording = False
        self.is_transcribing = False
        self.current_audio_file = None
        self.current_csv_file = None
        self.selected_language = tk.StringVar(value="ru")
        
        # Создание интерфейса
        self.create_widgets()
        
        # Запуск мониторинга уровня громкости
        self.recorder.start_monitoring(self.update_volume_indicator)
        
        # Центрируем окно на экране
        self.center_window()
        
        # Открытие окна на полный экран
        self.after(100, self.maximize_window)
    
    def maximize_window(self):
        """Открыть окно на весь экран"""
        self.state('zoomed')  # Для Windows
        # Для Linux/macOS: self.attributes('-zoomed', True)
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        # Создаем основной фрейм для элементов управления
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Верхняя секция: выбор или создание CSV файла
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Кнопки для работы с CSV файлами
        ctk.CTkLabel(file_frame, text="Файл CSV:").pack(side=tk.LEFT, padx=5)
        
        self.file_path_var = tk.StringVar()
        self.file_path_entry = ctk.CTkEntry(file_frame, textvariable=self.file_path_var, width=400)
        self.file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.browse_button = ctk.CTkButton(file_frame, text="Выбрать файл", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.new_file_button = ctk.CTkButton(file_frame, text="Создать новый", command=self.create_new_file)
        self.new_file_button.pack(side=tk.LEFT, padx=5)
        
        # Секция для настройки записи
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Выбор устройства записи
        device_frame = ctk.CTkFrame(settings_frame)
        device_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(device_frame, text="Устройство записи:", width=150).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Получаем список доступных устройств
        self.devices = self.recorder.get_available_devices()
        
        # Создаем ComboBox для выбора устройства с фиксированной шириной
        device_names = [dev['name'] for dev in self.devices]
        self.device_var = tk.StringVar()
        
        if device_names:
            self.device_var.set(device_names[0])  # По умолчанию - системное устройство
        
        self.device_combobox = ctk.CTkOptionMenu(
            device_frame, 
            values=device_names,
            variable=self.device_var,
            width=400, 
            dynamic_resizing=False,
            command=self.on_device_change
        )
        self.device_combobox.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # Выбор языка для транскрибации
        lang_frame = ctk.CTkFrame(settings_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(lang_frame, text="Язык распознавания:", width=150).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Создаем переключатели для выбора языка
        lang_options_frame = ctk.CTkFrame(lang_frame)
        lang_options_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.ru_radio = ctk.CTkRadioButton(
            lang_options_frame, 
            text="Русский",
            variable=self.selected_language,
            value="ru"
        )
        self.ru_radio.pack(side=tk.LEFT, padx=10)
        
        self.kk_radio = ctk.CTkRadioButton(
            lang_options_frame, 
            text="Казахский",
            variable=self.selected_language,
            value="kk"
        )
        self.kk_radio.pack(side=tk.LEFT, padx=10)
        
        self.en_radio = ctk.CTkRadioButton(
            lang_options_frame, 
            text="Английский",
            variable=self.selected_language,
            value="en"
        )
        self.en_radio.pack(side=tk.LEFT, padx=10)
        
        self.auto_radio = ctk.CTkRadioButton(
            lang_options_frame, 
            text="Авто-определение",
            variable=self.selected_language,
            value=""
        )
        self.auto_radio.pack(side=tk.LEFT, padx=10)
        
        # Секция для ввода данных
        data_frame = ctk.CTkFrame(self.main_frame)
        data_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Создаем поля ввода
        # Имя менеджера
        name_frame = ctk.CTkFrame(data_frame)
        name_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(name_frame, text="Имя менеджера:", width=150).pack(side=tk.LEFT, padx=5, pady=5)
        self.manager_name_var = tk.StringVar()
        self.manager_name_entry = ctk.CTkEntry(name_frame, textvariable=self.manager_name_var, width=400)
        self.manager_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Дата
        date_frame = ctk.CTkFrame(data_frame)
        date_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(date_frame, text="Дата:", width=150).pack(side=tk.LEFT, padx=5, pady=5)
        self.date_picker = DateEntry(date_frame, width=20, background='darkblue',
                                     foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.date_picker.pack(side=tk.LEFT, padx=5, pady=5)
        # Устанавливаем текущую дату
        self.date_picker.set_date(datetime.now())
        
        # ID переговора
        id_frame = ctk.CTkFrame(data_frame)
        id_frame.pack(fill=tk.X, pady=5)
        
        ctk.CTkLabel(id_frame, text="ID переговора:", width=150).pack(side=tk.LEFT, padx=5, pady=5)
        self.conversation_id_var = tk.StringVar()
        self.conversation_id_entry = ctk.CTkEntry(id_frame, textvariable=self.conversation_id_var, width=400)
        self.conversation_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Секция для записи и транскрибации
        record_frame = ctk.CTkFrame(self.main_frame)
        record_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Кнопка записи
        self.record_button_text = tk.StringVar(value="Запись")
        self.record_button = ctk.CTkButton(
            record_frame, 
            textvariable=self.record_button_text,
            command=self.toggle_recording,
            fg_color="darkred",
            hover_color="red"
        )
        self.record_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Индикатор уровня громкости
        self.volume_frame = ctk.CTkFrame(record_frame, width=200, height=20)
        self.volume_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
        
        self.volume_indicator = ctk.CTkProgressBar(self.volume_frame)
        self.volume_indicator.pack(fill=tk.X, padx=5, pady=5)
        self.volume_indicator.set(0)  # Начальное значение - тишина
        
        # Метка статуса
        self.status_var = tk.StringVar(value="Готов к записи")
        status_label = ctk.CTkLabel(record_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Секция для результата транскрибации
        transcription_frame = ctk.CTkFrame(self.main_frame)
        transcription_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(transcription_frame, text="Результат транскрибации:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.transcription_text = ctk.CTkTextbox(transcription_frame, height=200, wrap="word")
        self.transcription_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки внизу
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.save_button = ctk.CTkButton(
            button_frame, 
            text="Сохранить в CSV", 
            command=self.save_to_csv,
            state="disabled"
        )
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.clear_button = ctk.CTkButton(
            button_frame, 
            text="Очистить поля", 
            command=self.clear_fields
        )
        self.clear_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Если есть устройства, выбираем первое по умолчанию
        if self.devices:
            self.on_device_change(self.device_var.get())
    
    def on_device_change(self, device_name):
        """
        Обработчик изменения устройства записи
        
        Args:
            device_name (str): Название выбранного устройства
        """
        # Ищем устройство по имени
        selected_device = None
        for device in self.devices:
            if device['name'] == device_name:
                selected_device = device
                break
        
        if selected_device:
            # Устанавливаем выбранное устройство
            self.recorder.set_device(selected_device['index'])
            self.status_var.set(f"Выбрано устройство: {device_name}")
            print(f"[INFO] Выбрано устройство: {device_name} (индекс: {selected_device['index']})")
    
    def browse_file(self):
        """Открыть диалог выбора CSV файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите CSV файл",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.file_path_var.set(file_path)
            self.csv_handler.set_file_path(file_path)
            self.current_csv_file = file_path
            self.status_var.set(f"Выбран файл: {os.path.basename(file_path)}")
            print(f"[INFO] Выбран CSV файл: {file_path}")
    
    def create_new_file(self):
        """Создать новый CSV файл"""
        file_path = filedialog.asksaveasfilename(
            title="Создать новый CSV файл",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            self.csv_handler.create_new_file(file_path)
            self.file_path_var.set(file_path)
            self.current_csv_file = file_path
            self.status_var.set(f"Создан новый файл: {os.path.basename(file_path)}")
            print(f"[INFO] Создан новый CSV файл: {file_path}")
    
    def toggle_recording(self):
        """Переключение состояния записи"""
        if not self.current_csv_file:
            messagebox.showerror("Ошибка", "Сначала выберите или создайте CSV файл.")
            return
        
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def update_volume_indicator(self, volume):
        """
        Обновить индикатор уровня громкости
        
        Args:
            volume (float): Текущий уровень громкости (от 0.0 до 1.0)
        """
        # Обновляем индикатор в основном потоке
        self.after(10, lambda: self.volume_indicator.set(volume))
    
    def start_recording(self):
        """Начать запись аудио"""
        if not self.current_csv_file:
            messagebox.showerror("Ошибка", "Сначала выберите или создайте CSV файл для сохранения данных.")
            return
            
        self.is_recording = True
        self.record_button_text.set("Остановить")
        self.status_var.set("Идет запись...")
        
        print("[INFO] Начало записи аудио...")
        
        # Начинаем запись в отдельном потоке, передавая функцию обратного вызова
        self.recording_thread = threading.Thread(target=self._recording_thread)
        self.recording_thread.daemon = True
        self.recording_thread.start()
    
    def _recording_thread(self):
        """Функция записи, выполняемая в отдельном потоке"""
        # Передаем функцию обратного вызова для обновления индикатора громкости
        self.current_audio_file = self.recorder.start_recording(self.update_volume_indicator)
        
        # Обновляем UI во время записи (мигающая точка)
        dots = 0
        while self.is_recording:
            dots = (dots + 1) % 4
            status_text = "Идет запись" + "." * dots
            self.status_var.set(status_text)
            time.sleep(0.5)
    
    def stop_recording(self):
        """Остановить запись аудио и начать транскрибацию"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.record_button_text.set("Запись")
        self.status_var.set("Остановка записи...")
        
        # Сбрасываем индикатор уровня громкости
        self.volume_indicator.set(0)
        
        # Остановка записи и получение пути к файлу
        audio_file = self.recorder.stop_recording()
        
        if not audio_file:
            self.status_var.set("Ошибка при сохранении аудио")
            return
            
        # Отключаем кнопку записи во время транскрибации
        self.record_button.configure(state="disabled")
        
        # Показываем сообщение о начале транскрибации
        self.status_var.set("Начало транскрибации...")
        
        print(f"[DEBUG] Аудиофайл сохранен: {audio_file}")
        print(f"[DEBUG] Размер файла: {os.path.getsize(audio_file) / 1024} КБ")
        print(f"[DEBUG] Начинаем транскрибацию...")
        
        # Обновляем интерфейс перед запуском долгой операции
        self.update_idletasks()
        
        # Запускаем транскрибацию в отдельном потоке
        transcription_thread = threading.Thread(target=self._transcribe_thread, args=(audio_file,))
        transcription_thread.daemon = True
        transcription_thread.start()
    
    def _transcribe_thread(self, audio_file):
        """Функция транскрибации, выполняемая в отдельном потоке"""
        try:
            # Обновляем статус в UI из отдельного потока
            self.after(100, lambda: self.status_var.set("Транскрибация через Whisper API..."))
            
            # Получаем выбранный язык
            language = self.selected_language.get()
            
            # Информация о выбранном языке
            if language:
                lang_name = {
                    'ru': 'русском',
                    'en': 'английском',
                    'kk': 'казахском'
                }.get(language, language)
                print(f"[INFO] Выбран язык распознавания: {language} ({lang_name})")
                self.after(100, lambda: self.status_var.set(f"Транскрибация на {lang_name} языке..."))
            else:
                print(f"[INFO] Выбрано автоматическое определение языка")
            
            # Проверяем размер файла
            file_size = os.path.getsize(audio_file) / (1024 * 1024)  # в МБ
            print(f"[DEBUG] Размер файла для транскрибации: {file_size:.2f} МБ")
            
            # Запускаем индикатор прогресса в отдельном потоке
            self.is_transcribing = True
            progress_thread = threading.Thread(target=self._show_transcription_progress)
            progress_thread.daemon = True
            progress_thread.start()
            
            # Получаем транскрипцию с учетом выбранного языка
            start_time = time.time()
            print(f"[DEBUG] Запуск transcribe_audio с файлом {audio_file}")
            transcription = self.transcriber.transcribe_audio(audio_file, language)
            print(f"[DEBUG] Транскрибация завершена")
            
            # Останавливаем индикацию прогресса
            self.is_transcribing = False
            elapsed_time = time.time() - start_time
            
            # Обновляем UI с результатом транскрибации
            self.after(100, lambda: self._update_ui_with_transcription(transcription, elapsed_time))
            
        except Exception as e:
            print(f"[ERROR] Ошибка в _transcribe_thread: {e}")
            import traceback
            traceback.print_exc()
            self.is_transcribing = False
            
            # Обновляем UI с ошибкой
            self.after(100, lambda: self._update_ui_with_error(str(e)))
    
    def _update_ui_with_transcription(self, transcription, elapsed_time):
        """Обновляет UI с результатом транскрибации"""
        # Обновляем текстовое поле с результатом
        self.transcription_text.delete("0.0", tk.END)
        self.transcription_text.insert("0.0", transcription)
        
        # Обновляем статус
        self.status_var.set(f"Транскрибация завершена за {elapsed_time:.1f} секунд!")
        
        # Активируем кнопки
        self.save_button.configure(state="normal")
        self.record_button.configure(state="normal")
    
    def _update_ui_with_error(self, error_message):
        """Обновляет UI с сообщением об ошибке"""
        self.status_var.set(f"Ошибка: {error_message}")
        self.record_button.configure(state="normal")
        messagebox.showerror("Ошибка транскрибации", f"Произошла ошибка при транскрибации:\n\n{error_message}")
    
    def _show_transcription_progress(self):
        """Отображает прогресс транскрибации"""
        self.is_transcribing = True
        dots = 0
        spinner = ["|", "/", "-", "\\"]
        spinner_idx = 0
        seconds = 0
        
        while self.is_transcribing:
            dots = (dots + 1) % 4
            spinner_idx = (spinner_idx + 1) % len(spinner)
            
            if seconds >= 60:
                minutes = seconds // 60
                secs = seconds % 60
                time_str = f"{minutes}:{secs:02d}"
            else:
                time_str = f"{seconds} сек"
                
            status = f"Транскрибация {spinner[spinner_idx]} {time_str}"
            
            # Обновляем статус через метод after, чтобы избежать проблем с потоками
            self.after(10, lambda s=status: self.status_var.set(s))
            
            time.sleep(1)
            seconds += 1
            
            # Выходим из цикла, если флаг сброшен (транскрибация завершена или произошла ошибка)
            if not self.is_transcribing:
                break
    
    def save_to_csv(self):
        """Сохранить результаты в CSV файл"""
        manager_name = self.manager_name_var.get().strip()
        date = self.date_picker.get_date().strftime("%Y-%m-%d")
        conversation_id = self.conversation_id_var.get().strip()
        summary = self.transcription_text.get("0.0", tk.END).strip()
        
        # Проверка на заполненность полей
        if not manager_name:
            messagebox.showerror("Ошибка", "Введите имя менеджера")
            return
        
        if not conversation_id:
            messagebox.showerror("Ошибка", "Введите ID переговора")
            return
        
        if not summary:
            messagebox.showerror("Ошибка", "Нет текста транскрибации")
            return
        
        # Сохраняем в CSV
        success = self.csv_handler.add_entry(manager_name, date, conversation_id, summary)
        
        if success:
            messagebox.showinfo("Успех", "Данные успешно сохранены в CSV файл")
            self.status_var.set("Данные сохранены в CSV")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить данные в CSV файл")
    
    def clear_fields(self):
        """Очистить все поля ввода"""
        self.manager_name_var.set("")
        self.date_picker.set_date(datetime.now())
        self.conversation_id_var.set("")
        self.transcription_text.delete("0.0", tk.END)
        self.save_button.configure(state="disabled")
        self.volume_indicator.set(0)  # Сбросить индикатор уровня громкости
        self.status_var.set("Поля очищены")
    
    def on_close(self):
        """Обработчик закрытия окна"""
        if self.is_recording:
            result = messagebox.askyesno(
                "Подтверждение", 
                "Запись все еще идет. Вы уверены, что хотите закрыть приложение?"
            )
            if not result:
                return
            
            # Останавливаем запись
            self.recorder.stop_recording()
        
        # Проверяем наличие несохраненных изменений
        if self.csv_handler.has_unsaved_changes():
            result = messagebox.askyesno(
                "Несохраненные изменения", 
                "Имеются несохраненные изменения. Сохранить перед выходом?"
            )
            if result:
                self.save_to_csv()
        
        self.destroy()
        sys.exit()

def check_ffmpeg():
    """Проверка наличия FFmpeg в системе или в папке проекта"""
    import subprocess
    import os
    
    # Проверяем в PATH
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return True
    except:
        pass
    
    # Проверяем в папке проекта
    try:
        ffmpeg_path = os.path.join(os.getcwd(), 'ffmpeg', 'ffmpeg.exe')
        if os.path.exists(ffmpeg_path):
            os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
            return True
    except:
        pass
    
    # Проверяем в стандартных местах установки на Windows
    common_paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "FFmpeg", "bin"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "FFmpeg", "bin")
    ]
    
    for path in common_paths:
        if os.path.exists(os.path.join(path, "ffmpeg.exe")):
            os.environ["PATH"] += os.pathsep + path
            return True
    
    return False

def check_dependencies():
    """Проверка наличия необходимых зависимостей"""
    try:
        import openai
        print(f"[INFO] OpenAI версия: {openai.__version__}")
        
        # Проверка API ключа
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[WARNING] API ключ OpenAI не найден в переменных окружения")
            messagebox.showwarning(
                "API ключ не найден", 
                "API ключ OpenAI не найден. Убедитесь, что создали файл .env с переменной OPENAI_API_KEY."
            )
            return False
        
        # Проверка PyAudio
        import pyaudio
        p = pyaudio.PyAudio()
        input_devices = 0
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            if dev_info.get('maxInputChannels') > 0:
                input_devices += 1
        p.terminate()
        
        if input_devices == 0:
            print("[WARNING] Не найдено устройств записи звука")
            messagebox.showwarning(
                "Устройства записи не найдены", 
                "Не найдены устройства для записи звука. Проверьте, подключен ли микрофон."
            )
            return False
        
        print(f"[INFO] Найдено устройств записи звука: {input_devices}")
        
        # Проверка FFmpeg
        if not check_ffmpeg():
            print("[WARNING] FFmpeg не найден")
            messagebox.showwarning(
                "FFmpeg не найден", 
                "FFmpeg не найден. Некоторые функции работы с аудио могут быть недоступны."
            )
        
        return True
    
    except Exception as e:
        print(f"[ERROR] Ошибка при проверке зависимостей: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror(
            "Ошибка", 
            f"Ошибка при проверке зависимостей: {str(e)}"
        )
        return False

if __name__ == "__main__":
    print("[INFO] Запуск приложения...")
    print(f"[INFO] Текущая директория: {os.getcwd()}")
    
    # Создаем папку для записей
    os.makedirs("recordings", exist_ok=True)
    
    # Проверяем зависимости перед запуском
    if check_dependencies():
        app = App()
        app.mainloop()
    else:
        print("[ERROR] Невозможно запустить приложение из-за отсутствия необходимых зависимостей")