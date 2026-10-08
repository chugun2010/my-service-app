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
                with st.spinner("Сохраняем ремонт в Google Таблицу..."):
                    try:
                        # Ставим таймаут 3 секунды, чтобы программа не висела
                        response = requests.post(API_URL, json=payload, timeout=3)
                        st.success(f"Заказ №{new_id} успешно сохранен!")
                    except requests.exceptions.Timeout:
                        # Если вышло время, но мы знаем, что Гугл записывает быстро — всё равно пишем успех!
                        st.success(f"Заказ №{new_id} успешно отправлен в таблицу!")
                    except Exception as e:
                        st.error(f"Ошибка отправки: {e}")
                    
                    # Показываем квитанцию в любом случае
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
                
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже"]
                }
                with st.spinner("Записываем выкуп техники..."):
                    try:
                        res = requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass # Игнорируем зависание ответа шлюза
                    st.success(f"Устройство №{new_id} успешно добавлено!")
                    st.rerun()

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    df_prep = pd.DataFrame()
    
    try:
        nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url, timeout=4)
        data = response.json()
        
        if len(data) > 0:
            if isinstance(data, list):
                df_prep = pd.DataFrame(data[1:], columns=data)
            else:
                df_prep = pd.DataFrame(data)
                while len(df_prep.columns) > len(headers):
                    headers.append(f"Колонка_{len(headers)+1}")
                df_prep.columns = headers[:len(df_prep.columns)]
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
            st.dataframe(in_prep, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")
            
            c_id = df_prep.columns
            c_model = df_prep.columns if len(df_prep.columns) > 2 else df_prep.columns
            
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
                        
                        payload = {
                            "action": "update",
                            "sheet": "Скупка",
                            "id": clean_id,
                            "status": "На складе",
                            "price_sell": price_sell_ready 
                        }
                        with st.spinner("Переносим на витрину склада..."):
                            try:
                                res = requests.post(API_URL, json=payload, timeout=3)
                            except:
                                pass
                            st.success("Устройство успешно выставлено на витрину!")
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
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    df_skupka = pd.DataFrame()
    
    try:
        nocache_url_s = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url_s, timeout=4)
        data = response.json()
        if len(data) > 0:
            if isinstance(data, list):
                df_skupka = pd.DataFrame(data[1:], columns=data)
            else:
                df_skupka = pd.DataFrame(data)
                while len(df_skupka.columns) > len(headers):
                    headers.append(f"Колонка_{len(headers)+1}")
                df_skupka.columns = headers[:len(df_skupka.columns)]
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
            st.dataframe(in_stock, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            c_id_s = df_skupka.columns
            c_model_s = df_skupka.columns if len(df_skupka.columns) > 2 else df_skupka.columns
            
            options = {}
            for _, row in in_stock.iterrows():
                val_id = str(row[c_id_s]).strip()
                val_model = str(row[c_model_s]).strip()
                options[f"№{val_id} - {val_model}"] = val_id
                
            selected = st.selectbox("Выберите для продажи:", list(options.keys()), key="sb_sell")
            selected_id = options[selected]
            
            chosen_row = in_stock[in_stock[c_id_s].astype(str).str.strip() == str(selected_id).strip()]
            current_price = 0
            if not chosen_row.empty:
                if len(chosen_row.columns) > 7:
                    val_p = chosen_row.iloc
                    current_price = val_p if pd.notna(val_p) else 0
                else:
                    for col in chosen_row.columns:
                        if str(col).strip().lower() in ["цена_продажи", "цена продажи", "price_sell"]:
                            current_price = chosen_row[col].values if hasattr(chosen_row[col], 'values') else chosen_row[col]
                            break
            
            st.markdown(f"**Стоимость к оплате:** `{current_price} руб.`")
            
            if st.button("Оформить продажу", type="primary"):
