import streamlit as st
from page_parts.input_order import input_order, edit_order

st.set_page_config(page_title="発注情報登録", layout="wide", page_icon="🐗")


def main():
    if st.session_state.user is not None and st.session_state.user["admin"] == True:
        input_order()
        st.markdown("---")
        edit_order()
        st.markdown("---")
    else:
        st.warning("管理者ログインが必要です。管理者に連絡してください。")


if __name__ == "__main__":
    main()
