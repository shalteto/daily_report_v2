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
    user_options = (
        [f"{u['user_name']}（{u['user_code']}）" for u in users] if users else []
    )
    selected_idx = (
        st.selectbox(
            "編集・削除するユーザーを選択",
            range(len(user_options)),
            format_func=lambda i: user_options[i] if user_options else "",
            key="user_select",
            index=0 if users else None,
        )
        if users
        else None
    )

    if users and selected_idx is not None:
        user = users[selected_idx]
        with st.form(key="edit_form", clear_on_submit=False):
            user_name = st.text_input(
                "氏名", value=user["user_name"], key="edit_user_name"
            )
            user_code = st.text_input(
                "コード", value=user["user_code"], key="edit_user_code"
            )
            admin = st.checkbox(
                "管理者", value=user.get("admin", False), key="edit_admin"
            )
            # 画像差し替え用アップローダー追加
            permit_img = st.file_uploader(
                "許可証画像（差し替えたい場合のみ選択）",
                type=["jpg", "jpeg", "png"],
                key=f"edit_permit_img_{user['id']}",
                accept_multiple_files=False,
            )
            # 現在の画像名表示
            if user.get("permit_img_name"):
                st.caption(f"現在の画像: {user['permit_img_name']}")
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("更新")
            with col2:
                deleted = st.form_submit_button("削除")
            if submitted:
                with st.spinner("更新中...", show_time=True):
                    permit_img_name = user.get("permit_img_name")
                    # 画像がアップロードされた場合はOneDriveに上書き
                    if permit_img is not None:
                        extension = permit_img.name.split(".")[-1]
                        permit_img_name = f"従事者証_{user_name}.{extension}"
                        upload_onedrive(f"user_image/{permit_img_name}", permit_img)
                    updated = {
                        **user,
                        "category": "user",
                        "user_name": user_name,
                        "user_code": user_code,
                        "admin": admin,
                        "id": user["id"],
                        "permit_img_name": permit_img_name,
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
        user_code = st.text_input("コード", key="new_user_code")
        admin = st.checkbox("管理者", value=False, key="new_admin")
        permit_img = st.file_uploader(
            "許可証画像",
            type=["jpg", "jpeg", "png"],
            key="new_permit_img",
            accept_multiple_files=False,
        )
        submitted = st.form_submit_button("登録")
        if submitted:
            if user_name and user_code:
                with st.spinner("登録中...", show_time=True):
                    permit_img_name = None
                    if permit_img is not None:
                        extension = permit_img.name.split(".")[-1]
                        permit_img_name = f"従事者証_{user_name}.{extension}"
                        upload_onedrive(f"user_image/{permit_img_name}", permit_img)

                    new_user = {
                        "id": str(uuid.uuid4()),
                        "category": "user",
                        "user_name": user_name,
                        "user_code": user_code,
                        "admin": admin,
                        "permit_img_name": permit_img_name,
                    }
                    client.upsert_to_container(new_user)
                    st.session_state["users"].append(new_user)
                    st.success("ユーザーを登録しました。")
                    st.rerun()
            else:
                st.warning("氏名とコードは必須です。")
