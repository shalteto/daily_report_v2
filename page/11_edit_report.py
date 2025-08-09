import streamlit as st
from page_parts.upload_daily_report import edit_daily_report

from st_init import with_init


@with_init
def main():
    if st.session_state.user is None:
        st.warning("最初の画面でログインをしてください。")
        return
    edit_daily_report()


if __name__ == "__main__":
    main()
