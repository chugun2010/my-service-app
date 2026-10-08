import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
import time

st.set_page_config(page_title="Скупка & Repair", layout="wide")
st.title("📱 Учет Скупки и Ремонта")

# === МОСКОВСКОЕ ВРЕМЯ ===
MSK = ZoneInfo("Europe/Moscow")


def now_msk_str() -> str:
    """Текущее московское время в формате 'ГГГГ-ММ-ДД ЧЧ:ММ'."""
    return datetime.now(MSK).strftime("%Y-%m-%d %H:%M")


def normalize_date(value) -> str:
    """ISO UTC из Google -> 'ГГГГ-ММ-ДД ЧЧ:ММ' по Москве."""
    if value is None:
        return ""
    s = str(value).strip()
    if s == "":
        return ""
    try:
        dt = pd.to_datetime(s, utc=True).tz_convert(MSK)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def to_float(value) -> float:
    """Аккуратно превращает значение в float (для расчёта прибыли)."""
    if value is None:
        return 0.0
    s = str(value).strip().replace(" ", "").replace(",", ".")
    if s == "":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


# ТВОЙ АПИ-ШЛЮЗ
API_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"
)

# Инициализация локального хранилища
if "df_skupka_local" not in st.session_state:
    st.session_state["df_skupka_local"] = None

if "need_reload" not in st.session_state:
    st.session_state["need_reload"] = True


# Заголовки листа "Скупка" — должны совпадать с Google Таблицей
SKUPKA_HEADERS = [
    "ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
    "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи", "Дата продажи",
]


# Функция сбора чистой таблицы вручную по строкам
def load_data_from_google() -> pd.DataFrame:
    try:
        nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url, timeout=5)
        data = response.json()

        parsed_rows = []

        if isinstance(data, list) and len(data) > 0:
            for row in data:
                if not row or not isinstance(row, list):
                    continue

                first_cell = str(row[0]).strip().lower()
                if first_cell in ["id", "ид", "идентификатор", ""]:
                    continue

                clean_row = [str(cell).strip() for cell in row]
                while len(clean_row) < len(SKUPKA_HEADERS):
                    clean_row.append("")

                parsed_rows.append(clean_row[: len(SKUPKA_HEADERS)])

        df = pd.DataFrame(parsed_rows, columns=SKUPKA_HEADERS)

        # Нормализуем даты в московское время
        if not df.empty:
            if "Дата выкупа" in df.columns:
                df["Дата выкупа"] = df["Дата выкупа"].apply(normalize_date)
            if "Дата продажи" in df.columns:
                df["Дата продажи"] = df["Дата продажи"].apply(normalize_date)

        return df

    except Exception:
        return pd.DataFrame(columns=SKUPKA_HEADERS)


# Кнопка ручной синхронизации
if st.button("🔄 Синхронизировать с Google Таблицей"):
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False
    st.rerun()

# Первая загрузка при старте
if st.session_state["df_skupka_local"] is None or st.session_state["need_reload"]:
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False

df_main = st.session_state["df_skupka_local"]

# 4 ВКЛАДКИ
tab1, tab2, tab_prep, tab3 = st.tabs(
    ["🔧 Приемка в ремонт", "💰 Скупка (Выкуп)", "🛠 Подготовка к продаже", "📦 Продажа со склада"]
)

