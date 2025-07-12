import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from azure_.one_drive import upload_onedrive, download_onedrive_image


def user_main():
    client = st.session_state["cosmos_client"]
    st.subheader("ユーザー情報入力")
    users = st.session_state["users"]
    st.caption("ユーザー選択・編集")
    user_options = [f"{u['user_name']}" for u in users] if users else []
    selected_user_name = (
        st.segmented_control(
            "編集・削除するユーザーを選択",
            options=user_options,
            default=user_options[0] if user_options else None,
            key="user_select",
        )
        if users
        else None
    )

    if users and selected_user_name is not None:
        selected_idx = user_options.index(selected_user_name)
        user = users[selected_idx]

    if users and selected_idx is not None:
        user = users[selected_idx]
        with st.form(key="edit_form", clear_on_submit=False):
            user_name = st.text_input(
                "氏名", value=user["user_name"], key="edit_user_name"
            )
            admin = st.checkbox(
                "管理者", value=user.get("admin", False), key="edit_admin"
            )
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("更新")
            with col2:
                deleted = st.form_submit_button("削除")
            if submitted:
                with st.spinner("更新中...", show_time=True):
                    updated = {
                        **user,
                        "category": "user",
                        "user_name": user_name,
                        "admin": admin,
                        "id": user["id"],
                    }
                    client.upsert_to_container(updated)
                    st.session_state["users"][selected_idx] = updated
                    st.success("ユーザー情報を更新しました。")
                    st.rerun()
            if deleted:
                with st.spinner("削除中...", show_time=True):
                    print(user["id"])
                    client.delete_item_from_container(user["id"], "user")
                    st.session_state["users"].pop(selected_idx)
                    st.success("ユーザーを削除しました。")
                    st.rerun()
    else:
        st.info("ユーザーが登録されていません。")

    st.markdown("---")
    st.subheader("新規ユーザー登録")
    with st.form(key="add_form", clear_on_submit=True):
        user_name = st.text_input("氏名", key="new_user_name")
        admin = st.checkbox("管理者", value=False, key="new_admin")
        submitted = st.form_submit_button("登録")
        if submitted:
            if user_name:
                with st.spinner("登録中...", show_time=True):
                    new_user = {
                        "id": str(uuid.uuid4()),
                        "category": "user",
                        "user_name": user_name,
                        "admin": admin,
                    }
                    client.upsert_to_container(new_user)
                    st.session_state["users"].append(new_user)
                    st.success("ユーザーを登録しました。")
                    st.rerun()
            else:
                st.warning("氏名とコードは必須です。")
