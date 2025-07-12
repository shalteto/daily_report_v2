import streamlit as st
from page_parts.input_users import user_main

st.set_page_config(page_title="ユーザー登録", layout="wide", page_icon="🐗")


def main():
    if st.session_state.user is not None and st.session_state.user["admin"] == True:
        user_main()
    else:
        st.warning("管理者ログインが必要です。管理者に連絡してください。")


if __name__ == "__main__":
    main()
