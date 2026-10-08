import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# ТВОЙ НАСТОЯЩИЙ РАБОЧИЙ АПИ ШЛЮЗ
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

# 4 чистые вкладки по нашему плану
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
                try:
                    response = requests.post(API_URL, json=payload)
                    if response.text == "Success":
                        st.success(f"Заказ №{new_id} успешно сохранен!")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

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
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже"]
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success(f"Устройство добавлено!")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    try:
        response = requests.get(f"{API_URL}?sheet=Скупка")
        data = response.json()
        df_prep = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 0 else pd.DataFrame()
    except:
        df_prep = pd.DataFrame()
    
    if not df_prep.empty and "Статус" in df_prep.columns:
        in_prep = df_prep[df_prep["Статус"].str.strip() == "Подготовка к продаже"]
        if in_prep.empty:
            st.info("На подготовке пусто.")
        else:
            st.dataframe(in_prep, use_container_width=True)
            
            options_prep = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_prep.iterrows()}
            selected_prep = st.selectbox("Выберите для оценки:", list(options_prep.keys()))
            price_sell_ready = st.number_input("Цена продажи", min_value=0, step=100, key="prep_p")
            
            if st.button("Выставить на витрину"):
                payload = {
                    "action": "update",
                    "sheet": "Скупка",
                    "id": int(options_prep[selected_prep]),
                    "status": "На складе",
                    "price_sell": price_sell_ready
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success("Выставлено!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    try:
        response = requests.get(f"{API_URL}?sheet=Скупка")
        data = response.json()
        df_skupka = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 0 else pd.DataFrame()
    except:
        df_skupka = pd.DataFrame()
    
    if not df_skupka.empty and "Статус" in df_skupka.columns:
        in_stock = df_skupka[df_skupka["Статус"].str.strip() == "На складе"]
        if in_stock.empty:
            st.info("На складе пусто.")
        else:
            st.dataframe(in_stock, use_container_width=True)
            
            options = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_stock.iterrows()}
            selected = st.selectbox("Выберите для продажи:", list(options.keys()))
            
            if st.button("Оформить продажу"):
                payload = {
                    "action": "update",
                    "sheet": "Скупка",
                    "id": int(options[selected]),
                    "status": "Продано",
                    "date_sell": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success("Продано!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")
