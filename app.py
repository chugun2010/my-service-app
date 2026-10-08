import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

st.set_page_config(page_title="Скупка & Ремонт", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# Ваша личная ссылка-шлюз из Apps Script
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

tab1, tab2, tab3 = st.tabs(["🔧 Приемка в ремонт", "💰 Скупка (Выкуп)", "📦 Продажа со склада"])

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
                
                # Данные для добавления в таблицу
                payload = {
                    "action": "append",
                    "sheet": "Ремонт",
                    "row": [new_id, current_time, client, phone, device, issue, "В работе"]
                }
                
                try:
                    response = requests.post(API_URL, json=payload)
                    if response.text == "Success":
                        st.success(f"Заказ №{new_id} успешно сохранен в Google Таблицу!")
                        st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                        st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client} ({phone})\n\n**Устройство:** {device}\n\n**Неисправность:** {issue}\n\n*Дата: {current_time}*")
                    else:
                        st.error("Ошибка шлюза Google. Проверьте имена листов в таблице.")
                except Exception as e:
                    st.error(f"Не удалось отправить данные: {e}")
            else:
                st.error("Заполните поля: Клиент, Телефон, Устройство!")

# ---------------- Вкладка 2: СКУПКА ----------------
with tab2:
    st.header("Оформить выкуп устройства")
    with st.form("buyout_form", clear_on_submit=True):
        model = st.text_input("Модель телефона")
        specs = st.text_input("Характеристики (Память, цвет, состояние)")
        price_buy = st.number_input("Цена закупки (руб.)", min_value=0, step=100)
        seller = st.text_input("Данные продавца (ФИО, Паспорт)")
        submit_buyout = st.form_submit_button("Оформить выкуп")
        
        if submit_buyout:
            if model and price_buy > 0:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_id = int(datetime.now().timestamp()) % 100000
                
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "На складе", "", ""]
                }
                
                try:
                    response = requests.post(API_URL, json=payload)
                    if response.text == "Success":
                        st.success(f"Устройство №{new_id} добавлено на склад скупки!")
                        st.markdown("### 🖨 АКТ НА ВЫКУП ТЕХНИКИ")
                        st.info(f"**АКТ СКУПКИ №{new_id}**\n\n**Устройство:** {model} ({specs})\n\n**Цена выкупа:** {price_buy} руб.")
                    else:
                        st.error("Ошибка шлюза Google.")
                except Exception as e:
                    st.error(f"Ошибка отправки: {e}")
            else:
                st.error("Введите модель и цену закупки!")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    
    # Чтение остатков напрямую через ваш шлюз
    try:
        get_url = f"{API_URL}?sheet=Скупка"
        response = requests.get(get_url)
        data = response.json()
        
        if len(data) > 0:
            headers = data[0]
            rows = data[1:]
            df_skupka = pd.DataFrame(rows, columns=headers)
        else:
            df_skupka = pd.DataFrame()
    except Exception as e:
        df_skupka = pd.DataFrame()
    
    if not df_skupka.empty and "Статус" in df_skupka.columns:
        in_stock = df_skupka[df_skupka["Статус"] == "На складе"]
        if in_stock.empty:
            st.info("На складе нет доступных телефонов для продажи.")
        else:
            options = {f"№{row['ID']} - {row['Модель']} ({row['Характеристики']})": row['ID'] for _, row in in_stock.iterrows()}
            selected_option = st.selectbox("Выберите устройство для продажи:", list(options.keys()))
            selected_id = options[selected_option]
            price_sell = st.number_input("Цена продажи (руб.)", min_value=0, step=100)
            
            if st.button("Оформить продажу"):
                if price_sell > 0:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    payload = {
                        "action": "update",
                        "sheet": "Скупка",
                        "id": int(selected_id),
                        "status": "Продано",
                        "price_sell": price_sell,
                        "date_sell": current_time
                    }
                    
                    try:
                        res = requests.post(API_URL, json=payload)
                        if res.text == "Success":
                            st.success("Продажа успешно зафиксирована в Google Таблице!")
                            st.rerun()
                        else:
                            st.error("Ошибка обновления статуса.")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
                else:
                    st.error("Введите цену продажи!")
    else:
        st.info("На складе пока нет активных остатков.")
