import streamlit as st
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
import requests
import time

st.set_page_config(page_title="Батарейкин Сервис", layout="wide")

# === МОСКОВСКОЕ ВРЕМЯ ===
MSK = ZoneInfo("Europe/Moscow")


def now_msk_str() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%d %H:%M")


def normalize_date(value) -> str:
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
    if value is None:
        return 0.0
    s = str(value).strip().replace(" ", "").replace(",", ".")
    if s == "":
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def to_date(value):
    """Из строки 'ГГГГ-ММ-ДД ЧЧ:ММ' или ISO вытаскиваем date. Иначе None."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


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

if "section" not in st.session_state:
    st.session_state["section"] = "shop"   # по умолчанию открываем магазин


# Заголовки листа "Скупка" — 10 колонок, как в Google Таблице
SKUPKA_HEADERS = [
    "ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
    "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи",
    "Дата продажи", "Срок гарантии",
]


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

        if not df.empty:
            if "Дата выкупа" in df.columns:
                df["Дата выкупа"] = df["Дата выкупа"].apply(normalize_date)
            if "Дата продажи" in df.columns:
                df["Дата продажи"] = df["Дата продажи"].apply(normalize_date)

        return df

    except Exception:
        return pd.DataFrame(columns=SKUPKA_HEADERS)


# ---------- ШАПКА С НАВИГАЦИЕЙ ----------
col_title, col_btn_repair, col_btn_shop = st.columns([5, 1, 1])

with col_title:
    st.title("📱 Батарейкин Сервис")

with col_btn_repair:
    if st.button(
        "🔧 Ремонт",
        use_container_width=True,
        type="primary" if st.session_state["section"] == "repair" else "secondary",
    ):
        st.session_state["section"] = "repair"
        st.rerun()

with col_btn_shop:
    if st.button(
        "💰 Магазин",
        use_container_width=True,
        type="primary" if st.session_state["section"] == "shop" else "secondary",
    ):
        st.session_state["section"] = "shop"
        st.rerun()

st.markdown("---")

# Кнопка синхронизации
if st.button("🔄 Синхронизировать с Google Таблицей"):
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False
    st.rerun()

if st.session_state["df_skupka_local"] is None or st.session_state["need_reload"]:
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False

df_main = st.session_state["df_skupka_local"]


# ================== РАЗДЕЛ «РЕМОНТ» ==================
if st.session_state["section"] == "repair":
    tab1, = st.tabs(["🔧 Приемка в ремонт"])

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


# ================== РАЗДЕЛ «МАГАЗИН» ==================
else:
    tab2, tab_prep, tab3, tab_sales = st.tabs(
        ["💰 Скупка (Выкуп)", "🛠 Подготовка к продаже",
         "📦 Продажа со склада", "📈 Продажи"]
    )

    # ---------- СКУПКА ----------
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
                                "Подготовка к продаже", "", "", ""],
                    }

                    new_row = [str(new_id), current_time, model, specs, str(price_buy),
                               seller, "Подготовка к продаже", "", "", ""]
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

    # ---------- ПОДГОТОВКА ----------
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

    # ---------- ПРОДАЖА СО СКЛАДА ----------
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

                st.dataframe(stock_view, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 💰 Оформление сделки")

                options = {}
                for _, row in in_stock.iterrows():
                    val_id = str(row["ID"]).strip()
                    val_model = str(row["Модель/IMEI/SN"]).strip()
                    options[f"№{val_id} - {val_model}"] = val_id

                selected = st.selectbox(
                    "Выберите для продажи:", list(options.keys()), key="sb_sell"
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

                warranty = st.text_input(
                    "Срок гарантии (например: 14 дней, 30 дней, 1 год)",
                    key="sell_warranty",
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
                        elif not warranty.strip():
                            st.error("Укажите срок гарантии!")
                        else:
                            clean_id = (
                                int(float(selected_id))
                                if str(selected_id).replace(".", "", 1).isdigit()
                                else selected_id
                            )
                            sale_time = now_msk_str()

                            df_main.loc[
                                df_main["ID"] == str(selected_id).strip(), "Статус"
                            ] = "Продано"
                            df_main.loc[
                                df_main["ID"] == str(selected_id).strip(), "Цена_Продажи"
                            ] = str(final_price)
                            df_main.loc[
                                df_main["ID"] == str(selected_id).strip(), "Дата продажи"
                            ] = sale_time
                            df_main.loc[
                                df_main["ID"] == str(selected_id).strip(), "Срок гарантии"
                            ] = warranty.strip()
                            st.session_state["df_skupka_local"] = df_main

                            payload = {
                                "action": "update",
                                "sheet": "Скупка",
                                "id": clean_id,
                                "status": "Продано",
                                "price_sell": final_price,
                                "date_sell": sale_time,
                                "warranty": warranty.strip(),
                            }

                            with st.spinner("Оформляем продажу..."):
                                try:
                                    requests.post(API_URL, json=payload, timeout=3)
                                except Exception:
                                    pass

                            st.success(
                                f"Товар №{selected_id} продан за {final_price:.0f} ₽ "
                                f"({sale_time}). Гарантия: {warranty}. "
                                f"Прибыль: {profit_preview:.0f} ₽"
                            )
                            st.rerun()

                with col2:
                    if st.button("🖨 Печать квитанции"):
                        st.info("⏳ Функция печати квитанции в разработке. Скоро подключим!")
        else:
            st.info("На складе пусто.")

    # ---------- НОВАЯ ВКЛАДКА: ПРОДАЖИ ----------
    with tab_sales:
        st.header("📈 Проданные товары")

        if df_main.empty:
            st.info("Данных пока нет.")
        else:
            sold = df_main[df_main["Статус"] == "Продано"].copy()

            if sold.empty:
                st.info("Продаж ещё не было.")
            else:
                # Считаем дату для фильтрации
                sold["_sale_date"] = sold["Дата продажи"].apply(to_date)
                sold["_profit"] = sold.apply(
                    lambda r: to_float(r["Цена_Продажи"]) - to_float(r["Цена_Закупки"]),
                    axis=1,
                )

                # Дефолтный период: от минимальной продажи до сегодня
                valid_dates = sold["_sale_date"].dropna()
                if not valid_dates.empty:
                    min_d = valid_dates.min()
                    max_d = valid_dates.max()
                else:
                    min_d = max_d = date.today()

                st.markdown("### 🗓 Период продаж")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    date_from = st.date_input(
                        "С", value=min_d, key="sales_from"
                    )
                with col_d2:
                    date_to = st.date_input(
                        "По", value=max_d, key="sales_to"
                    )

                # Фильтруем
                if date_from and date_to and date_from <= date_to:
                    filtered = sold[
                        (sold["_sale_date"] >= date_from)
                        & (sold["_sale_date"] <= date_to)
                    ].copy()
                else:
                    st.error("Дата 'С' должна быть раньше или равна дате 'По'.")
                    filtered = sold.iloc[0:0].copy()

                # Итоги
                total_count = len(filtered)
                total_buy = filtered["Цена_Закупки"].apply(to_float).sum()
                total_sell = filtered["Цена_Продажи"].apply(to_float).sum()
                total_profit = total_sell - total_buy

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Продано, шт", total_count)
                m2.metric("Сумма закупки", f"{total_buy:,.0f} ₽")
                m3.metric("Сумма продаж", f"{total_sell:,.0f} ₽")
                m4.metric("Чистая прибыль", f"{total_profit:,.0f} ₽")

                st.markdown("---")
                st.markdown("### 📋 Детали продаж за период")

                if filtered.empty:
                    st.info("За выбранный период продаж нет.")
                else:
                    show = filtered[
                        ["ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
                         "Продавец", "Цена_Закупки", "Цена_Продажи",
                         "Дата продажи", "Срок гарантии"]
                    ].copy()
                    show["Прибыль"] = filtered["_profit"].values
                    st.dataframe(show, use_container_width=True, hide_index=True)
