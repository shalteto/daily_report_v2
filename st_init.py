import streamlit as st
import pandas as pd

# from page_parts.input_users import load_users
from page_parts.load_data import get_all_data
from azure_.cosmosdb import CosmosDBClient


def init():
    print("INIT実行")
    if "selected_objects" not in st.session_state:
        st.session_state.selected_objects = ""
    # if "users_filtered_by_type" not in st.session_state:
    #     st.session_state.users_filtered_by_type = ""
    # if "user_input_type" not in st.session_state:
    #     st.session_state.user_input_type = "None"
    if "trap_page" not in st.session_state:
        st.session_state.trap_page = "None"
    if "trap_data" not in st.session_state:
        st.session_state.trap_data = ""
    # if "daily_report_result_df" not in st.session_state:
    #     st.session_state.daily_report_result_df = pd.DataFrame()
    if "location" not in st.session_state:
        st.session_state.location = ""

    # 作り変え以降
    if "user" not in st.session_state:
        st.session_state.user = None
    if "cosmos_client" not in st.session_state:
        st.session_state["cosmos_client"] = CosmosDBClient()

    if "users" not in st.session_state:
        st.session_state.users = ""
    if "traps" not in st.session_state:
        st.session_state.traps = ""
    if "daily_reports" not in st.session_state:
        st.session_state.daily_reports = ""
    if "catch_results" not in st.session_state:
        st.session_state.catch_results = ""

    if st.session_state["users"] == "":
        data = get_all_data()
        st.session_state.fy = "2025年度"
        st.session_state.users = data["users"]
        st.session_state.traps = data["traps"]
        st.session_state.daily_reports = data["daily_reports"]
        st.session_state.catch_results = data["catch_results"]
        st.session_state.orders = data["orders"]
    if "task_type_option" not in st.session_state:
        st.session_state.task_type_option = {
            "わな猟見回り": "trap_research",
            "わな猟調査": "trap_setting",
            "わな猟設置": "trap_remove",
            "わな猟撤去": "trap_resetting",
            "わな猟移設": "trap_check",
            "銃猟調査": "gun_research",
            "銃猟誘引狙撃": "gun_calling",
            "銃猟巻き狩り": "gun_driven_hunting",
            "銃猟忍び猟": "gun_sneak_hunting",
            "その他": "other",
        }
    if "catch_method_option" not in st.session_state:
        st.session_state.catch_method_option = {
            "くくり罠": "kukuri",
            "箱罠": "box",
            "巻き狩り": "driven",
            "忍び猟": "sneak",
            "誘引狙撃": "call",
        }
    # アプリにアクセスしたときに、クエリに"user"が含まれている場合、セッションステートに保存する
    if "params_user" not in st.session_state:
        if "user_code" in st.query_params:
            st.session_state.params_user = True
            st.session_state.user = next(
                (
                    u
                    for u in st.session_state.users
                    if u["user_code"] == st.query_params["user_code"]
                ),
                None,
            )
        else:
            st.session_state.params_user = None
