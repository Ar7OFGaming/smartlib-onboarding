import streamlit as st
import requests
import json
import urllib.parse

# --------------------------------------------------------------------------
# ШАГ 1: ВАШИ ПЕРСОНАЛЬНЫЕ НАСТРОЙКИ
# --------------------------------------------------------------------------
STREAMLIT_URL = "https://smartlib-app-fcz2i2s8uzbn2ffp5wsbhm.streamlit.app"
CLIENT_ID = "340752343067-79ipapn7o97qd8ibqvgpjg4687fm7jo7.apps.googleusercontent.com"
GET_FOLDERS_WEBHOOK_URL = "https://goooglovskiq.app.n8n.cloud/webhook/4aa31f22-b98e-4c4c-8c0f-93077cf63726"
SAVE_FOLDERS_WEBHOOK_URL = "https://goooglovskiq.app.n8n.cloud/webhook/438e832a-14fc-406a-87b4-d1711ab9c326"
SCOPES = "https://www.googleapis.com/auth/userinfo.email"
# SCOPES = "https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"

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

if 'auth_step' not in st.session_state:
    st.session_state.auth_step = "initial"
if 'folders' not in st.session_state:
    st.session_state.folders = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

query_params = st.query_params
auth_code = query_params.get("code")
state = query_params.get("state")
chat_id_from_tg = query_params.get("chat_id")
current_chat_id = state if state else chat_id_from_tg

# РЕЖИМ 1
if st.session_state.auth_step == "initial":
    if not current_chat_id:
        st.error("Ошибка: Не найден ID пользователя. Пожалуйста, вернитесь в Telegram и перейдите по ссылке снова.")
    else:
        st.info("Для начала, пожалуйста, предоставьте доступ к вашему аккаунту Google.")
        final_auth_link = f"{MAGIC_AUTH_LINK}&state={current_chat_id}"
        st.link_button("Войти через Google и выбрать папки", final_auth_link, use_container_width=True)

# РЕЖИМ 2
if auth_code and st.session_state.auth_step == "initial":
    try:
        with st.spinner('Получаем доступ и загружаем список ваших папок...'):
            payload = {"code": auth_code, "state": state}
            response = requests.post(GET_FOLDERS_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            response_data = response.json()
            st.session_state.folders = response_data.get("folders", [])
            st.session_state.auth_step = "pending_folders"
            st.rerun() # <<< ИСПРАВЛЕНО ЗДЕСЬ

    except Exception as e:
        st.session_state.error_message = f"Произошла ошибка при получении данных от Google: {e}"
        st.session_state.auth_step = "error"
        st.rerun() # <<< И ИСПРАВЛЕНО ЗДЕСЬ

# РЕЖИМ 3
if st.session_state.auth_step == "pending_folders":
    if st.session_state.folders is None: # Добавил проверку на None
        st.warning("Не удалось загрузить папки. Попробуйте обновить страницу.")
    elif not st.session_state.folders:
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
                        st.rerun() # <<< И ИСПРАВЛЕНО ЗДЕСЬ
                    except Exception as e:
                        st.error(f"Произошла ошибка при сохранении вашего выбора: {e}")

# РЕЖИМ 4
if st.session_state.auth_step == "done":
    st.success("Отлично! Ваш выбор сохранен. Документы из выбранных папок будут обработаны в ближайшее время. Можете закрывать это окно и возвращаться в Telegram.")
    st.balloons()

if st.session_state.auth_step == "error":
    st.error(st.session_state.error_message)
    st.write("Пожалуйста, попробуйте авторизоваться еще раз, вернувшись в Telegram.")




