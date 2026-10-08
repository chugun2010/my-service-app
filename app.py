import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# Ваша ссылка на шлюз Google Apps Script
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

# СОЗДАЕМ 4 ВКЛАДКИ (Добавили Подготовку к продаже)
tab1, tab2, tab_prep, tab3 = st.tabs([
    "🔧 Приемка в ремонт", 
    "💰 Скупка (Выкуп)", 
    "🛠 Подготовка к продаже", 
    "📦 Продажа со склада"
])

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
                        st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                        st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client}\n**Телефон:** {phone}\n**Устройство:** {device}\n**Неисправность:** {issue}")
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
                
                # ТЕПЕРЬ ТЕХНИКА ПОДАТАЕТ В СТАТУС "Подготовка к продаже"
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже"]
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success(f"Устройство №{new_id} добавлено и отправлено на подготовку!")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    try:
        response = requests.get(f"{API_URL}?sheet=Скупка")
        data = response.json()
        df_prep = pd.DataFrame(data[1:], columns=data) if len(data) > 0 else pd.DataFrame()
    except:
        df_prep = pd.DataFrame()
    
    if not df_prep.empty and "Статус" in df_prep.columns:
        in_prep = df_prep[df_prep["Статус"].str.strip() == "Подготовка к продаже"]
        
        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            show_cols = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Статус"]
            available_prep_cols = [col for col in show_cols if col in df_prep.columns]
            st.dataframe(in_prep[available_prep_cols], use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")
            
            options_prep = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_prep.iterrows()}
            selected_prep = st.selectbox("Выберите устройство для оценки:", list(options_prep.keys()))
            selected_prep_id = options_prep[selected_prep]
            
            price_sell_ready = st.number_input("Установить цену продажи (руб.)", min_value=0, step=100, key="prep_price")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Готов к продаже (На склад)"):
                    if price_sell_ready > 0:
                        payload = {
                            "action": "update",
                            "sheet": "Скупка",
                            "id": int(selected_prep_id) if str(selected_prep_id).isdigit() else selected_prep_id,
                            "status": "На складе",
                            "price_sell": price_sell_ready 
                        }
                        try:
                            res = requests.post(API_URL, json=payload)
                            if res.text == "Success":
                                st.success(f"Устройство №{selected_prep_id} выставлено на продажу за {price_sell_ready} руб.!")
                                st.rerun()
                            else:
                                st.error("Ошибка обновления статуса.")
                        except Exception as e:
                            st.error(f"Ошибка связи: {e}")
                    else:
                        st.error("Укажите цену продажи!")
            
            with col2:
                if st.button("🖨 Печать этикетки штрих-кода"):
                    st.info(f"⏳ Функция печати для устройства №{selected_prep_id} в разработке. Скоро подключим!")
    else:
        st.info("Таблица скупки пуста или еще не создана.")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    
    try:
        response = requests.get(f"{API_URL}?sheet=Скупка")
        data = response.json()
        df_skupka = pd.DataFrame(data[1:], columns=data) if len(data) > 0 else pd.DataFrame()
    except:
        df_skupka = pd.DataFrame()
    
    if not df_skupka.empty and "Статус" in df_skupka.columns:
        in_stock = df_skupka[df_skupka["Статус"].str.strip() == "На складе"]
        
        if in_stock.empty:
            st.info("На складе сейчас пусто. Нет доступных товаров.")
        else:
            st.markdown("### 🏪 Витрина магазина (Товары в наличии):")
            
            # Показываем красивую таблицу остатков. 
            # Название колонки цены проверяется автоматически (подойдет и Цена_Продажи, и price_sell)
            show_stock_cols = ["ID", "Модель", "Характеристики", "Цена_Продажи", "price_sell"]
            available_stock_cols = [col for col in show_stock_cols if col in in_stock.columns]
            st.dataframe(in_stock[available_stock_cols], use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 💰 Оформление сделки")
            
            options_sell = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_stock.iterrows()}
            selected_sell = st.selectbox("Выберите продаваемый аппарат из списка:", list(options_sell.keys()))
            selected_sell_id = options_sell[selected_sell]
            
            # Автоматически находим цену выбранного телефона
            chosen_row = in_stock[in_stock["ID"] == selected_sell_id]
            current_price = 0
            if not chosen_row.empty:
                for col in ["Цена_Продажи", "price_sell"]:
                    if col in chosen_row.columns:
                        current_price = chosen_row[col].values[0]
                        break
            
            st.markdown(f"**Стоимость к оплате:** `{current_price} руб.`")
            
            if st.button("Оформить продажу", type="primary"):
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                payload = {
                    "action": "update",
                    "sheet": "Скупка",
                    "id": int(selected_sell_id) if str(selected_sell_id).isdigit() else selected_sell_id,
                    "status": "Продано",
                    "date_sell": current_time
                }
                
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success(f"🎉 Продано! Товар №{selected_sell_id} списан со склада.")
                        st.rerun()
                    else:
                        st.error("Ошибка шлюза при обновлении статуса.")
                except Exception as e:
                    st.error(f"Не удалось отправить данные: {e}")
                    
    else:
        st.info("На складе пока нет активных остатков.")
