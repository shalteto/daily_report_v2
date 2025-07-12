import streamlit as st
from page_parts.result_graph import show_graph, show_map

st.set_page_config(page_title="捕獲統計", layout="wide", page_icon="🐗")


def main():
    if st.session_state.user is not None:
        show_map()
        show_graph()
    else:
        st.warning("最初の画面でログインをしてください。")


if __name__ == "__main__":
    main()
