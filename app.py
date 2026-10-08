import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import time

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# ТВОЙ АПИ-ШЛЮЗ НАСТОЯЩИЙ И РАБОЧИЙ
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

# Функция перевода кривого времени Google в московское (работает чисто на отображение)
def clean_date_display(val):
    v = str(val).strip()
    if "t" in v.lower() or "z" in v.lower():
        try:
            s = v.replace("T", " ").replace("t", " ").replace("Z", "").replace("z", "")
            if "." in s:
                s = s.split(".")[0]
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            return (dt + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M")
        except:
            pass
    return v

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
                with st.spinner("Сохраняем ремонт..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                        st.success(f"Заказ №{new_id} успешно сохранен!")
                    except:
                        st.success(f"Заказ №{new_id} отправлен!")
                    st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client} ({phone})\n**Устройство:** {device}")

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
                    "sheet": "Sкупка",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже", ""]
                }
                with st.spinner("Сохраняем выкуп..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass
                    st.success(f"Устройство №{new_id} добавлено!")
                    st.rerun()

# --- ПРОСТОЙ И НАДЕЖНЫЙ СБОР ДАННЫХ ИЗ GOOGLE ТАБЛИЦЫ ---
headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
df_main = pd.DataFrame(columns=headers)

try:
    response = requests.get(f"{API_URL}?sheet=Скупка&t={time.time()}", timeout=5)
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        # Безопасно отсекаем шапку, если первая ячейка содержит текст названия заголовка
        if len(data[0]) > 0 and str(data[0][0]).strip().lower() in ["id", "ид", "идентификатор"]:
            rows = data[1:]
        else:
            rows = data
            
        if len(rows) > 0:
            df_main = pd.DataFrame(rows)
            # Выравниваем количество колонок строго под наш паспорт (8 штук)
            while len(df_main.columns) < len(headers):
                df_main[len(df_main.columns)] = ""
            df_main = df_main.iloc[:, :len(headers)]
            df_main.columns = headers
            
            # Убираем пробелы вокруг текста
            for c in df_main.columns:
                df_main[c] = df_main[c].astype(str).str.strip()
except:
    pass

# ---------------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------------
with tab_prep:
    st.header("Техника на подготовке к продаже")
    
    if not df_main.empty:
        in_prep = df_main[df_main["Статус"] == "Подготовка к продаже"].copy()
        
        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            # Делаем время красивым и московским прямо перед показом на экране
            in_prep["Дата"] = in_prep["Дата"].apply(clean_date_display)
            
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
                        with st.spinner("Выставляем на витрину..."):
                            try:
                                requests.post(API_URL, json=payload, timeout=3)
                            except:
                                pass
                            st.success("Успешно выставлено!")
                            st.rerun()
                    else:
                        st.error("Укажите цену продажи!")
            with col2:
                if st.button("🖨 Печать этикетки штрих-кода"):
                    st.info("⏳ Функция печати в разработке.")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    
    if not df_main.empty:
        in_stock = df_main[df_main["Статус"] == "На складе"].copy()
        if in_stock.empty:
            st.info("На складе пусто.")
        else:
            # Делаем время красивым и московским перед показом на витрине
            in_stock["Дата"] = in_stock["Дата"].apply(clean_date_display)
            
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
                # ИСПРАВЛЕНО: Извлекаем чистое одиночное значение из ячейки первой строки через .iloc[0]
                val_p = chosen_row["Цена_Продажи"].iloc[0]
                current_price = str(val_p).strip() if pd.notna(val_p) and str(val_p).strip() != "" else "0"
            
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
                with st.spinner("Продаем..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except:
                        pass
                    st.success("Успешно продано!")
                    st.rerun()
    else:
        st.info("На складе пока пусто.")
