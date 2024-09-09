import json
import time
import requests
import base64
import datetime
import os
import config
from telebot import TeleBot, types
from telebot.types import InputMediaPhoto
from threading import Thread
from dotenv import load_dotenv


load_dotenv()
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
            if not generating:
                print("[DEBUG] Генерация была остановлена.")
                return None
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


TOKEN = config.BOT_TOKEN
bot = TeleBot(TOKEN)

api1 = Text2ImageAPI(url='https://api-key.fusionbrain.ai/', api_key=config.api_key, secret_key=config.secret_key)
api2 = Text2ImageAPI(url='https://api-key.fusionbrain.ai/', api_key=config.api_key2, secret_key=config.secret_key2)
api3 = Text2ImageAPI(url='https://api-key.fusionbrain.ai/', api_key=config.api_key3, secret_key=config.secret_key3)

try:
    model_id1 = api1.get_model()
    model_id2 = api2.get_model()
    model_id3 = api3.get_model()
    print(
        f"[DEBUG] Модели успешно получены. ID модели 1: {model_id1}, ID модели 2: {model_id2}, ID модели 3: {model_id3}")
except ValueError as e:
    print(f"Ошибка при получении модели: {e}")
    exit(1)

generating = False
current_prompt = ""
current_num_images = 0
current_style = 0
previous_user_message_id = None
previous_bot_message_id = None

style_names = {
    1: "Kandinsky",
    2: "Детальный",
    3: "Аниме",
    4: "Default"
}


def get_time_string(minutes):
    """Функция для получения правильного склонения слова 'минута'."""
    if minutes % 10 == 1 and minutes % 100 != 11:
        return f"{minutes} минута"
    elif 2 <= minutes % 10 <= 4 and not (12 <= minutes % 100 <= 14):
        return f"{minutes} минуты"
    else:
        return f"{minutes} минут"


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "🌌 Добро пожаловать в мир визуальных чудес ArtGenie! \n"
                                      "\n🔮 Здесь вы можете создавать уникальные изображения с помощью магии команд. Начните свое путешествие с /generate и дайте волю своему воображению!\n"
                                      "\nВаши инструменты для творчества:\n"
                                      "\n✨ /generate – откройте двери в мир новых образов\n"
                                      "✨ /stop - остановите поток идей\n"
                                      "✨ /help - помощь с командами")


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(message.chat.id, "\nВаши инструменты для творчества:\n"
                                      "\n✨ /generate – откройте двери в мир новых образов\n"
                                      "✨ /stop - остановите поток идей")


@bot.message_handler(commands=['generate'])
def generate_image(message):
    global generating, previous_bot_message_id
    generating = False

    if previous_user_message_id:
        try:
            bot.delete_message(message.chat.id, previous_user_message_id)
        except Exception as e:
            print(f"[DEBUG] Не удалось удалить предыдущее сообщение пользователя: {e}")

    if previous_bot_message_id:
        try:
            bot.delete_message(message.chat.id, previous_bot_message_id)
        except Exception as e:
            print(f"[DEBUG] Не удалось удалить предыдущее сообщение бота: {e}")

    bot.delete_message(message.chat.id, message.message_id)

    msg = bot.send_message(message.chat.id, "Введите текст для генерации изображения:")
    previous_bot_message_id = msg.message_id


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global generating, current_prompt, previous_user_message_id, previous_bot_message_id, current_num_images, current_style
    if not generating:
        chat_id = message.chat.id
        current_prompt = message.text

        if previous_user_message_id:
            try:
                bot.delete_message(chat_id, previous_user_message_id)
            except Exception as e:
                print(f"[DEBUG] Не удалось удалить предыдущее сообщение пользователя: {e}")

        if previous_bot_message_id:
            try:
                bot.delete_message(chat_id, previous_bot_message_id)
            except Exception as e:
                print(f"[DEBUG] Не удалось удалить предыдущее сообщение бота: {e}")

        previous_user_message_id = message.message_id

        bot.delete_message(chat_id, message.message_id)

        msg = bot.send_message(chat_id, "Выберите количество изображений:", reply_markup=create_image_count_keyboard())
        previous_bot_message_id = msg.message_id


def create_image_count_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text='1', callback_data='num_images_1'),
        types.InlineKeyboardButton(text='3', callback_data='num_images_3'),
        types.InlineKeyboardButton(text='5', callback_data='num_images_5'),
        types.InlineKeyboardButton(text='10', callback_data='num_images_10'),
        types.InlineKeyboardButton(text='Введите количество', callback_data='num_images_input'),
    ]
    keyboard.add(*buttons)
    return keyboard


@bot.callback_query_handler(func=lambda call: call.data.startswith('num_images_'))
def handle_image_count_selection(call):
    global current_num_images, previous_bot_message_id
    if call.data == 'num_images_input':

        if previous_bot_message_id:
            try:
                bot.delete_message(call.message.chat.id, previous_bot_message_id)
            except Exception as e:
                print(f"[DEBUG] Не удалось удалить предыдущее сообщение бота: {e}")

        msg = bot.send_message(call.message.chat.id, "Введите количество изображений:")
        previous_bot_message_id = msg.message_id
        bot.register_next_step_handler(msg, process_image_count)
    else:
        current_num_images = int(call.data.split('_')[-1])

        bot.delete_message(call.message.chat.id, call.message.message_id)

        msg = bot.send_message(call.message.chat.id, "Выберите стиль изображения:",
                               reply_markup=create_style_keyboard())
        previous_bot_message_id = msg.message_id


