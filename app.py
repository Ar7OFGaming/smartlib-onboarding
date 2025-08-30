
import streamlit as st
import requests
import json
import urllib.parse

st.title("SmartLib AI: Настройка папок")

query_params = st.query_params
chat_id = query_params.get("chat_id")
# Новый параметр, который будет приходить от Google
auth_code = query_params.get("code")

# URL вебхука "Обмен кода на токен и получение папок"
GET_FOLDERS_WEBHOOK = "https://goooglovskiq.app.n8n.cloud/webhook/1665a6b8-e161-4117-bb03-6c5db9b7a148"
# URL вебхука "Запуск индексации"
START_INDEXING_WEBHOOK = "https://goooglovskiq.app.n8n.cloud/webhook/438e832a-14fc-406a-87b4-d1711ab9c326"
# "Магическая" ссылка, которую мы возьмем из n8n
# ВАЖНО: Redirect URI в этой ссылке должен вести ОБРАТНО на это же Streamlit-приложение!
# Пример правильной настройки
STREAMLIT_URL = "https://smartlib-app-fcz2i2s8uzbn2ffp5wsbhm.streamlit.app"
# Вставьте сюда ваш Client ID
CLIENT_ID = "340752343067-79ipapn7o97qd8ibqvgpjg4687fm7jo7.apps.googleusercontent.com"
# Ваши scopes, склеенные через пробел
SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"

# --- СОБИРАЕМ ПРАВИЛЬНУЮ "МАГИЧЕСКУЮ" ССЫЛКУ ---
# --- СОБИРАЕМ ПРАВИЛЬНУЮ "МАГИЧЕСКУЮ" ССЫЛКУ ---
MAGIC_AUTH_LINK = (
    f"https://accounts.google.com/o/oauth2/v2/auth?"
    f"scope={urllib.parse.quote(SCOPES)}&"
    f"redirect_uri={STREAMLIT_URL}&"
    f"response_type=code&"
    f"client_id={CLIENT_ID}&"
    f"access_type=offline&prompt=consent"  # Убрал & в конце и добавил f в начале
)

# --- Основная логика приложения ---
st.title("SmartLib AI: Настройка папок")

query_params = st.query_params

# Получаем параметры и берем ПЕРВЫЙ элемент из списка
chat_id = query_params.get("chat_id")
auth_code = query_params.get("code")
state = query_params.get("state")


# --- РЕЖИМ 1: Пользователь только что пришел из Telegram ---
if not auth_code:
    if not chat_id:
        st.error("Ошибка: Не найден ID пользователя. Пожалуйста, вернитесь в Telegram и перейдите по ссылке снова.")
    else:
        st.info("Для начала, пожалуйста, предоставьте доступ к вашему аккаунту Google.")
        # Формируем персональную ссылку, добавляя chat_id в параметр state
        final_auth_link = f"{MAGIC_AUTH_LINK}&state={chat_id}"
        # Используем st.page_link для более красивой кнопки-ссылки
        st.link_button("Войти через Google и выбрать папки", final_auth_link, use_container_width=True)

# --- РЕЖИМ 2: Пользователь вернулся от Google с кодом авторизации ---
else:
    if not state:
        st.error("Ошибка: Потерян идентификатор сессии (state). Пожалуйста, начните процесс заново из Telegram.")
    else:
        try:
            with st.spinner('Получаем доступ и загружаем список ваших папок...'):
                # Отправляем код в n8n, чтобы получить список папок
                payload = {"code": auth_code, "state": state} # Передаем state
                response = requests.post(GET_FOLDERS_WEBHOOK, json=payload)
                response.raise_for_status() # Проверка на ошибки HTTP (4xx, 5xx)

                response_data = response.json()
                folders = response_data.get("folders", [])

                if not folders:
                    st.warning("Не удалось найти папки на вашем Google Диске или произошла ошибка.")
                else:
                    st.success("Доступ получен! Теперь выберите папки для анализа:")

                    selected_folder_ids = []
                    for folder in folders:
                        if folder.get('name') and folder.get('id'):
                            if st.checkbox(folder.get('name'), key=folder.get('id')):
                                selected_folder_ids.append(folder.get('id'))

                    if st.button("Завершить и начать индексацию", use_container_width=True):
                        if not selected_folder_ids:
                            st.warning("Пожалуйста, выберите хотя бы одну папку.")
                        else:
                            with st.spinner('Отправляем задачи на индексацию...'):
                                # chat_id берем из state, который вернулся от Google
                                indexing_payload = { "chat_id": state, "folder_ids": selected_folder_ids }
                                indexing_response = requests.post(START_INDEXING_WEBHOOK, json=indexing_payload)
                                indexing_response.raise_for_status()

                                st.success("Отлично! Ваши папки отправлены на обработку. Ассистент будет готов к работе в течение нескольких минут. Можете возвращаться в Telegram.")
                                st.balloons()

        except requests.exceptions.HTTPError as http_err:
            st.error(f"Произошла сетевая ошибка при обращении к серверу: {http_err}")
            st.code(http_err.response.text) # Показываем ответ сервера для отладки
        except Exception as e:
            st.error(f"Произошла непредвиденная ошибка: {e}")

            st.write("Пожалуйста, попробуйте авторизоваться еще раз, вернувшись в Telegram.")

