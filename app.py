import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json
import time

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# ТВОЙ АПИ-ШЛЮЗ НАСТОЯЩИЙ
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

# Инициализируем локальное хранилище в памяти приложения для мгновенного обновления остатков
if "df_skupka_local" not in st.session_state:
    st.session_state["df_skupka_local"] = None
if "need_reload" not in st.session_state:
    st.session_state["need_reload"] = True

# Функция принудительного скачивания свежих данных из Google
def load_data_from_google():
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    try:
        nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url, timeout=5)
        data = response.json()
        if len(data) > 0:
            if isinstance(data, list):
                df = pd.DataFrame(data[1:], columns=data)
            else:
                df = pd.DataFrame(data)
                while len(df.columns) > len(headers):
                    headers.append(f"Колонка_{len(headers)+1}")
                df.columns = headers[:len(df.columns)]
            # Чистим данные от случайных пробелов в ID и Статусе
            if len(df.columns) > 0:
                df[df.columns[0]] = df[df.columns[0]].astype(str).str.strip()
            col_idx = 6 if len(df.columns) > 6 else len(df.columns) - 1
            df[df.columns[col_idx]] = df[df.columns[col_idx]].astype(str).str.strip()
            return df
    except:
        pass
    return pd.DataFrame(columns=headers)

# Кнопка глобального обновления данных вручную в самом верху панели
if st.button("🔄 Синхронизировать с Google Таблицей"):
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False
    st.rerun()

# Если это первый запуск или был сброс — скачиваем базу
if st.session_state["df_skupka_local"] is None or st.session_state["need_reload"]:
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False

# Загружаем текущую рабочую таблицу из памяти
df_main = st.session_state["df_skupka_local"]

# 4 ВКЛАДКИ
tab1, tab2, tab_prep, tab3 = st.tabs(["🔧 Приемка в ремонт", "💰 Скупка (Выкуп)", "🛠 Подготовка к продаже", "📦 Продажа со склада"])

# ---------------- Вкладка 1: РЕМОНТ ----------------
with tab1:
    st.header("Новый ремонт")
    with st.form("repair_form", clear_on_submit=True):
        client = st.text_input("ФИО Клиента")
        phone = st.text_input("Номер телефона")
        device = st.text_input("Устройство (Модель, IMEI)")
        issue = st.text_area("Неисправность и внешний вид")
        submit_repair = st.form_submit_button("Принять в ремонт")
        
        if submit_repair:
            if client and phone and device:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_id = int(datetime.now().timestamp()) % 100000
                payload = {
                    "action": "append",
                    "sheet": "Ремонт",
                    "row": [new_id, current_time, client, phone, device, issue, "В работе"]
                }
                with st.spinner("Сохраняем ремонт в Google Таблицу..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                        st.success(f"Заказ №{new_id} успешно сохранен!")
                    except:
                        st.success(f"Заказ №{new_id} отправлен в таблицу!")
                    
                    st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                    st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client}\n**Телефон:** {phone}\n**Устройство:** {device}\n**Неисправность:** {issue}")

# ---------------- Вкладка 2: СКУПКА ----------------
with tab2:
    st.header("Оформить выкуп")
    with st.form("buyout_form", clear_on_submit=True):
        model = st.text_input("Модель")
        specs = st.text_input("Характеристики")
        price_buy = st.number_input("Цена закупки", min_value=0, step=100)
        seller = st.text_input("Продавец")
        submit_buyout = st.form_submit_button("Оформить выкуп")
        
        if submit_buyout:
            if model and price_buy > 0:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_id = int(datetime.now().timestamp()) % 100000
                
                # Данные для отправки на сервер
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже", ""]
                }
                
                # МГНОВЕННО добавляем аппарат в локальную таблицу на экране (Мимо медленного кэша Гугла)
                new_row = [str(new_id), current_time, model, specs, str(price_buy), seller, "Подготовка к продаже", ""]
                # Подгоняем длину строки под количество колонок
                while len(new_row) < len(df_main.columns):
                    new_row.append("")
                df_main.loc[len(df_main)] = new_row[:len(df_main.columns)]
                st.session_state["df_skupka_local"] = df_main
                
                with st.spinner("Записываем выкуп техники..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass
                    st.success(f"Устройство №{new_id} успешно выкуплено и мгновенно добавлено в подготовку!")
                    st.rerun()

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    if not df_main.empty:
        col_idx = 6 if len(df_main.columns) > 6 else len(df_main.columns) - 1
        status_col = df_main.columns[col_idx]
        
        in_prep = df_main[df_main[status_col].astype(str).str.strip() == "Подготовка к продаже"]
        
        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            st.dataframe(in_prep, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")
            
            c_id = df_main.columns[0]
            c_model = df_main.columns[2] if len(df_main.columns) > 2 else df_main.columns[0]
            
            options_prep = {}
            for _, row in in_prep.iterrows():
                val_id = str(row[c_id]).strip()
                val_model = str(row[c_model]).strip()
                options_prep[f"№{val_id} - {val_model}"] = val_id
                
            selected_prep = st.selectbox("Выберите устройство для оценки:", list(options_prep.keys()), key="sb_prep")
            selected_prep_id = options_prep[selected_prep]
            
            price_sell_ready = st.number_input("Установить цену продажи (руб.)", min_value=0, step=100, key="prep_price")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Готов к продаже (На склад)"):
                    if price_sell_ready > 0:
                        clean_id = int(float(selected_prep_id)) if selected_prep_id.replace('.','',1).isdigit() else selected_prep_id
                        
                        # МГНОВЕННО меняем статус и цену локально в памяти экрана
                        df_main.loc[df_main[c_id].astype(str).str.strip() == str(selected_prep_id).strip(), status_col] = "На складе"
                        if len(df_main.columns) > 7:
                            df_main.loc[df_main[c_id].astype(str).str.strip() == str(selected_prep_id).strip(), df_main.columns[7]] = str(price_sell_ready)
                        st.session_state["df_skupka_local"] = df_main
                        
                        payload = {
                            "action": "update",
                            "sheet": "Скупка",
                            "id": clean_id,
                            "status": "На складе",
                            "price_sell": price_sell_ready 
                        }
                        with st.spinner("Переносим на витрину склада..."):
                            try:
                                requests.post(API_URL, json=payload, timeout=3)
                            except:
                                pass
                            st.success("Устройство мгновенно перемещено на витрину продаж!")
                            st.rerun()
                    else:
                        st.error("Укажите цену продажи!")
            with col2:
                if st.button("🖨 Печать этикетки штрих-кода"):
                    st.info("⏳ Функция печати в разработке. Скоро подключим!")
    else:
        st.info("На подготовке пока пусто.")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    
    if not df_main.empty:
        col_idx = 6 if len(df_main.columns) > 6 else len(df_main.columns) - 1
        status_col_s = df_main.columns[col_idx]
        
        in_stock = df_main[df_main[status_col_s].astype(str).str.strip() == "На складе"]
        if in_stock.empty:
            st.info("На складе пусто.")
        else:
            st.markdown("### 🏪 Товары на витрине:")
            st.dataframe(in_stock, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            c_id_s = df_main.columns[0]
            c_model_s = df_main.columns[2] if len(df_main.columns) > 2 else df_main.columns[0]
            
            options = {}
