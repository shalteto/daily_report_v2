# pip install streamlit
import streamlit as st
from st_init import init, with_init

st.set_page_config(page_title="SAT Report", layout="wide", page_icon="🐗")

st.logo("images/sat_logo.png", size="large")

pages = {
    "報告作成": [
        st.Page("page/00_login.py", title="ログイン"),
        st.Page("page/10_daily_report.py", title="作業日報"),
        st.Page("page/11_edit_report.py", title="作業日報編集"),
        st.Page("page/20_result_report.py", title="捕獲実績登録"),
        st.Page("page/21_edit_result.py", title="捕獲実績編集"),
    ],
    "進捗": [
        st.Page("page/50_result_review.py", title="捕獲集計"),
        st.Page("page/51_traps_status.py", title="わな稼働状況"),
    ],
    "管理": [
        st.Page("page/30_traps.py", title="わな管理"),
        st.Page("page/62_trup_research.py", title="わな設置調査"),
        # st.Page("page/64_trup_research_Mesh_Select.py", title="罠設置調査_Mesh Select"),
        # st.Page("page/80_user_input.py", title="ユーザー登録"),
        # st.Page("page/90_order_input.py", title="受注情報登録"),
    ],
}

pg = st.navigation(pages)
pg.run()
