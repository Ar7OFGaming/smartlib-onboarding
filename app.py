import streamlit as st
import requests
import json
import urllib.parse

# --------------------------------------------------------------------------
# ШАГ 1: ВАШИ ПЕРСОНАЛЬНЫЕ НАСТРОЙКИ
# --------------------------------------------------------------------------
STREAMLIT_URL = "https://smartlib-app-fcz2i2s8uzbn2ffp5wsbhm.streamlit.app"
CLIENT_ID = "340752343067-79ipapn7o97qd8ibqvgpjg4687fm7jo7.apps.googleusercontent.com"
GET_FOLDERS_WEBHOOK_URL = "https://gooooglovskiq.app.n.io/webhook/4aa31f22-b98e-4c4c-8c0f-93077cf63726" # Убедитесь, что это URL от workflow "Обмен Кода"
SAVE_FOLDERS_WEBHOOK_URL = "https://gooooglovskiq.app.n8n.cloud/webhook/438e832a-14fc-406a-87b4-d1711ab9c326" # Убедитесь, что это URL от workflow "Сохранение Выбора"
SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"

# --------------------------------------------------------------------------
# ШАГ 2: СБОРКА "МАГИЧЕСКОЙ" ССЫЛКИ
# --------------------------------------------------------------------------
MAGIC_AUTH_LINK = (
    f"https://accounts.google.com/o/oauth2/v2/auth?"
    f"scope={urllib.parse.quote(SCOPES)}&"
    f"redirect_uri={STREAMLIT_URL}&"
    f"response_type=code&"
    f"client_id={CLIENT_ID}&"
    f"access_type=offline&prompt=consent"
)

# --------------------------------------------------------------------------
# ШАГ 3: ОСНОВНАЯ ЛОГИКА ПРИЛОЖЕНИЯ
# --------------------------------------------------------------------------
st.set_page_config(layout="centered")
st.title("SmartLib AI: Настройка папок")

# Инициализируем "сейф" для хранения данных сессии
if 'auth_step' not in st.session_state:
    st.session_state.auth_step = "initial" # initial -> pending_folders -> done
if 'folders' not in st.session_state:
    st.session_state.folders = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

query_params = st.query_params
auth_code = query_params.get("code")
state = query_params.get("state")
chat_id = query_params.get("chat_id")
current_chat_id = state if state else chat_id

# --- РЕЖИМ 1: Пользователь только что пришел из Telegram ---
if st.session_state.auth_step == "initial":
    if not current_chat_id:
        st.error("Ошибка: Не найден ID пользователя. Пожалуйста, вернитесь в Telegram и перейдите по ссылке снова.")
    else:
        st.info("Для начала, пожалуйста, предоставьте доступ к вашему аккаунту Google.")
        final_auth_link = f"{MAGIC_AUTH_LINK}&state={current_chat_id}"
        st.link_button("Войти через Google и выбрать папки", final_auth_link, use_container_width=True)

# --- РЕЖИМ 2: Пользователь вернулся от Google с кодом ---
if auth_code and st.session_state.auth_step == "initial":
    try:
        with st.spinner('Получаем доступ и загружаем список ваших папок...'):
            payload = {"code": auth_code, "state": state}
            response = requests.post(GET_FOLDERS_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            st.session_state.folders = response_data.get("folders", [])
            st.session_state.auth_step = "pending_folders" # <<< ВАЖНО: МЕНЯЕМ СТАТУС
            st.experimental_rerun() # <<< ВАЖНО: ПЕРЕЗАГРУЖАЕМ СТРАНИЦУ, ЧТОБЫ "СЖЕЧЬ" AUTH_CODE

    except Exception as e:
        st.session_state.error_message = f"Произошла ошибка при получении данных от Google: {e}"
        st.session_state.auth_step = "error"
        st.experimental_rerun()

# --- РЕЖИМ 3: Папки получены, показываем выбор ---
if st.session_state.auth_step == "pending_folders":
    if not st.session_state.folders:
        st.warning("Не удалось найти папки на вашем Google Диске.")
    else:
        st.success("Доступ получен! Теперь выберите папки для анализа:")
        
        selected_folders = []
        for folder in st.session_state.folders:
            if folder.get('name') and folder.get('id'):
                if st.checkbox(folder.get('name'), key=folder.get('id')):
                    selected_folders.append({'id': folder.get('id'), 'name': folder.get('name')})
        
        if st.button("Сохранить выбор и завершить настройку", use_container_width=True):
            if not selected_folders:
                st.warning("Пожалуйста, выберите хотя бы одну папку.")
            else:
                with st.spinner('Сохраняем ваш выбор...'):
                    payload = { "chat_id": current_chat_id, "selected_folders": selected_folders }
                    try:
                        response = requests.post(SAVE_FOLDERS_WEBHOOK_URL, json=payload)
                        response.raise_for_status()
                        st.session_state.auth_step = "done"
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Произошла ошибка при сохранении вашего выбора: {e}")

# --- РЕЖИМ 4: Завершение или Ошибка ---
if st.session_state.auth_step == "done":
    st.success("Отлично! Ваш выбор сохранен. Документы из выбранных папок будут обработаны в ближайшее время. Можете закрывать это окно и возвращаться в Telegram.")
    st.balloons()

if st.session_state.auth_step == "error":
    st.error(st.session_state.error_message)
    st.write("Пожалуйста, попробуйте авторизоваться еще раз, вернувшись в Telegram.")
