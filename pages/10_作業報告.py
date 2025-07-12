import streamlit as st
from page_parts.upload_daily_report import upsert_daily_report
from page_parts.trap_map import call_trap_date

st.set_page_config(page_title="作業報告", layout="wide", page_icon="🐗")


def main():
    if st.session_state.user is not None:
        if st.session_state.trap_data == "":
            st.session_state.trap_data = call_trap_date()
        upsert_daily_report()
    else:
        st.warning("最初の画面でログインをしてください。")


if __name__ == "__main__":
    main()
