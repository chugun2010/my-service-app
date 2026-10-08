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
                
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже"]
                }
                try:
                    res = requests.post(API_URL, json=payload)
                    if res.text == "Success":
                        st.success(f"Устройство №{new_id} добавлено и отправлено на подготовку!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка отправки: {e}")

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    df_prep = pd.DataFrame()
    
    try:
        # УБИВАЕМ КЭШ: добавляем уникальный номер секунды t= к ссылке
        nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url)
        data = response.json()
        
        if len(data) > 0:
            if isinstance(data, list):
                df_prep = pd.DataFrame(data[1:], columns=data)
            else:
                df_prep = pd.DataFrame(data, columns=headers[:len(data) if data else 7])
    except:
        df_prep = pd.DataFrame()
        
    if not df_prep.empty:
        col_idx = 6 if len(df_prep.columns) > 6 else len(df_prep.columns) - 1
        status_col = df_prep.columns[col_idx]
        
        in_prep = df_prep[df_prep[status_col].astype(str).str.strip() == "Подготовка к продаже"]
        
        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            st.dataframe(in_prep, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")
            
            id_col = df_prep.columns
            model_col = df_prep.columns if len(df_prep.columns) > 2 else df_prep.columns
            
            options_prep = {f"№{row[id_col]} - {row[model_col]}": row[id_col] for _, row in in_prep.iterrows()}
            selected_prep = st.selectbox("Выберите устройство для оценки:", list(options_prep.keys()), key="sb_prep")
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
                                time.sleep(1) # Небольшая пауза, чтобы Гугл успел сохранить изменения
                                st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка связи: {e}")
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
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    df_skupka = pd.DataFrame()
    
    try:
        # УБИВАЕМ КЭШ И ТУТ
        nocache_url_s = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url_s)
        data = response.json()
        if len(data) > 0:
            if isinstance(data, list):
                df_skupka = pd.DataFrame(data[1:], columns=data)
            else:
                df_skupka = pd.DataFrame(data, columns=headers[:len(data) if data else 7])
    except:
        df_skupka = pd.DataFrame()
        
    if not df_skupka.empty:
        col_idx = 6 if len(df_skupka.columns) > 6 else len(df_skupka.columns) - 1
        status_col_s = df_skupka.columns[col_idx]
        
        in_stock = df_skupka[df_skupka[status_col_s].astype(str).str.strip() == "На складе"]
        if in_stock.empty:
            st.info("На складе пусто.")
        else:
            st.markdown("### 🏪 Товары на витрине:")
            st.dataframe(in_stock, use_container_width=True)
            
            st.markdown("---")
            id_col_s = df_skupka.columns
            model_col_s = df_skupka.columns if len(df_skupka.columns) > 2 else df_skupka.columns
            
            options = {f"№{row[id_col_s]} - {row[model_col_s]}": row[id_col_s] for _, row in in_stock.iterrows()}
            selected = st.selectbox("Выберите для продажи:", list(options.keys()), key="sb_sell")
            selected_id = options[selected]
            
            chosen_row = in_stock[in_stock[id_col_s] == selected_id]
            current_price = 0
            if not chosen_row.empty:
                for col in chosen_row.columns:
                    if str(col).strip().lower() in ["цена_продажи", "цена продажи", "price_sell"]:
                        # Извлекаем чистое значение цены
                        current_price = chosen_row[col].values[0] if hasattr(chosen_row[col], 'values') else chosen_row[col]
                        break
            
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
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    else:
        st.info("На складе пока пусто.")
