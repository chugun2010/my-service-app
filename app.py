import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Скупка & Ремонт", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# Подключение к таблице
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Ошибка подключения. Проверьте Secrets.")
    st.stop()

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
                try:
                    # Читаем текущие данные, чтобы узнать последний ID
                    df_repair = conn.read(worksheet="Ремонт", ttl=0).dropna(how="all")
                    new_id = int(df_repair["ID"].max() + 1) if not df_repair.empty and "ID" in df_repair.columns else 1
                except:
                    new_id = 1
                
                # Создаем ОДНУ новую строчку строго по вашим колонкам
                new_row = pd.DataFrame([{
                    "ID": new_id,
                    "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Клиент": client,
                    "Телефон": phone,
                    "Устройство": device,
                    "Неисправность": issue,
                    "Статус": "В работе"
                }])
                
                try:
                    # БЕЗОПАСНАЯ ЗАПИСЬ: просто дописываем строчку в конец листа
                    conn.create(worksheet="Ремонт", data=new_row)
                    st.success(f"Заказ №{new_id} успешно сохранен в Google Таблицу!")
                    
                    st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                    st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client} ({phone})\n\n**Устройство:** {device}\n\n**Неисправность:** {issue}\n\n*Дата: {datetime.now().strftime('%d.%m.%Y')}*")
                except Exception as e:
                    st.error(f"Не удалось записать в таблицу. Проверьте, что лист называется 'Ремонт'. Ошибка: {e}")
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
                try:
                    df_skupka = conn.read(worksheet="Скупка", ttl=0).dropna(how="all")
                    new_id = int(df_skupka["ID"].max() + 1) if not df_skupka.empty and "ID" in df_skupka.columns else 1
                except:
                    new_id = 1
                
                new_row = pd.DataFrame([{
                    "ID": new_id,
                    "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Модель": model,
                    "Характеристики": specs,
                    "Цена_Закупки": price_buy,
                    "Продавец": seller,
                    "Статус": "На складе",
                    "Цена_Продажи": "",
                    "Дата_Продажи": ""
                }])
                
                try:
                    conn.create(worksheet="Скупка", data=new_row)
                    st.success(f"Устройство №{new_id} добавлено на склад скупки!")
                    st.markdown("### 🖨 АКТ НА ВЫКУП ТЕХНИКИ")
                    st.info(f"**АКТ СКУПКИ №{new_id}**\n\n**Устройство:** {model} ({specs})\n\n**Цена выкупа:** {price_buy} руб.\n\n**Продавец:** {seller}")
                except Exception as e:
                    st.error(f"Ошибка записи в скупку: {e}")
            else:
                st.error("Введите модель и цену закупки!")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со касается склада")
    try:
        df_skupka = conn.read(worksheet="Скупка", ttl=0).dropna(how="all")
    except:
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
                    idx = df_skupka[df_skupka["ID"] == selected_id].index
                    df_skupka.at[idx, "Статус"] = "Продано"
                    df_skupka.at[idx, "Цена_Продажи"] = price_sell
                    df_skupka.at[idx, "Дата_Продажи"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    try:
                        conn.update(worksheet="Скупка", data=df_skupka)
                        st.success("Продажа успешно зафиксирована!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка при обновлении статуса продажи: {e}")
                else:
                    st.error("Введите цену продажи!")
    else:
        st.info("Склад пуст.")
