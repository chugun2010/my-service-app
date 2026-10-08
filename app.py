import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="Скупка & Ремонт", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# Подключение к Google Таблице
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Ошибка подключения к Google Таблице. Проверьте Secrets в настройках Streamlit.")
    st.stop()

# Чтение данных с очисткой кэша
def load_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0).dropna(how="all")
    except Exception:
        return pd.DataFrame()

# Функция для сохранения данных
def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)

# Создаем вкладки в интерфейсе
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
                df_repair = load_data("Ремонт")
                new_id = len(df_repair) + 1 if not df_repair.empty else 1
                new_row = pd.DataFrame([{
                    "ID": int(new_id),
                    "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Клиент": client,
                    "Телефон": phone,
                    "Устройство": device,
                    "Неисправность": issue,
                    "Статус": "В работе"
                }])
                df_combined = pd.concat([df_repair, new_row], ignore_index=True)
                save_data(df_combined, "Ремонт")
                st.success(f"Заказ №{new_id} успешно сохранен!")
                
                # Шаблон для печати
                st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client} ({phone})\n\n**Устройство:** {device}\n\n**Неисправность:** {issue}\n\n*Дата: {datetime.now().strftime('%d.%m.%Y')}*")
                st.caption("Нажмите Ctrl+P (или три точки в браузере -> Печать) для отправки на принтер.")
            else:
                st.error("Заполните обязательные поля: Клиент, Телефон, Устройство!")

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
            if model and price_buyout > 0:
                df_skupka = load_data("Скупка")
                new_id = len(df_skupka) + 1 if not df_skupka.empty else 1
                new_row = pd.DataFrame([{
                    "ID": int(new_id),
                    "Дата": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Модель": model,
                    "Характеристики": specs,
                    "Цена_Закупки": price_buy,
                    "Продавец": seller,
                    "Статус": "На складе",
                    "Цена_Продажи": "",
                    "Дата_Продажи": ""
                }])
                df_combined = pd.concat([df_skupka, new_row], ignore_index=True)
                save_data(df_combined, "Скупка")
                st.success(f"Устройство №{new_id} добавлено на склад скупки!")
                
                # Договор скупки
                st.markdown("### 🖨 АКТ НА ВЫКУП ТЕХНИКИ")
                st.info(f"**АКТ СКУПКИ №{new_id}**\n\n**Устройство:** {model} ({specs})\n\n**Цена выкупа:** {price_buy} руб.\n\n**Продавец:** {seller}\n\n*Подпись приемщика: _________  Подпись продавца: _________*")
            else:
                st.error("Введите модель и цену закупки!")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    df_skupka = load_data("Скупка")
    
    if not df_skupka.empty and "Статус" in df_skupka.columns:
        # Фильтруем только то, что лежит на складе
        in_stock = df_skupka[df_skupka["Статус"] == "На складе"]
        
        if in_stock.empty:
            st.info("На складе нет доступных телефонов для продажи.")
        else:
            # Создаем список для выбора устройства
            options = {f"№{row['ID']} - {row['Модель']} ({row['Характеристики']}) [Закупка: {row['Цена_Закупки']} руб.]": row['ID'] for _, row in in_stock.iterrows()}
            selected_option = st.selectbox("Выберите устройство для продажи:", list(options.keys()))
            selected_id = options[selected_option]
            
            price_sell = st.number_input("Цена продажи (руб.)", min_value=0, step=100)
            
            if st.button("Оформить продажу"):
                if price_sell > 0:
                    # Находим нужную строчку в исходной таблице скупки и обновляем данные
                    idx = df_skupka[df_skupka["ID"] == selected_id].index[0]
                    df_skupka.at[idx, "Статус"] = "Продано"
                    df_skupka.at[idx, "Цена_Продажи"] = price_sell
                    df_skupka.at[idx, "Дата_Продажи"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    save_data(df_skupka, "Скупка")
                    st.success("Продажа успешно зафиксирована!")
                    
                    # Товарный чек
                    st.markdown("### 🖨 ТОВАРНЫЙ ЧЕК")
                    st.warning(f"**ТОВАРНЫЙ ЧЕК**\n\n**Товар:** {df_skupka.at[idx, 'Модель']}\n\n**Цена:** {price_sell} руб.\n\n*Спасибо за покупку!*")
                    st.rerun()
                else:
                    st.error("Введите цену продажи!")
    else:
        st.info("Склад пуст.")
