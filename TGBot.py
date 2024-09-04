import json
import time
import requests
import base64
import datetime
import os
import config
from telebot import TeleBot
from telebot.types import InputMediaPhoto


# Класс для генерации изображений
class Text2ImageAPI:
    def __init__(self, url, api_key, secret_key, save_directory='photos'):
        self.URL = url
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }
        self.save_directory = save_directory
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

    def get_model(self):
        response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
        data = response.json()

        # Проверка на наличие данных
        if not data or 'id' not in data[0]:
            raise ValueError("Не удалось получить модель. Ответ API: {}".format(data))

        return data[0]['id']

    def generate(self, prompt, model, images=1, width=1024, height=1024, style=2):
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "generateParams": {
                "query": f"{prompt}",
                "style": style
            }
        }

        data = {
            'model_id': (None, model),
            'params': (None, json.dumps(params), 'application/json')
        }
        response = requests.post(self.URL + 'key/api/v1/text2image/run', headers=self.AUTH_HEADERS, files=data)
        data = response.json()
        print(f"[DEBUG] Запрос на генерацию отправлен. UUID: {data['uuid']}")
        return data['uuid']

    def check_generation(self, request_id, attempts=10, delay=10):
        print(f"[DEBUG] Проверка статуса генерации для UUID: {request_id}")
        while attempts > 0:
            response = requests.get(self.URL + 'key/api/v1/text2image/status/' + request_id, headers=self.AUTH_HEADERS)
            data = response.json()
            print(f"[DEBUG] Статус генерации: {data['status']}")
            if data['status'] == 'DONE':
                return data['images']
            attempts -= 1
            time.sleep(delay)
        print("[DEBUG] Превышено максимальное количество попыток проверки статуса.")
        return None

    def save_image(self, base64_string, file_name):
        if base64_string.startswith('data:image/png;base64,'):
            base64_string = base64_string.split(',')[1]

        image_data = base64.b64decode(base64_string)
        full_file_path = os.path.join(self.save_directory, file_name)

        with open(full_file_path, 'wb') as image_file:
            image_file.write(image_data)
        print(f"[DEBUG] Изображение сохранено: {full_file_path}")

    def get_unique_file_name(self, base_name, extension):
        time_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_name = f"{base_name}_{time_stamp}{extension}"

        count = 1
        while os.path.exists(os.path.join(self.save_directory, unique_name)):
            unique_name = f"{base_name}_{time_stamp}_{count}{extension}"
            count += 1

        return unique_name


# Настройка Telegram-бота
TOKEN = config.BOT_TOKEN
bot = TeleBot(TOKEN)

# Инициализация API
api = Text2ImageAPI(url='https://api-key.fusionbrain.ai/', api_key=config.api_key, secret_key=config.secret_key)

try:
    model_id = api.get_model()
    print(f"[DEBUG] Модель успешно получена. ID модели: {model_id}")
except ValueError as e:
    print(f"Ошибка при получении модели: {e}")
    exit(1)

# Переменные для отслеживания состояния генерации
generating = False
current_prompt = ""
current_num_images = 0
current_style = 0


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "🌌 Добро пожаловать в мир визуальных чудес ArtGenie! \n"
                                       "\n🔮 Здесь вы можете создавать уникальные изображения с помощью магии команд. Начните свое путешествие с /generate и дайте волю своему воображению!\n"
                                       "\nВаши инструменты для творчества:\n"
                                       "\n✨ /generate – откройте двери в мир новых образов\n"
                                       "✨ /retry – попробуйте снова и создайте шедевр\n"
                                       "✨ /stop - остановите поток идей\n"
                                       "✨ /help - помощь с командами")


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id, "\nВаши инструменты для творчества:\n"
                                       "\n✨ /generate – откройте двери в мир новых образов\n"
                                       "✨ /retry – попробуйте снова и создайте шедевр\n"
                                       "✨ /stop - остановите поток идей")


@bot.message_handler(commands=['generate'])
def generate_image(message):
    global generating
    generating = False
    bot.send_message(message.chat.id, "Введите текст для генерации изображения:")


@bot.message_handler(commands=['retry'])
def retry_message(message):
    global generating
    if generating:
        bot.send_message(message.chat.id, "Генерация уже идет. Пожалуйста, дождитесь её завершения или остановите с помощью /stop.")
    else:
        generating = False
        bot.send_message(message.chat.id, "Введите текст для генерации изображения:")


@bot.message_handler(commands=['stop'])
def stop_generation(message):
    global generating
    generating = False
    bot.send_message(message.chat.id, "Генерация остановлена. Вы можете начать заново с командой /generate.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global generating, current_prompt
    if not generating:
        chat_id = message.chat.id
        current_prompt = message.text
        bot.send_message(chat_id, "Введите количество изображений (1-10):")
        bot.register_next_step_handler(message, process_num_images, current_prompt)  # Передаем prompt


def process_num_images(message, prompt):
    global generating, current_num_images
    chat_id = message.chat.id
    if message.text.startswith('/'):
        return  # Игнор команд

    try:
        current_num_images = int(message.text)
        bot.send_message(chat_id, "Выберите стиль изображения (1-4): \n 1 - kandinsky \n 2 - детальный \n 3 - аниме \n 4 - default")
        bot.register_next_step_handler(message, process_style, prompt)  # Передаем prompt
    except ValueError:
        bot.send_message(chat_id, "Пожалуйста, введите корректное число.")
        bot.register_next_step_handler(message, process_num_images, prompt)  # Передаем prompt


def process_style(message, prompt):
    global generating, current_style
    chat_id = message.chat.id
    if message.text.startswith('/'):
        return  # Игнорируем команды, если они введены во время ввода стиля

    try:
        current_style = int(message.text)
        if current_style < 1 or current_style > 4:
            raise ValueError("Стиль должен быть от 1 до 4.")

        # Примерное время ожидания
        estimated_time = current_num_images * 1  # 1 минута за каждое изображение
        bot.send_message(chat_id, f"Ожидайте, примерное время ожидания: {estimated_time} минут.")

        generating = True
        image_files = []  # Список для хранения имен файлов изображений
        for i in range(current_num_images):
            if not generating:
                bot.send_message(chat_id, "Генерация была остановлена.")
                return

            try:
                uuid = api.generate(prompt, model_id, images=1, style=current_style)
                images = api.check_generation(uuid)
            except requests.exceptions.ReadTimeout:
                bot.send_message(chat_id, "Запрос к API завершился таймаутом. Пожалуйста, попробуйте снова.")
                return
            except Exception as e:
                bot.send_message(chat_id, f"Произошла ошибка при генерации изображения: {str(e)}")
                return

            if images:
                for j, img in enumerate(images):
                    file_name = api.get_unique_file_name('изображение', '.png')
                    api.save_image(img, file_name)
                    image_files.append(os.path.join(api.save_directory, file_name))
            else:
                bot.send_message(chat_id, "Не удалось сгенерировать изображения.")
                return

        # Отправка изображений партиями по 10
        for i in range(0, len(image_files), 10):
            media = []
            for file_path in image_files[i:i + 10]:
                media.append(InputMediaPhoto(open(file_path, 'rb')))

            try:
                bot.send_media_group(chat_id, media)
            except Exception as e:
                bot.send_message(chat_id, f"Произошла ошибка при отправке изображений: {str(e)}")
                return

    except ValueError as e:
        bot.send_message(chat_id, str(e))
        bot.register_next_step_handler(message, process_style, prompt)  # Передаем prompt


if __name__ == '__main__':
    bot.polling(skip_pending=True, timeout=30)