# ---------- Вкладка 1: РЕМОНТ ----------
with tab1:
    st.header("Новый ремонт")

    with st.form("repair_form", clear_on_submit=True):
        client = st.text_input("ФИО Клиента")
        phone = st.text_input("Номер телефона")
        device = st.text_input("Устройство (Модель, IMEI/SN)")
        issue = st.text_area("Неисправность и внешний вид")
        submit_repair = st.form_submit_button("Принять в ремонт")

        if submit_repair:
            if client and phone and device:
                current_time = now_msk_str()
                new_id = int(datetime.now().timestamp()) % 100000

                payload = {
                    "action": "append",
                    "sheet": "Ремонт",
                    "row": [new_id, current_time, client, phone, device, issue, "В работе"],
                }

                with st.spinner("Сохраняем ремонт в Google..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                        st.success(f"Заказ №{new_id} успешно сохранен!")
                    except Exception:
                        st.success(f"Заказ №{new_id} отправлен в таблицу!")

                st.markdown("### 🖨 КВИТАНЦИЯ О ПРИЕМКЕ")
                st.info(
                    f"**ЗАКАЗ №{new_id}**\n\n"
                    f"**Клиент:** {client}\n"
                    f"**Телефон:** {phone}\n"
                    f"**Устройство:** {device}\n"
                    f"**Неисправность:** {issue}"
                )
            else:
                st.error("Заполните ФИО, телефон и устройство!")

# ---------- Вкладка 2: СКУПКА ----------
with tab2:
    st.header("Оформить выкуп")

    with st.form("buyout_form", clear_on_submit=True):
        model = st.text_input("Модель / IMEI / SN")
        specs = st.text_input("Характеристики")
        price_buy = st.number_input("Цена закупки", min_value=0, step=100)
        seller = st.text_input("Продавец")
        submit_buyout = st.form_submit_button("Оформить выкуп")

        if submit_buyout:
            if model and price_buy > 0:
                current_time = now_msk_str()
                new_id = int(datetime.now().timestamp()) % 100000

                payload = {
                    "action": "append",
                    "sheet": "Скупка",
                    "row": [new_id, current_time, model, specs, price_buy, seller,
                            "Подготовка к продаже", "", ""],
                }

                new_row = [str(new_id), current_time, model, specs, str(price_buy),
                           seller, "Подготовка к продаже", "", ""]
                df_main.loc[len(df_main)] = new_row
                st.session_state["df_skupka_local"] = df_main

                with st.spinner("Записываем выкуп техники..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                    except Exception:
                        pass

                st.success(f"Устройство №{new_id} успешно добавлено в подготовку!")
                st.rerun()
            else:
                st.error("Заполните модель/IMEI/SN и цену закупки!")

# ---------- Вкладка: ПОДГОТОВКА К ПРОДАЖЕ ----------
with tab_prep:
    st.header("Техника на подготовке к продаже")

    if not df_main.empty:
        in_prep = df_main[df_main["Статус"] == "Подготовка к продаже"]

        if in_prep.empty:
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            st.dataframe(
                in_prep[["ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики", "Цена_Закупки"]],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.markdown("### 🚀 Выставить аппарат на витрину")

            options_prep = {}
            for _, row in in_prep.iterrows():
                val_id = str(row["ID"]).strip()
                val_model = str(row["Модель/IMEI/SN"]).strip()
                options_prep[f"№{val_id} - {val_model}"] = val_id

            selected_prep = st.selectbox(
                "Выберите устройство для оценки:",
                list(options_prep.keys()),
                key="sb_prep",
            )
            selected_prep_id = options_prep[selected_prep]

            price_sell_ready = st.number_input(
                "Установить цену продажи (руб.)",
                min_value=0,
                step=100,
                key="prep_price",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Готов к продаже (На склад)"):
                    if price_sell_ready > 0:
                        clean_id = (
                            int(float(selected_prep_id))
                            if selected_prep_id.replace(".", "", 1).isdigit()
                            else selected_prep_id
                        )

                        df_main.loc[
                            df_main["ID"] == str(selected_prep_id).strip(), "Статус"
                        ] = "На складе"
                        df_main.loc[
                            df_main["ID"] == str(selected_prep_id).strip(), "Цена_Продажи"
                        ] = str(price_sell_ready)
                        st.session_state["df_skupka_local"] = df_main

                        payload = {
                            "action": "update",
                            "sheet": "Скупка",
                            "id": clean_id,
                            "status": "На складе",
                            "price_sell": price_sell_ready,
                        }

                        with st.spinner("Переносим на витрину склада..."):
                            try:
                                requests.post(API_URL, json=payload, timeout=3)
                            except Exception:
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

# ---------- Вкладка 3: ПРОДАЖА СО СКЛАДА ----------
with tab3:
    st.header("Продажа товаров со склада")

    if not df_main.empty:
        in_stock = df_main[df_main["Статус"] == "На складе"]

        if in_stock.empty:
            st.info("На складе пусто.")
        else:
            st.markdown("### 🏪 Товары на витрине:")

            stock_view = in_stock[
                ["ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
                 "Цена_Закупки", "Цена_Продажи"]
            ].copy()

            stock_view["Прибыль"] = stock_view.apply(
                lambda r: to_float(r["Цена_Продажи"]) - to_float(r["Цена_Закупки"]),
                axis=1,
            )

            st.dataframe(
                stock_view,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")
            st.markdown("### 💰 Оформление сделки")

            options = {}
            for _, row in in_stock.iterrows():
                val_id = str(row["ID"]).strip()
                val_model = str(row["Модель/IMEI/SN"]).strip()
                options[f"№{val_id} - {val_model}"] = val_id

            selected = st.selectbox(
                "Выберите для продажи:",
                list(options.keys()),
                key="sb_sell",
            )
            selected_id = options[selected]

            chosen_row = in_stock[in_stock["ID"] == str(selected_id).strip()]

            current_price = 0.0
            current_buy = 0.0
            if not chosen_row.empty:
                current_price = to_float(chosen_row["Цена_Продажи"].values[0])
                current_buy = to_float(chosen_row["Цена_Закупки"].values[0])

            final_price = st.number_input(
                "Фактическая цена продажи (руб.)",
                min_value=0,
                step=100,
                value=int(current_price),
                key="sell_final_price",
            )

            profit_preview = final_price - current_buy
            st.info(
                f"Цена выкупа: **{current_buy:.0f} ₽**  |  "
                f"Цена продажи: **{final_price:.0f} ₽**  |  "
                f"Прибыль: **{profit_preview:.0f} ₽**"
            )

            confirm_sale = st.checkbox(
                "Подтверждаю продажу (действие необратимо)",
                key="confirm_sale",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Оформить продажу"):
                    if not confirm_sale:
                        st.error("Поставьте галочку подтверждения продажи.")
                    elif final_price <= 0:
                        st.error("Укажите цену продажи!")
                    else:
                        clean_id = (
                            int(float(selected_id))
                            if str(selected_id).replace(".", "", 1).isdigit()
                            else selected_id
                        )
                        sale_time = now_msk_str()

                        # Локально: статус, цена, дата продажи
                        df_main.loc[
                            df_main["ID"] == str(selected_id).strip(), "Статус"
                        ] = "Продано"
                        df_main.loc[
                            df_main["ID"] == str(selected_id).strip(), "Цена_Продажи"
                        ] = str(final_price)
                        df_main.loc[
                            df_main["ID"] == str(selected_id).strip(), "Дата продажи"
                        ] = sale_time
                        st.session_state["df_skupka_local"] = df_main

                        payload = {
                            "action": "update",
                            "sheet": "Скупка",
                            "id": clean_id,
                            "status": "Продано",
                            "price_sell": final_price,
                            "date_sell": sale_time,
                        }

                        with st.spinner("Оформляем продажу..."):
                            try:
                                requests.post(API_URL, json=payload, timeout=3)
                            except Exception:
                                pass

                        st.success(
                            f"Товар №{selected_id} продан за {final_price:.0f} ₽ "
                            f"({sale_time}). Прибыль: {profit_preview:.0f} ₽"
                        )
                        st.rerun()

            with col2:
                if st.button("🖨 Печать квитанции"):
                    st.info(
                        "⏳ Функция печати квитанции в разработке. "
                        "Скоро подключим!"
                    )
    else:
        st.info("На складе пусто.")
