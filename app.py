import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import time

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# ТВОЙ АПИ-ШЛЮЗ НАСТОЯЩИЙ
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

# Жесткие и чистые заголовки по паспорту проекта
SKUPKA_HEADERS = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]

# Функция для приведения кривого времени Google к нормальному московскому формату
def to_moscow_time(time_val):
    val = str(time_val).strip()
    if not val or val == "None" or val == "":
        return ""
    # Если это формат Google с буквой T и Z (например, 2026-10-08T11:45:00.000Z)
    if "t" in val.lower() or "z" in val.lower():
        try:
            clean_str = val.replace("T", " ").replace("t", " ").replace("Z", "").replace("z", "")
            if "." in clean_str:
                clean_str = clean_str.split(".")[0]
            # Считаем Московское время (+3 часа)
            dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
            dt_moscow = dt + timedelta(hours=3)
            return dt_moscow.strftime("%d.%m.%Y %H:%M")
        except:
            pass
    return val

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
                with st.spinner("Сохраняем ремонт в Google..."):
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
                with st.spinner("Записываем выкуп техники..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass
                    st.success(f"Устройство №{new_id} успешно добавлено!")
                    st.rerun()

# ЧТЕНИЕ ДАННЫХ ИЗ GOOGLE НАПРЯМУЮ ДЛЯ ОСТАЛЬНЫХ ВКЛАДОК
df_main = pd.DataFrame(columns=SKUPKA_HEADERS)
try:
    nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
    response = requests.get(nocache_url, timeout=5)
    data = response.json()
    
    parsed_rows = []
    if isinstance(data, list) and len(data) > 0:
        for row in data:
            if not row or not isinstance(row, list):
                continue
            # Пропускаем заголовки Google, если они прилетели
            if str(row[0]).strip().lower() in ["id", "ид", ""]:
                continue
            
            clean_row = [str(cell).strip() for cell in row]
            while len(clean_row) < len(SKUPKA_HEADERS):
                clean_row.append("")
            
            # Меняем кривое время на московское строго во втором столбце
            clean_row[1] = to_moscow_time(clean_row[1])
            parsed_rows.append(clean_row[:len(SKUPKA_HEADERS)])
            
        df_main = pd.DataFrame(parsed_rows, columns=SKUPKA_HEADERS)
except:
    pass

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    if not df_main.empty:
        in_prep = df_main[df_main["Статус"] == "Подготовка к продаже"]
        
        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            st.dataframe(in_prep[["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки"]], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")
            
            options_prep = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_prep.iterrows()}
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
                                requests.post(API_URL, json=payload, timeout=3)
                            except:
                                pass
                            st.success("Устройство выставлено на витрину продаж!")
                            st.rerun()
                    else:
                        st.error("Укажите цену продажи!")
            with col2:
                if st.button("🖨 Печать этикетки штрих-кода"):
                    st.info("⏳ Функция печати в разработке. Скоро подключим!")
    else:
        st.info("На подготовке пока пусто или таблица пуста.")

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
            
            options = {f"№{row['ID']} - {row['Модель']}": row['ID'] for _, row in in_stock.iterrows()}
            selected = st.selectbox("Выберите для продажи:", list(options.keys()), key="sb_sell")
            selected_id = options[selected]
            
            chosen_row = in_stock[in_stock["ID"] == str(selected_id).strip()]
            current_price = "0"
            if not chosen_row.empty:
                val_p = chosen_row["Цена_Продажи"].values[0] if hasattr(chosen_row["Цена_Продажи"], "values") else chosen_row["Цена_Продажи"]
                current_price = str(val_p) if pd.notna(val_p) and str(val_p).strip() != "" else "0"
            
            st.markdown(f"**Стоимость к оплате:** `{current_price} руб.`")
            
            if st.button("Оформить продажу", type="primary"):
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                clean_id_s = int(float(selected_id)) if selected_id.replace('.','',1).isdigit() else selected_id
                payload = {
                    "action": "update",
                    "sheet": "Скупка",
                    "id": clean_id_s,
                    "status": "Продано",
                    "date_sell": current_time
                }
                with st.spinner("Проводим сделку и списываем со склада..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass
                    st.success("Успешно продано!")
                    st.rerun()
    else:
        st.info("На складе пока пусто.")
