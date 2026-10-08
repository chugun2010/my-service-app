import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Скупка & Ремонт", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# ID вашей таблицы, взятый прямо с вашего экрана
SPREADSHEET_ID = "1xFtd73X75f_p7MMtT9tiFVv_gKk4-ENqS3oHtQrk1AA"
READ_URL = f"https://google.com{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"

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
                
                st.success(f"Заказ №{new_id} успешно зафиксирован!")
                st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                st.info(f"**ЗАКАЗ №{new_id}**\n\n**Клиент:** {client} ({phone})\n\n**Устройство:** {device}\n\n**Неисправность:** {issue}\n\n*Дата: {current_time}*")
            else:
                st.error("Заполните поля: Клиент, Телефон, Устройство!")

# ---------------- Вкладка 2: СКУПКА ----------------
with tab2:
    st.header("Оформить выкуп устройства")
    with st.form("buyout_form", clear_on_submit=True):
        model = st.text_input("Модель телефона")
        specs = st.text_input("Характеристики (Память, цвет, состояние)")
        price_buy = st.number_input("Цена закупки (руб.)", min_value=0, step=100)
        submit_buyout = st.form_submit_button("Оформить выкуп")
        
        if submit_buyout:
            if model and price_buy > 0:
                new_id = int(datetime.now().timestamp()) % 100000
                st.success(f"Устройство №{new_id} ({model}) успешно добавлено на склад!")
                st.markdown("### 🖨 АКТ НА ВЫКУП ТЕХНИКИ")
                st.info(f"**АКТ СКУПКИ №{new_id}**\n\n**Устройство:** {model} ({specs})\n\n**Цена выкупа:** {price_buy} руб.")
            else:
                st.error("Введите модель и цену закупки!")

# ---------------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------------
with tab3:
    st.header("Продажа товаров со склада")
    try:
        df_skupka = pd.read_csv(f"{READ_URL}&sheet=Скупка").dropna(how="all")
    except:
        df_skupka = pd.DataFrame()
    
    if not df_skupka.empty and "Статус" in df_skupka.columns:
        in_stock = df_skupka[df_skupka["Статус"] == "На складе"]
        if in_stock.empty:
            st.info("На складе нет доступных телефонов для продажи.")
        else:
            options = {f"№{row['ID']} - {row['Модель']} ({row['Характеристики']})": row['ID'] for _, row in in_stock.iterrows()}
            selected_option = st.selectbox("Выберите устройство для продажи:", list(options.keys()))
            price_sell = st.number_input("Цена продажи (руб.)", min_value=0, step=100)
            
            if st.button("Оформить продажу"):
                if price_sell > 0:
                    st.success("Продажа успешно оформлена!")
                else:
                    st.error("Введите цену продажи!")
    else:
        st.info("На складе пока нет активных остатков.")
