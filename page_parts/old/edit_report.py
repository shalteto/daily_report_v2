import streamlit as st
import pandas as pd
from page_parts.upload_daily_report import submit_data


def get_daily_report(task_type, task_date):
    client = st.session_state["cosmos_client"]
    task_date = task_date.strftime("%Y-%m-%d")
    query = "SELECT c.users, c.task_type, c.task_date, c.start_time, c.end_time, c.trap, c.trap_type, c.sex, c.size, c.weight, c.disposal, c.images, c.comment, c.id FROM c WHERE c.task_type = @task_type and c.task_date = @task_date"
    parameters = [
        {"name": "@task_type", "value": task_type},
        {"name": "@task_date", "value": task_date},
    ]
    res = client.search_container_by_query(
        query,
        parameters,
    )
    return res


def edit_report():
    st.subheader("報告内容の修正")
    st.caption("作業種類と作業日を選択してください")
    with st.form(key="edit_form"):
        task_type = st.selectbox(
            "作業種類を選択",
            [
                "わな猟見回り",
                "わな猟調査",
                "わな猟設置",
                "わな猟撤去",
                "わな猟移設",
                "銃猟調査",
                "銃猟誘引狙撃",
                "銃猟巻き狩り",
                "銃猟忍び猟",
                "その他",
            ],
        )
        task_date = st.date_input("作業日を選択")
        submit_button = st.form_submit_button(label="報告内容表示")

    if submit_button:
        res = get_daily_report(task_type, task_date)
        if res:
            daily_report_result_df = pd.DataFrame(res)
            daily_report_result_df.insert(0, "編集対象", False)
            st.session_state.daily_report_result_df = daily_report_result_df
    if not st.session_state.daily_report_result_df.empty:
        edited_daily_report_result_df = st.data_editor(
            st.session_state.daily_report_result_df
        )
        selected_records = edited_daily_report_result_df[
            edited_daily_report_result_df["編集対象"] == True
        ]
        if len(selected_records) > 1:
            st.error("編集対象は1つのレコードのみ選択してください。")
        elif len(selected_records) == 1:
            record = selected_records.iloc[0]
            print("record==>")
            print(record)
            with st.form(key="update_form"):
                users = st.multiselect(
                    "ユーザーを選択",
                    st.session_state.users,
                    default=record["users"],
                )
                task_date = st.date_input(
                    "作業日を選択", value=pd.to_datetime(record["task_date"])
                )
                start_time = st.time_input(
                    "開始時間", value=pd.to_datetime(record["start_time"]).time()
                )
                end_time = st.time_input(
                    "終了時間", value=pd.to_datetime(record["end_time"]).time()
                )
                trap = st.text_input("罠", value=record["trap"])
                trap_type = st.text_input("罠種類", value=record["trap_type"])
                sex = st.selectbox(
                    "雌雄",
                    ["オス", "メス", "-"],
                    index=["オス", "メス", "-"].index(record["sex"]),
                )
                size = st.slider("頭胴長サイズ（cm）", 0, 150, int(record["size"]))
                weight = st.slider("推定体重（kg）", 0, 150, int(record["weight"]))
                disposal = st.selectbox(
                    "処分方法",
                    ["焼却", "自家消費", "埋設", "食肉加工", "-"],
                    index=["焼却", "自家消費", "埋設", "食肉加工", "-"].index(
                        record["disposal"]
                    ),
                )
                comment = st.text_input("コメント", value=record["comment"])
                update_button = st.form_submit_button(label="更新")

            if update_button:
                updated_data = {
                    "users": users,
                    "task_type": task_type,
                    "task_date": task_date.strftime("%Y-%m-%d"),
                    "start_time": start_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M"),
                    "trap": trap,
                    "trap_type": trap_type,
                    "sex": sex,
                    "size": size,
                    "weight": weight,
                    "disposal": disposal,
                    "images": record["images"],
                    "comment": comment,
                    "id": record["id"],
                }
                submit_data(updated_data)
        else:
            st.text("編集対象のレコードを選択してください。")
    else:
        st.text("該当する報告が見つかりませんでした。")
