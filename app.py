import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import json

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# ТВОЙ АПИ ШЛЮЗ ВШИТ НАВСЕГДА
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

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
                try:
                    response = requests.post(API_URL, json=payload)
                    if response.text == "Success":
                        st.success(f"Заказ №{new_id} успешно сохранен!")
                        st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                        st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client}\n**Телефон:** {phone}\n**Устройство:** {device}\n**Неисправность:** {issue}")
                except Exception as e:
                    st.error(f"Ошибка отправки: {e}")

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
                
                # При выкупе статус жестко пишется как "Подготовка к продаже"
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
                    st.error(f"Ошибка отправки: {e}")

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
            st.dataframe(in_prep, use_container_width=True)
            
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
                                st.success("Устройство успешно выставлено на продажу!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка связи: {e}")
                    else:
                        st.error("Укажите цену продажи!")
            with col2:
                if st.button("🖨 Печать этикетки штрих-кода"):
                    st.info("⏳ Функция печати в разработке. Скоро подключим!")
    else:
        st.info("На подготовке пока пусто или шлюз не вернул данные таблицы.")

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
            st.info("На складе пусто.")
        else:
            st.markdown("### 🏪 Товары на витрине:")
            st.dataframe(in_stock, use_container_width=True)
            
            st.markdown("---")
            options = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_stock.iterrows()}
            selected = st.selectbox("Выберите для продажи:", list(options.keys()))
            selected_id = options[selected]
            
            chosen_row = in_stock[in_stock["ID"] == selected_id]
            current_price = 0
            if not chosen_row.empty:
                if "Цена_Продажи" in chosen_row.columns:
                    current_price = chosen_row["Цена_Продажи"].values[0]
                elif "price_sell" in chosen_row.columns:
                    current_price = chosen_row["price_sell"].values[0]
            
            st.markdown(f"**Стоимость к оплате:** `{current_price} руб.`")
            
            if st.button("Оформить продажу", type="primary"):
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                payload = {
                    "action": "update",
                    "sheet": "Скупка",
                    "id": int(selected_id) if str(selected_id).isdigit() else selected_id,
                    "status": "Продано",
                    "date_sell": current_time
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success("Продано!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    else:
        st.info("На складе пока пусто или шлюз не вернул данные таблицы.")