def process_image_count(message):
    global current_num_images, previous_user_message_id, previous_bot_message_id
    try:
        current_num_images = int(message.text)
        if current_num_images <= 0:
            raise ValueError("Количество изображений должно быть положительным.")

        if previous_user_message_id:
            try:
                bot.delete_message(message.chat.id, previous_user_message_id)
            except Exception as e:
                print(f"[DEBUG] Не удалось удалить предыдущее сообщение пользователя: {e}")

        bot.delete_message(message.chat.id, message.message_id)

        if previous_bot_message_id:
            try:
                bot.delete_message(message.chat.id, previous_bot_message_id)
            except Exception as e:
                print(f"[DEBUG] Не удалось удалить предыдущее сообщение бота: {e}")

        msg = bot.send_message(message.chat.id, "Выберите стиль изображения:", reply_markup=create_style_keyboard())
        previous_bot_message_id = msg.message_id
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректное число.")
        bot.register_next_step_handler(message, process_image_count)


def create_style_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text='Kandinsky', callback_data='style_1'),
        types.InlineKeyboardButton(text='Детальный', callback_data='style_2'),
        types.InlineKeyboardButton(text='Аниме', callback_data='style_3'),
        types.InlineKeyboardButton(text='Default', callback_data='style_4'),
    ]
    keyboard.add(*buttons)
    return keyboard


@bot.callback_query_handler(func=lambda call: call.data.startswith('style_'))
def handle_style_selection(call):
    global current_style, generating
    current_style = int(call.data.split('_')[-1])

    if current_num_images <= 3:
        estimated_time = 1
    elif current_num_images <= 6:
        estimated_time = 2
    elif current_num_images <= 9:
        estimated_time = 3
    elif current_num_images <= 12:
        estimated_time = 4
    else:

        estimated_time = 4 + (current_num_images - 12 + 2) // 3

    time_string = get_time_string(estimated_time)

    stop_button = types.InlineKeyboardButton(text='Остановить генерацию', callback_data='stop_generation')
    keyboard = types.InlineKeyboardMarkup().add(stop_button)

    bot.delete_message(call.message.chat.id, call.message.message_id)

    style_name = style_names[current_style]

    final_message = (f"Промпт: '{current_prompt}', "
                     f"Количество изображений: '{current_num_images}', "
                     f"Выбранный стиль: '{style_name}'. "
                     f"Ожидайте, примерное время ожидания: {time_string}.")

    confirmation_msg = bot.send_message(call.message.chat.id, final_message, reply_markup=keyboard)
    previous_bot_message_id = confirmation_msg.message_id

    generating = True
    image_files = []

    print("[DEBUG] Начало генерации изображений.")

    def generate_with_api(api, model_id, num_images):
        if num_images > 0:
            print(f"[DEBUG] Генерация с API: {api.AUTH_HEADERS['X-Key']}")
            for i in range(num_images):
                if not generating:
                    print("[DEBUG] Генерация была остановлена.")
                    return

                try:
                    uuid = api.generate(current_prompt, model_id, images=1, style=current_style)
                    images = api.check_generation(uuid)
                except requests.exceptions.ReadTimeout:
                    if generating:
                        bot.send_message(call.message.chat.id,
                                         "Запрос к API завершился таймаутом. Пожалуйста, попробуйте снова.")
                    return
                except Exception as e:
                    if generating:
                        bot.send_message(call.message.chat.id, f"Произошла ошибка при генерации изображения: {str(e)}")
                    return

                if images:
                    for j, img in enumerate(images):
                        if not generating:
                            print("[DEBUG] Генерация была остановлена.")
                            return
                        file_name = api.get_unique_file_name('изображение', '.png')
                        api.save_image(img, file_name)
                        image_files.append(os.path.join(api.save_directory, file_name))
                else:
                    if generating:
                        print("[DEBUG] Не удалось сгенерировать изображения.")
                    return

    num_images_api1 = current_num_images // 3
    num_images_api2 = (current_num_images - num_images_api1) // 2
    num_images_api3 = current_num_images - num_images_api1 - num_images_api2

    if current_num_images > 2:
        thread1 = Thread(target=generate_with_api, args=(api1, model_id1, num_images_api1))
        thread2 = Thread(target=generate_with_api, args=(api2, model_id2, num_images_api2))
        thread3 = Thread(target=generate_with_api, args=(api3, model_id3, num_images_api3))

        thread1.start()
        thread2.start()
        thread3.start()

        thread1.join()
        thread2.join()
        thread3.join()
    else:

        if current_num_images == 1:
            generate_with_api(api1, model_id1, 1)
        else:
            generate_with_api(api1, model_id1, 1)
            generate_with_api(api2, model_id2, 1)

    if not image_files:
        bot.send_message(call.message.chat.id, "Не удалось сгенерировать изображения.")
        return

    for i in range(0, len(image_files), 10):
        media = []
        for file_path in image_files[i:i + 10]:
            media.append(InputMediaPhoto(open(file_path, 'rb')))

        try:
            media_group_msg = bot.send_media_group(call.message.chat.id, media)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Произошла ошибка при отправке изображений: {str(e)}")
            return

    buttons = [
        types.InlineKeyboardButton(text='Начать заново', callback_data='restart'),
    ]
    keyboard = types.InlineKeyboardMarkup().add(*buttons)
    bot.send_message(call.message.chat.id, "Что дальше?", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == 'restart')
def restart_generation(call):
    generate_image(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'stop_generation')
def stop_generation_callback(call):
    global generating
    generating = False
    bot.send_message(call.message.chat.id, "Генерация остановлена.")


if __name__ == '__main__':
    bot.polling(skip_pending=True, timeout=30)