import streamlit as st
from page_parts.result_graph import show_graph, show_map

st.set_page_config(page_title="捕獲統計", layout="wide", page_icon="🐗")

from st_init import with_init


@with_init
def main():
    if st.session_state.user is None:
        st.warning("最初の画面でログインをしてください。")
        return

    show_graph()
    st.markdown("---")
    show_map()



if __name__ == "__main__":
    main()
