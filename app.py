@@ -11,50 +11,45 @@
# ТВОЙ АПИ-ШЛЮЗ НАСТОЯЩИЙ
API_URL = "https://script.google.com/macros/s/AKfycbypt3LA1wLZZ-iitNH3x-3ElZrcMVuYm-7od43EQviYsuQcVGB6UV3YVu15tK1OOFnJ/exec"

# Жесткие и чистые заголовки по паспорту проекта для устранения дубляжа
SKUPKA_HEADERS = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]

# Инициализируем локальное хранилище в памяти приложения
if "df_skupka_local" not in st.session_state:
    st.session_state["df_skupka_local"] = None
if "need_reload" not in st.session_state:
    st.session_state["need_reload"] = True

# Функция правильного и безопасного скачивания данных из Google
# Функция БРОНЕБОЙНОГО сбора чистой таблицы вручную по строкам
def load_data_from_google():
    headers = ["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки", "Продавец", "Статус", "Цена_Продажи"]
    try:
        nocache_url = f"{API_URL}?sheet=Скупка&t={time.time()}"
        response = requests.get(nocache_url, timeout=5)
        data = response.json()

        parsed_rows = []
        if isinstance(data, list) and len(data) > 0:
            # Проверяем, прислал ли Гугл строку заголовков. 
            # Если в первом элементе первой строки написано "ID" или "id", значит это шапка таблицы
            first_row = data[0]
            if isinstance(first_row, list) and len(first_row) > 0 and str(first_row[0]).strip().lower() in ["id", "ид"]:
                raw_rows = data[1:] # Отсекаем гугловские заголовки, чтобы они не дублировались серой строкой
            else:
                raw_rows = data
            for row in data:
                # Если строчка пустая или это заголовок таблицы из Google, пропускаем её
                if not row or not isinstance(row, list):
                    continue
                first_cell = str(row[0]).strip().lower()
                if first_cell in ["id", "ид", "идентификатор", ""]:
                    continue

            # Собираем DataFrame строго с нашими чистыми заголовками
            df = pd.DataFrame(raw_rows)
            
            # Если колонок в таблице меньше или больше, подгоняем под наш стандарт
            while len(df.columns) < len(SKUPKA_HEADERS):
                df[len(df.columns)] = ""
            df = df.iloc[:, :len(SKUPKA_HEADERS)]
            df.columns = SKUPKA_HEADERS
            
            # Очищаем все текстовые поля от лишних скрытых пробелов
            for col in df.columns:
                df[col] = df[col].astype(str).str.strip()
            return df
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
    # Если база совсем пустая, возвращаем пустую таблицу с правильной структурой
    return pd.DataFrame(columns=SKUPKA_HEADERS)
    return pd.DataFrame(columns=headers)

# Кнопка синхронизации
# Кнопка ручной синхронизации
if st.button("🔄 Синхронизировать с Google Таблицей"):
    st.session_state["df_skupka_local"] = load_data_from_google()
    st.session_state["need_reload"] = False
@@ -90,7 +85,7 @@ def load_data_from_google():
                    "sheet": "Ремонт",
                    "row": [new_id, current_time, client, phone, device, issue, "В работе"]
                }
                with st.spinner("Сохраняем ремонт в Google Таблицу..."):
                with st.spinner("Сохраняем ремонт in Google..."):
                    try:
                        requests.post(API_URL, json=payload, timeout=3)
                        st.success(f"Заказ №{new_id} успешно сохранен!")
@@ -121,7 +116,7 @@ def load_data_from_google():
                    "row": [new_id, current_time, model, specs, price_buy, seller, "Подготовка к продаже", ""]
                }

                # Мгновенно добавляем в локальную таблицу с правильной структурой столбцов
                # Мгновенно добавляем в локальную таблицу с чистой структурой
                new_row = [str(new_id), current_time, model, specs, str(price_buy), seller, "Подготовка к продаже", ""]
                df_main.loc[len(df_main)] = new_row
                st.session_state["df_skupka_local"] = df_main
@@ -145,7 +140,7 @@ def load_data_from_google():
            st.info("Сейчас нет техники на подготовке к продаже.")
        else:
            st.markdown("### 📋 Список устройств в работе:")
            # Выводим только важные колонки для витрины подготовки
            # Идеально чистая витрина без индексов
            st.dataframe(in_prep[["ID", "Дата", "Модель", "Характеристики", "Цена_Закупки"]], use_container_width=True, hide_index=True)

            st.markdown("---")
@@ -168,7 +163,7 @@ def load_data_from_google():
                    if price_sell_ready > 0:
                        clean_id = int(float(selected_prep_id)) if selected_prep_id.replace('.','',1).isdigit() else selected_prep_id

                        # Мгновенно меняем статус и цену продажи локально в памяти программы
                        # Мгновенно обновляем локально статус и цену продажи
                        df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Статус"] = "На складе"
                        df_main.loc[df_main["ID"] == str(selected_prep_id).strip(), "Цена_Продажи"] = str(price_sell_ready)
                        st.session_state["df_skupka_local"] = df_main
@@ -185,7 +180,7 @@ def load_data_from_google():
                                requests.post(API_URL, json=payload, timeout=3)
                            except:
                                pass
                            st.success("Устройство мгновенно перемещено на витрину продаж!")
                            st.success("Устройство перемещено на витрину продаж!")
                            st.rerun()
                    else:
                        st.error("Укажите цену продажи!")
@@ -205,7 +200,6 @@ def load_data_from_google():
            st.info("На складе пусто.")
        else:
            st.markdown("### 🏪 Товары на витрине:")
            # ЧИСТАЯ КРАСИВАЯ ВИТРИНА: показываем только то, что нужно продавцу, без серых строк
            st.dataframe(in_stock[["ID", "Дата", "Модель", "Характеристики", "Цена_Продажи"]], use_container_width=True, hide_index=True)

            st.markdown("---")
@@ -215,3 +209,12 @@ def load_data_from_google():
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
