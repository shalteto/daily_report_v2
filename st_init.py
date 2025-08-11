import streamlit as st
import pandas as pd
from functools import wraps

from page_parts.load_data import get_all_data
from azure_.cosmosdb import CosmosDBClient


def init():
    print("INIT実行")
    if "selected_objects" not in st.session_state:
        st.session_state.selected_objects = ""
    if "trap_page" not in st.session_state:
        st.session_state.trap_page = "None"
    if "location" not in st.session_state:
        st.session_state.location = ""

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

    if "report_submitted" not in st.session_state:
        st.session_state.report_submitted = False


# デコレーター化
def with_init(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        init()
        return func(*args, **kwargs)

    return wrapper
