import streamlit as st
from page_parts.upload_result_report import upsert_catch_result

# from page_parts.trap_map import call_trap_date

# st.set_page_config(page_title="作業報告", layout="wide", page_icon="🐗")

from st_init import with_init


@with_init
def main():
    if st.session_state.user is None:
        st.warning("最初の画面でログインをしてください。")
        return
    upsert_catch_result()


if __name__ == "__main__":
    main()
