import streamlit as st
from page_parts.upload_daily_report import edit_daily_report


def main():
    if st.session_state.user is not None:
        edit_daily_report()
    else:
        st.warning("最初の画面でログインをしてください。")


if __name__ == "__main__":
    main()
