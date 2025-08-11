# pip install streamlit
import streamlit as st

st.set_page_config(page_title="SAT App", layout="wide", page_icon="🐗")

st.logo("images/sat_logo.png", size="large")

pages = {
    "報告作成": [
        st.Page("page/10_daily_report.py", title="1. 作業日報"),
        st.Page("page/40_get_result_ids.py", title="2. 捕獲番号発行"),
        st.Page("page/20_result_report.py", title="3. 捕獲実績登録"),
    ],
    "進捗": [
        st.Page("page/50_result_review.py", title="捕獲集計"),
        st.Page("page/51_traps_status.py", title="わな稼働状況"),
    ],
}

pg = st.navigation(pages)
pg.run()
