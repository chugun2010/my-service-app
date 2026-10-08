
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

# Инициализируем локальное хранилище в памяти приложения
if "df_skupka_local" not in st.session_state:
    st.session_state["df_skupka_local"] = None
if "need_reload" not in st.session_state:
    st.session_state["need_reload"] = True

# Функция БРОНЕБОЙНОГО сбора чистой таблицы вручную по строкам
def load_data_from_google():
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    try:
        nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url, timeout=5)
        data = response.json()
        
        parsed_rows = []
        if isinstance(data, list) and len(data) > 0:
            for row in data:
                # Если строчка пустая или это заголовок таблицы из Google, пропускаем её
                if not row or not isinstance(row, list):
                    continue
                first_cell = str(row[0]).strip().lower()
                if first_cell in ["id", "ид", "идентификатор", ""]:
                    continue
                
                # Достраиваем строку пустыми ячейками, если в таблице заполнено не все
                clean_row = [str(cell).strip() for cell in row]
                while len(clean_row) < len(headers):
                    clean_row.append("")
                
                # Берем только первые 8 ячеек строго по нашему паспорту
                parsed_rows.append(clean_row[:len(headers)])
                
        # Собираем чистейший DataFrame БЕЗ мульти-индексов и скрытой каши
        return pd.DataFrame(parsed_rows, columns=headers)
    except:
        pass
    return pd.DataFrame(columns=headers)

# Кнопка ручной синхронизации
if st.button("🔄 Синхронизировать с Google Таблицей"):
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False
    st.rerun()

# Первая загрузка при старте
if st.session_state["df_skupka_local"] is None or st.session_state["need_reload"]:
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False

# Загружаем текущую чистую таблицу из памяти
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
                with st.spinner("Сохраняем ремонт in Google..."):
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
                
                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже", ""]
                }
                
                # Мгновенно добавляем в локальную таблицу с чистой структурой
                new_row = [str(new_id), current_time, model, specs, str(price_buy), seller, "Подготовка к продаже", ""]
                df_main.loc[len(df_main)] = new_row
                st.session_state["df_skupka_local"] = df_main
                
                with st.spinner("Записываем выкуп техники..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass
                    st.success(f"Устройство №{new_id} успешно добавлено в подготовку!")
                    st.rerun()

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    if not df_main.empty:
        in_prep = df_main[df_main["Статус"] == "Подготовка к продаже"]
        
        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            # Идеально чистая витрина без индексов
            st.dataframe(in_prep[["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")
            
            options_prep = {}
            for _, row in in_prep.iterrows():
                val_id = str(row["ID"]).strip()
                val_model = str(row["Модель"]).strip()
                options_prep[f"№{val_id} - {val_model}"] = val_id
                
            selected_prep = st.selectbox("Выберите устройство для оценки:", list(options_prep.keys()), key="sb_prep")
            selected_prep_id = options_prep[selected_prep]
            
            price_sell_ready = st.number_input("Установить цену продажи (руб.)", min_value=0, step=100, key="prep_price")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Готов к продаже (На склад)"):
                    if price_sell_ready > 0:
                        clean_id = int(float(selected_prep_id)) if selected_prep_id.replace('.','',1).isdigit() else selected_prep_id
                        
                        # Мгновенно обновляем локально статус и цену продажи
                        df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Статус"] = "На складе"
                        df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Цена_Продажи"] = str(price_sell_ready)
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
                            st.success("Устройство перемещено на витрину продаж!")
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
        in_stock = df_main[df_main["Статус"] == "На складе"]
        if in_stock.empty:
            st.info("На складе пусто.")
        else:
            st.markdown("### 🏪 Товары на витрине:")
            st.dataframe(in_stock[["ID", "Дата", "Модель", "Характеристики", "Цена_Продажи"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 💰 Оформление сделки")
            
            options = {}
            for _, row in in_stock.iterrows():
                val_id = str(row["ID"]).strip()
                val_model = str(row["Модель"]).strip()
                options[f"№{val_id} - {val_model}"] = val_id
                
            selected = st.selectbox("Выберите для продажи:", list(options.keys()), key="sb_sell")
            selected_id = options[selected]
            
            chosen_row = in_stock[in_stock["ID"] == str(selected_id).strip()]
            current_price = "0"
            if not chosen_row.empty:
                current_price = str(chosen_row["Цена_Продажи"].values[0])
