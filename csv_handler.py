import os
import csv
import pandas as pd
from datetime import datetime

class CSVHandler:
    def __init__(self, file_path=None):
        self.file_path = file_path
        self.headers = ["Имя менеджера", "Дата", "ID", "Резюме"]
        self.unsaved_changes = False
    
    def set_file_path(self, file_path):
        """Установить путь к файлу CSV"""
        self.file_path = file_path
        self.unsaved_changes = False
    
    def create_new_file(self, file_path):
        """Создать новый CSV файл с заголовками"""
        # Проверяем, существует ли директория, иначе создаем её
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Создаем новый файл с заголовками
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.headers)
        
        self.file_path = file_path
        self.unsaved_changes = False
        return file_path
    
    def add_entry(self, manager_name, date, conversation_id, summary):
        """
        Добавить новую запись в CSV файл
        
        Args:
            manager_name (str): Имя менеджера
            date (str): Дата в формате ГГГГ-ММ-ДД
            conversation_id (str): ID переговора
            summary (str): Резюме переговора
            
        Returns:
            bool: True, если запись успешно добавлена
        """
        try:
            # Проверяем, существует ли файл
            file_exists = os.path.isfile(self.file_path)
            
            # Открываем файл для добавления записи
            with open(self.file_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # Если файл только что создан, добавляем заголовки
                if not file_exists:
                    writer.writerow(self.headers)
                
                # Добавляем новую запись
                writer.writerow([manager_name, date, conversation_id, summary])
            
            self.unsaved_changes = False
            return True
            
        except Exception as e:
            print(f"Ошибка при добавлении записи в CSV: {e}")
            self.unsaved_changes = True
            return False
    
    def read_entries(self):
        """
        Чтение всех записей из CSV файла
        
        Returns:
            list: Список всех записей из файла
        """
        try:
            if not os.path.exists(self.file_path):
                return []
            
            # Чтение данных с помощью pandas для удобства
            df = pd.read_csv(self.file_path, encoding='utf-8-sig')
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Ошибка при чтении CSV: {e}")
            return []
    
    def has_unsaved_changes(self):
        """Проверить, есть ли несохраненные изменения"""
        return self.unsaved_changes