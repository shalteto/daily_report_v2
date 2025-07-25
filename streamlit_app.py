# pip install streamlit
import streamlit as st
from st_init import init

st.set_page_config(page_title="SAT Report", layout="wide", page_icon="🐗")


def main():
    st.text("合同会社ＳＡＴ")
    st.subheader("作業報告アプリ🐗🦌🦋")
    st.write('左上の"＞"でメニューを表示')
    st.write("---")


def user_select():
    users_df = st.session_state.users
    user_options = [f"{u['user_name']}" for u in users_df] if users_df else []

    # 既にユーザーが選択されている場合
    if "user" in st.session_state and st.session_state.user:
        user_info = st.session_state.user
        user_name = user_info.get("user_name", str(user_info))
        st.success(f"ログインユーザー：{user_name}")
        if st.button("ユーザー変更"):
            st.session_state.user = None
            st.session_state.show_selectbox = True
            st.session_state.params_user = None
            st.rerun()
        else:
            with st.expander("DB Data", expanded=False):
                st.write("st.session_state.users:")
                st.session_state.users
                "---"
                st.write("st.session_state.traps:")
                st.session_state.traps
                "---"
                st.write("st.session_state.daily_reports:")
                st.session_state.daily_reports
                "---"
                st.write("st.session_state.catch_results:")
                st.session_state.catch_results
                "---"
                st.write("st.session_state.orders:")
                st.session_state.orders

    # プルダウン選択表示
    else:
        with st.form("selectbox_form"):
            selected_user_name = st.segmented_control(
                "ユーザーを選択", user_options, key="selectbox_user"
            )
            selectbox_submitted = st.form_submit_button("ログイン")
        if selectbox_submitted:
            # レコード取得
            user_record = next(
                u for u in users_df if u["user_name"] == selected_user_name
            )
            st.session_state.user = user_record
            st.success(f"ログインユーザー：{selected_user_name}")
            return


if __name__ == "__main__":
    init()
    main()
    user_select()
