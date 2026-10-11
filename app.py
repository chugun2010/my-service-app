import streamlit as st
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
import requests
import time

st.set_page_config(page_title="Батарейкин Сервис", layout="wide")

# ================== СТИЛИ ==================
st.markdown(
    """
    <style>
    button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {
        background-color: #B5E8A8 !important;
        color: #1a3a1a !important;
        border: 1px solid #8ED17E !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        background-color: #9DDD8C !important;
        border: 1px solid #7BC56A !important;
        color: #0d2a0d !important;
    }
    button[kind="primary"] p,
    button[data-testid="stBaseButton-primary"] p {
        color: #1a3a1a !important;
    }
    .hdr-btn {
        display: inline-block;
        padding: 6px 12px;
        font-size: 13px;
        line-height: 1.2;
        color: #444 !important;
        text-decoration: none !important;
        border: 1px solid #ccc;
        border-radius: 6px;
        background: #fafafa;
        white-space: nowrap;
        vertical-align: middle;
    }
    .hdr-btn:hover {
        background: #efefef;
        color: #000 !important;
        border-color: #999;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ================== АВТОРИЗАЦИЯ ==================
def check_password() -> bool:
    if st.session_state.get("auth_ok"):
        return True

    st.markdown("## 🔒 Вход в Батарейкин Сервис")
    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Логин:", key="login_user")
        pwd = st.text_input("Пароль:", type="password", key="login_pwd")
        if st.button("Войти", use_container_width=True):
            users = st.secrets.get("users", {})
            if username in users and users[username] == pwd:
                st.session_state["auth_ok"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("❌ Неверный логин или пароль.")
    return False


if st.query_params.get("logout") == "1":
    st.session_state["auth_ok"] = False
    st.session_state["username"] = ""
    st.query_params.clear()
    st.rerun()

if not check_password():
    st.stop()


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


def clean_id_for_api(val):
    s = str(val).strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return s


CATEGORIES = {
    "📱 Смартфоны": "S",
    "🖥️ ПК": "P",
    "🛒 Комплектующие": "K",
    "🔋 Электроника": "E",
}

EMOJI_PREFIXES = ["📱 ", "🖥️ ", "🛒 ", "🔋 "]


def strip_emoji(name: str) -> str:
    """Убирает смайлик-префикс, чтобы получить реальное имя листа Google."""
    for emoji in EMOJI_PREFIXES:
        if name.startswith(emoji):
            return name[len(emoji):]
    return name


def next_shop_id(df, prefix: str) -> str:
    max_num = 0
    for v in df["ID"].astype(str):
        v = v.strip()
        if v.startswith(f"{prefix}-"):
            try:
                n = int(v[2:])
                if n > max_num:
                    max_num = n
            except ValueError:
                pass
    return f"{prefix}-{max_num + 1:04d}"


def next_repair_id() -> str:
    try:
        url = f"{API_URL}?sheet=Ремонт&t={time.time()}"
        r = requests.get(url, timeout=5)
        data = r.json()
        max_num = 0
        for row in data:
            if not row or not isinstance(row, list):
                continue
            v = str(row[0]).strip()
            if v.startswith("R-"):
                try:
                    n = int(v[2:])
                    if n > max_num:
                        max_num = n
                except ValueError:
                    pass
        return f"R-{max_num + 1:04d}"
    except Exception:
        return f"R-{int(datetime.now().timestamp()) % 100000}"


API_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"
)

SHOP_HEADERS = [
    "ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
    "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи",
    "Дата продажи", "Срок гарантии", "Стоимость_запчастей",
]

if "df_cache" not in st.session_state:
    st.session_state["df_cache"] = {}
if "section" not in st.session_state:
    st.session_state["section"] = "shop"
if "category" not in st.session_state:
    st.session_state["category"] = None
if "flash" not in st.session_state:
    st.session_state["flash"] = []


def flash(kind: str, text: str):
    st.session_state["flash"].append((kind, text))


def show_flash():
    for kind, text in st.session_state["flash"]:
        if kind == "success":
            st.success(text)
        elif kind == "info":
            st.info(text)
        elif kind == "warning":
            st.warning(text)
        else:
            st.error(text)
    st.session_state["flash"] = []


def load_data_from_google(sheet_name: str) -> pd.DataFrame:
    clean_sheet = strip_emoji(sheet_name)
    try:
        nocache_url = f"{API_URL}?sheet={clean_sheet}&t={time.time()}"
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
                while len(clean_row) < len(SHOP_HEADERS):
                    clean_row.append("")
                parsed_rows.append(clean_row[: len(SHOP_HEADERS)])

        df = pd.DataFrame(parsed_rows, columns=SHOP_HEADERS)

        if not df.empty:
            if "Дата выкупа" in df.columns:
                df["Дата выкупа"] = df["Дата выкупа"].apply(normalize_date)
            if "Дата продажи" in df.columns:
                df["Дата продажи"] = df["Дата продажи"].apply(normalize_date)

        return df

    except Exception:
        return pd.DataFrame(columns=SHOP_HEADERS)


# ================== ОБРАБОТКА ?sync=1 ==================
if st.query_params.get("sync") == "1":
    st.query_params.clear()
    if st.session_state["section"] == "shop" and st.session_state.get("category"):
        cat = st.session_state["category"]
        with st.spinner(f"Обновляем «{cat}»..."):
            st.session_state["df_cache"][cat] = load_data_from_google(cat)
        flash("success", f"✅ Данные «{cat}» синхронизированы.")
    elif st.session_state["section"] == "shop":
        flash("info", "Сначала выберите категорию товара.")
    else:
        flash("info", "Синхронизация доступна в разделе «Магазин».")
    st.rerun()


# ---------- ШАПКА ----------
current_user = st.session_state.get("username", "")
st.markdown(
    f"""
    <div style="padding:0 0 10px 0;">
      <div style="font-size:44px; font-weight:800; margin-bottom:8px; letter-spacing:-0.5px;">📱 Батарейкин Сервис</div>
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="color:#555; font-size:13px;">👤 Вошёл как: <b>{current_user}</b></span>
        <a href="?logout=1" class="hdr-btn" target="_self">🚪 Выйти</a>
        <a href="?sync=1" class="hdr-btn" target="_self">🔄 Синхронизация</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col_spacer, col_btn_repair, col_btn_shop = st.columns([5, 1, 1])

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

# Кнопки категорий (только для магазина)
if st.session_state["section"] == "shop":
    cat_cols = st.columns(len(CATEGORIES))
    for i, cat_name in enumerate(CATEGORIES.keys()):
        with cat_cols[i]:
            is_active = st.session_state.get("category") == cat_name
            if st.button(
                cat_name,
                use_container_width=True,
                type="primary" if is_active else "secondary",
                key=f"cat_btn_{cat_name}",
            ):
                st.session_state["category"] = cat_name
                if cat_name not in st.session_state["df_cache"]:
                    with st.spinner(f"Загружаем «{cat_name}»..."):
                        st.session_state["df_cache"][cat_name] = load_data_from_google(cat_name)
                st.rerun()

st.markdown("---")

show_flash()


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
                    new_id = next_repair_id()

                    payload = {
                        "action": "append",
                        "sheet": "Ремонт",
                        "row": [new_id, current_time, client, phone, device, issue, "В работе"],
                    }

                    with st.spinner("Сохраняем ремонт в Google..."):
                        try:
                            requests.post(API_URL, json=payload, timeout=5)
                            flash("success", f"✅ Ремонт №{new_id} принят и сохранён.")
                        except Exception:
                            flash("warning", f"⚠️ Ремонт №{new_id} сформирован, но не ушёл в Google.")

                    st.rerun()
                else:
                    st.error("Заполните ФИО, телефон и устройство!")


# ================== РАЗДЕЛ «МАГАЗИН» ==================
else:
    current_cat = st.session_state.get("category")

    if not current_cat:
        st.info("👆 Выберите категорию товара выше, чтобы начать работу.")
    else:
        df_main = st.session_state["df_cache"].get(current_cat)
        if df_main is None:
            df_main = load_data_from_google(current_cat)
            st.session_state["df_cache"][current_cat] = df_main

        prefix = CATEGORIES[current_cat]
        sheet_name_clean = strip_emoji(current_cat)

        tab2, tab_prep, tab3, tab_sales = st.tabs(
            ["💰 Скупка (Выкуп)", "🛠 Подготовка к продаже",
             "📦 Продажа со склада", "📈 Продажи"]
        )

        # ---------- СКУПКА ----------
        with tab2:
            st.header(f"Оформить выкуп — {current_cat}")

            with st.form(f"buyout_form_{current_cat}", clear_on_submit=True):
                model = st.text_input("Модель / IMEI / SN")
                specs = st.text_input("Характеристики")
                price_buy = st.number_input("Цена закупки", min_value=0, step=100)
                seller = st.text_input("Продавец")
                submit_buyout = st.form_submit_button("Оформить выкуп")

                if submit_buyout:
                    if model and price_buy > 0:
                        current_time = now_msk_str()
                        new_id = next_shop_id(df_main, prefix)

                        payload = {
                            "action": "append",
                            "sheet": sheet_name_clean,
                            "row": [new_id, current_time, model, specs, price_buy, seller,
                                    "Подготовка к продаже", "", "", "", ""],
                        }

                        new_row = [new_id, current_time, model, specs, str(price_buy),
                                   seller, "Подготовка к продаже", "", "", "", ""]
                        df_main.loc[len(df_main)] = new_row
                        st.session_state["df_cache"][current_cat] = df_main

                        with st.spinner("Записываем выкуп в Google Таблицу..."):
                            try:
                                requests.post(API_URL, json=payload, timeout=5)
                                flash("success", f"✅ Товар {new_id} выкуплен за {price_buy} ₽.")
                            except Exception:
                                flash("warning", f"⚠️ Товар {new_id} добавлен локально, но не ушёл в Google.")

                        st.rerun()
                    else:
                        st.error("Заполните модель/IMEI/SN и цену закупки!")

        # ---------- ПОДГОТОВКА ----------
        with tab_prep:
            st.header(f"Техника на подготовке — {current_cat}")

            if df_main.empty:
                st.info("На подготовке пока пусто.")
            else:
                in_prep = df_main[df_main["Статус"] == "Подготовка к продаже"]

                if in_prep.empty:
                    st.info("Сейчас нет техники на подготовке к продаже.")
                else:
                    st.markdown("### 📋 Список устройств в работе:")
                    st.dataframe(
                        in_prep[["ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики", "Цена_Закупки", "Стоимость_запчастей"]],
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
                        key=f"sb_prep_{current_cat}",
                    )
                    selected_prep_id = options_prep[selected_prep]

                    chosen_prep = in_prep[in_prep["ID"] == str(selected_prep_id).strip()]
                    buy_price_here = 0.0
                    existing_parts = 0.0
                    if not chosen_prep.empty:
                        buy_price_here = to_float(chosen_prep["Цена_Закупки"].values[0])
                        existing_parts = to_float(chosen_prep["Стоимость_запчастей"].values[0])

                    col_price, col_parts = st.columns(2)
                    with col_price:
                        price_sell_ready = st.number_input(
                            "Установить цену продажи (руб.)",
                            min_value=0, step=100, key=f"prep_price_{current_cat}",
                        )
                    with col_parts:
                        parts_cost_add = st.number_input(
                            "Добавить запчастей на сумму (руб.)",
                            min_value=0, step=100, key=f"prep_parts_{current_cat}",
                        )

                    total_parts = existing_parts + parts_cost_add
                    est_profit = price_sell_ready - buy_price_here - total_parts
                    st.info(
                        f"Выкуп: **{buy_price_here:.0f} ₽**  |  "
                        f"Запчасти уже: **{existing_parts:.0f} ₽**  |  "
                        f"Добавляем: **{parts_cost_add:.0f} ₽**  |  "
                        f"Итого запчастей: **{total_parts:.0f} ₽**  |  "
                        f"Продажа: **{price_sell_ready:.0f} ₽**  |  "
                        f"Ожидаемая прибыль: **{est_profit:.0f} ₽**"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("✅ Готов к продаже (На склад)", key=f"btn_ready_{current_cat}"):
                            if price_sell_ready > 0:
                                clean_id = clean_id_for_api(selected_prep_id)

                                df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Статус"] = "На складе"
                                df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Цена_Продажи"] = str(price_sell_ready)
                                df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Стоимость_запчастей"] = str(total_parts)
                                st.session_state["df_cache"][current_cat] = df_main

                                payload = {
                                    "action": "update",
                                    "sheet": sheet_name_clean,
                                    "id": clean_id,
                                    "status": "На складе",
                                    "price_sell": price_sell_ready,
                                    "parts_cost": total_parts,
                                }

                                with st.spinner("Переносим на витрину склада..."):
                                    try:
                                        requests.post(API_URL, json=payload, timeout=5)
                                        flash(
                                            "success",
                                            f"✅ Товар №{selected_prep_id} перемещён на витрину. "
                                            f"Цена: {price_sell_ready} ₽, запчасти: {total_parts:.0f} ₽.",
                                        )
                                    except Exception:
                                        flash("warning", "⚠️ Обновлено локально, но не ушло в Google.")

                                st.rerun()
                            else:
                                st.error("Укажите цену продажи!")

                    with col2:
                        if st.button("🖨 Печать этикетки штрих-кода", key=f"btn_label_{current_cat}"):
                            st.info("⏳ Функция печати в разработке. Скоро подключим!")

                    st.markdown("---")
                    st.markdown("### ⚠️ Опасные действия")

                    confirm_wo_prep = st.checkbox(
                        "Подтверждаю списание — товар уйдёт в утиль",
                        key=f"confirm_wo_prep_{current_cat}",
                    )

                    if st.button("❌ Списать в утиль", key=f"btn_wo_prep_{current_cat}"):
                        if not confirm_wo_prep:
                            st.error("Поставьте галочку подтверждения списания.")
                        else:
                            clean_id = clean_id_for_api(selected_prep_id)
                            df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Статус"] = "Списано"
                            st.session_state["df_cache"][current_cat] = df_main

                            payload = {
                                "action": "update",
                                "sheet": sheet_name_clean,
                                "id": clean_id,
                                "status": "Списано",
                            }
                            with st.spinner("Списываем в утиль..."):
                                try:
                                    requests.post(API_URL, json=payload, timeout=5)
                                    flash("warning", f"❌ Товар №{selected_prep_id} списан в утиль.")
                                except Exception:
                                    flash("warning", "⚠️ Обновлено локально, но не ушло в Google.")
                            st.rerun()

        # ---------- ПРОДАЖА СО СКЛАДА ----------
        with tab3:
            st.header(f"Продажа со склада — {current_cat}")

            if df_main.empty:
                st.info("На складе пусто.")
            else:
                in_stock = df_main[df_main["Статус"] == "На складе"]

                if in_stock.empty:
                    st.info("На складе пусто.")
                else:
                    st.markdown("### 🏪 Товары на витрине:")

                    stock_view = in_stock[
                        ["ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
                         "Цена_Закупки", "Стоимость_запчастей", "Цена_Продажи"]
                    ].copy()
                    stock_view["Прибыль"] = stock_view.apply(
                        lambda r: to_float(r["Цена_Продажи"])
                                  - to_float(r["Цена_Закупки"])
                                  - to_float(r["Стоимость_запчастей"]),
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
                        "Выберите для продажи:",
                        list(options.keys()),
                        key=f"sb_sell_{current_cat}",
                    )
                    selected_id = options[selected]

                    chosen_row = in_stock[in_stock["ID"] == str(selected_id).strip()]
                    current_price = 0.0
                    current_buy = 0.0
                    current_parts = 0.0
                    if not chosen_row.empty:
                        current_price = to_float(chosen_row["Цена_Продажи"].values[0])
                        current_buy = to_float(chosen_row["Цена_Закупки"].values[0])
                        current_parts = to_float(chosen_row["Стоимость_запчастей"].values[0])

                    final_price = st.number_input(
                        "Фактическая цена продажи (руб.)",
                        min_value=0, step=100, value=int(current_price),
                        key=f"sell_final_price_{current_cat}",
                    )
                    warranty = st.text_input(
                        "Срок гарантии (например: 14 дней, 30 дней, 1 год)",
                        key=f"sell_warranty_{current_cat}",
                    )

                    profit_preview = final_price - current_buy - current_parts
                    st.info(
                        f"Выкуп: **{current_buy:.0f} ₽**  |  "
                        f"Запчасти: **{current_parts:.0f} ₽**  |  "
                        f"Продажа: **{final_price:.0f} ₽**  |  "
                        f"Прибыль: **{profit_preview:.0f} ₽**"
                    )

                    confirm_sale = st.checkbox(
                        "Подтверждаю продажу (действие необратимо)",
                        key=f"confirm_sale_{current_cat}",
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("✅ Оформить продажу", key=f"btn_sell_{current_cat}"):
                            if not confirm_sale:
                                st.error("Поставьте галочку подтверждения продажи.")
                            elif final_price <= 0:
                                st.error("Укажите цену продажи!")
                            elif not warranty.strip():
                                st.error("Укажите срок гарантии!")
                            else:
                                clean_id = clean_id_for_api(selected_id)
                                sale_time = now_msk_str()

                                df_main.loc[df_main["ID"] == str(selected_id).strip(), "Статус"] = "Продано"
                                df_main.loc[df_main["ID"] == str(selected_id).strip(), "Цена_Продажи"] = str(final_price)
                                df_main.loc[df_main["ID"] == str(selected_id).strip(), "Дата продажи"] = sale_time
                                df_main.loc[df_main["ID"] == str(selected_id).strip(), "Срок гарантии"] = warranty.strip()
                                st.session_state["df_cache"][current_cat] = df_main

                                payload = {
                                    "action": "update",
                                    "sheet": sheet_name_clean,
                                    "id": clean_id,
                                    "status": "Продано",
                                    "price_sell": final_price,
                                    "date_sell": sale_time,
                                    "warranty": warranty.strip(),
                                }
                                with st.spinner("Оформляем продажу..."):
                                    try:
                                        requests.post(API_URL, json=payload, timeout=5)
                                        flash(
                                            "success",
                                            f"✅ Товар №{selected_id} продан за {final_price:.0f} ₽. "
                                            f"Гарантия: {warranty}. Прибыль: {profit_preview:.0f} ₽.",
                                        )
                                    except Exception:
                                        flash("warning", "⚠️ Обновлено локально, но не ушло в Google.")
                                st.rerun()

                    with col2:
                        if st.button("⬅️ Обратно на подготовку", key=f"btn_back_{current_cat}"):
                            clean_id = clean_id_for_api(selected_id)
                            df_main.loc[df_main["ID"] == str(selected_id).strip(), "Статус"] = "Подготовка к продаже"
                            df_main.loc[df_main["ID"] == str(selected_id).strip(), "Цена_Продажи"] = ""
                            st.session_state["df_cache"][current_cat] = df_main

                            payload = {
                                "action": "update",
                                "sheet": sheet_name_clean,
                                "id": clean_id,
                                "status": "Подготовка к продаже",
                                "price_sell": "",
                            }
                            with st.spinner("Возвращаем товар на подготовку..."):
                                try:
                                    requests.post(API_URL, json=payload, timeout=5)
                                    flash("info", f"⬅️ Товар №{selected_id} возвращён на подготовку.")
                                except Exception:
                                    flash("warning", "⚠️ Обновлено локально, но не ушло в Google.")
                            st.rerun()

                    st.markdown("---")
                    st.markdown("### ⚠️ Опасные действия")

                    confirm_wo_stock = st.checkbox(
                        "Подтверждаю списание — товар уйдёт в утиль",
                        key=f"confirm_wo_stock_{current_cat}",
                    )
                    if st.button("❌ Списать в утиль", key=f"btn_wo_stock_{current_cat}"):
                        if not confirm_wo_stock:
                            st.error("Поставьте галочку подтверждения списания.")
                        else:
                            clean_id = clean_id_for_api(selected_id)
                            df_main.loc[df_main["ID"] == str(selected_id).strip(), "Статус"] = "Списано"
                            st.session_state["df_cache"][current_cat] = df_main
                            payload = {
                                "action": "update",
                                "sheet": sheet_name_clean,
                                "id": clean_id,
                                "status": "Списано",
                            }
                            with st.spinner("Списываем в утиль..."):
                                try:
                                    requests.post(API_URL, json=payload, timeout=5)
                                    flash("warning", f"❌ Товар №{selected_id} списан в утиль.")
                                except Exception:
                                    flash("warning", "⚠️ Обновлено локально, но не ушло в Google.")
                            st.rerun()

                    st.markdown("---")
                    if st.button("🖨 Печать квитанции", key=f"btn_receipt_{current_cat}"):
                        st.info("⏳ Функция печати квитанции в разработке. Скоро подключим!")

        # ---------- ПРОДАЖИ ----------
        with tab_sales:
            st.header(f"📈 Проданные товары — {current_cat}")

            if df_main.empty:
                st.info("Данных пока нет.")
            else:
                sold = df_main[df_main["Статус"] == "Продано"].copy()
                if sold.empty:
                    st.info("Продаж ещё не было.")
                else:
                    sold["_sale_date"] = pd.to_datetime(
                        sold["Дата продажи"], errors="coerce"
                    ).dt.date
                    sold = sold.dropna(subset=["_sale_date"]).copy()
                    sold["_profit"] = sold.apply(
                        lambda r: to_float(r["Цена_Продажи"])
                                  - to_float(r["Цена_Закупки"])
                                  - to_float(r["Стоимость_запчастей"]),
                        axis=1,
                    )

                    if sold.empty:
                        st.info("Продаж ещё не было.")
                    else:
                        min_d = sold["_sale_date"].min()
                        max_d = sold["_sale_date"].max()
                        today = date.today()

                        st.markdown("### 🗓 Период продаж")
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            date_from = st.date_input("С", value=min_d, max_value=today, key=f"sales_from_{current_cat}")
                        with col_d2:
                            date_to = st.date_input("По", value=max_d, max_value=today, key=f"sales_to_{current_cat}")

                        if date_from > date_to:
                            st.error("Дата «С» должна быть раньше или равна дате «По».")
                        else:
                            filtered = sold[
                                (sold["_sale_date"] >= date_from) & (sold["_sale_date"] <= date_to)
                            ].copy()

                            if filtered.empty:
                                st.warning("📭 Продаж не было — работай лучше! 💪")
                            else:
                                total_count = len(filtered)
                                total_buy = float(filtered["Цена_Закупки"].apply(to_float).sum())
                                total_parts = float(filtered["Стоимость_запчастей"].apply(to_float).sum())
                                total_sell = float(filtered["Цена_Продажи"].apply(to_float).sum())
                                total_profit = total_sell - total_buy - total_parts

                                m1, m2, m3, m4, m5 = st.columns(5)
                                m1.metric("Продано, шт", total_count)
                                m2.metric("Закупка", f"{total_buy:,.0f} ₽")
                                m3.metric("Запчасти", f"{total_parts:,.0f} ₽")
                                m4.metric("Продажи", f"{total_sell:,.0f} ₽")
                                m5.metric("Чистая прибыль", f"{total_profit:,.0f} ₽")

                                st.markdown("---")
                                st.markdown("### 📋 Детали продаж за период")

                                show = filtered[
                                    ["ID", "Дата выкупа", "Модель/IMEI/SN", "Характеристики",
                                     "Продавец", "Цена_Закупки", "Стоимость_запчастей",
                                     "Цена_Продажи", "Дата продажи", "Срок гарантии"]
                                ].copy()
                                show["Прибыль"] = filtered["_profit"].values
                                st.dataframe(show, use_container_width=True, hide_index=True)
