import streamlit as st
from datetime import datetime, timedelta
from azure_.one_drive import upload_onedrive, download_onedrive_image
import uuid


users_df = st.session_state.users
user_options = list({u["user_name"] for u in users_df})


def file_upload_daily(uploaded_file, task_type):
    images = []
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    extension = uploaded_file.name.split(".")[-1]
    blob_name = f"{now}_{st.session_state.task_type_option[task_type]}_1.{extension}"
    print(f"blob_name: {blob_name}")
    images.append({"name": blob_name})
    uploaded_file.seek(0)
    upload_onedrive(
        f"Apps_Images/daily_report/{blob_name}",
        uploaded_file,
    )
    return images


def submit_data(data):
    client = st.session_state["cosmos_client"]
    try:
        client.upsert_to_container(data)
    except Exception as e:
        st.error(f"CosmosDB登録エラー: {e}")
        return
    st.success("送信完了")


def upsert_daily_report():
    st.subheader("作業日報")
    with st.form(key="daily_report"):
        # st.write(st.session_state.user)
        users = st.segmented_control(
            "従事者選択",
            user_options,
            key="user_select",
            selection_mode="multi",
            default=st.session_state.user["user_name"],
        )
        task_type = st.segmented_control(
            "作業内容選択(複数作業の場合は1つ選択して備考に他作業を記載)",
            list(st.session_state.task_type_option.keys()),
            selection_mode="single",
        )
        date = st.date_input("作業日を選択", datetime.today())
        now = datetime.now() + timedelta(hours=9)
        hour = st.number_input(
            "作業時間を入力(1時間単位で切上げ)", min_value=1, max_value=10, value=1
        )
        start_time = now - timedelta(hours=int(hour))
        end_time = now
        uploaded_files = st.file_uploader(
            "従事者の写真をアップロード",
            accept_multiple_files=False,
            type=["jpg", "jpeg", "png"],
        )
        comment = st.text_input("(任意) コメントを入力")
        submit_button = st.form_submit_button(label="送信")

    if submit_button:
        with st.spinner("送信中...", show_time=True):
            print("処理開始")
            if uploaded_files and users and task_type:
                task_date = date.strftime("%Y-%m-%d")
                images = file_upload_daily(uploaded_files, task_type)

                # 画像のアップロード
                data = {
                    "id": str(uuid.uuid4()),
                    "category": "daily",
                    "fy": st.session_state.fy,
                    "users": users,
                    "task_type": task_type,
                    "task_date": task_date,
                    "start_time": start_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M"),
                    "images": images,
                    "comment": comment,
                }
                submit_data(data)
                submit_button = False  # フォーム送信後は再送信防止
                st.session_state["daily_reports"].append(data)
            else:
                if not users:
                    st.error("従事者を選択してください。")
                if not uploaded_files:
                    st.error("写真をアップロードしてください。")
                if not task_type:
                    st.error("作業内容を選択してください。")


def edit_daily_report():
    client = st.session_state["cosmos_client"]
    # users, task_type, date で絞り込みが可能。
    data = st.session_state["daily_reports"]

    st.subheader("作業報告編集")
    with st.form(key="edit_daily_report_filter"):
        filter_users = st.segmented_control(
            "従事者で絞り込み", user_options, selection_mode="multi"
        )
        filter_task_type = st.segmented_control(
            "作業内容で絞り込み",
            list(st.session_state.task_type_option.keys()),
            selection_mode="single",
        )
        filter_date_from = st.date_input(
            "作業日(開始)", value=None, key="filter_date_from"
        )
        filter_date_to = st.date_input("作業日(終了)", value=None, key="filter_date_to")
        filter_button = st.form_submit_button("レポート絞り込み")

    filtered = data
    # usersで絞り込み
    if filter_users:
        filtered = [
            d for d in filtered if any(u in d.get("users", []) for u in filter_users)
        ]
    # task_typeで絞り込み
    if filter_task_type:
        filtered = [d for d in filtered if d.get("task_type") == filter_task_type]
    # dateで絞り込み
    if filter_date_from:
        filtered = [
            d
            for d in filtered
            if "task_date" in d
            and d["task_date"] >= filter_date_from.strftime("%Y-%m-%d")
        ]
    if filter_date_to:
        filtered = [
            d
            for d in filtered
            if "task_date" in d
            and d["task_date"] <= filter_date_to.strftime("%Y-%m-%d")
        ]

    st.write(f"該当件数: {len(filtered)}")
    for idx, d in enumerate(filtered):
        with st.expander(
            f"{d.get('task_date', '')} | {', '.join(d.get('users', []))} | {d.get('task_type', '')}"
        ):
            st.write(f"作業日: {d.get('task_date', '')}")
            st.write(f"従事者: {', '.join(d.get('users', []))}")
            st.write(f"作業内容: {d.get('task_type', '')}")
            st.write(f"作業時間: {d.get('start_time', '')} - {d.get('end_time', '')}")
            st.write(f"コメント: {d.get('comment', '')}")

            col1, col2 = st.columns([2, 1])
            with col1:
                edit_key = f"edit_{d['id']}"
                if st.button("編集", key=edit_key):
                    st.session_state["editing_id"] = d["id"]
                if st.session_state.get("editing_id") == d["id"]:
                    with st.form(key=f"edit_form_{d['id']}"):
                        edit_users = st.segmented_control(
                            "従事者",
                            user_options,
                            default=d.get("users", []),
                            key=f"edit_users_{d['id']}",
                            selection_mode="multi",
                        )
                        edit_task_type = st.segmented_control(
                            "作業内容",
                            list(st.session_state.task_type_option.keys()),
                            default=d.get("task_type", ""),
                            key=f"edit_task_type_{d['id']}",
                            selection_mode="single",
                        )
                        edit_date = st.date_input(
                            "作業日",
                            value=datetime.strptime(d.get("task_date", ""), "%Y-%m-%d"),
                            key=f"edit_date_{d['id']}",
                        )
                        edit_start_time = st.text_input(
                            "開始時刻(HH:MM)",
                            value=d.get("start_time", ""),
                            key=f"edit_start_{d['id']}",
                        )
                        edit_end_time = st.text_input(
                            "終了時刻(HH:MM)",
                            value=d.get("end_time", ""),
                            key=f"edit_end_{d['id']}",
                        )
                        edit_comment = st.text_input(
                            "コメント",
                            value=d.get("comment", ""),
                            key=f"edit_comment_{d['id']}",
                        )
                        # ここにd.get("images", [])から得た複数の画像名称から、OneDriveからファイルをダウンロードして表示を追加
                        images = d.get("images", [])
                        if images:
                            st.text("アップロード済み画像:")
                            for img_idx, img in enumerate(images):
                                file_path = f"Apps_Images/daily_report/{img['name']}"
                                image_data, error = download_onedrive_image(file_path)
                                if error:
                                    st.warning(f"{img['name']} の取得失敗: {error}")
                                else:
                                    st.image(
                                        image_data,
                                        caption=img["name"],
                                        use_container_width=True,
                                    )
                                # 差し替え機能追加
                                replace_file = st.file_uploader(
                                    f"{img['name']} を差し替える",
                                    type=["jpg", "jpeg", "png"],
                                    key=f"replace_{d['id']}_{img_idx}",
                                    accept_multiple_files=False,
                                )
                        # 追加: 写真追加用アップローダー
                        add_files = st.file_uploader(
                            "写真を追加アップロード",
                            type=["jpg", "jpeg", "png"],
                            key=f"add_files_{d['id']}",
                            accept_multiple_files=True,
                        )
                        submit_edit = st.form_submit_button("保存")
                        if submit_edit:
                            with st.spinner("送信中...", show_time=True):
                                # 画像差し替え
                                if images:
                                    for img_idx, img in enumerate(images):
                                        replace_file = st.session_state.get(
                                            f"replace_{d['id']}_{img_idx}"
                                        )
                                        if replace_file:
                                            extension = replace_file.name.split(".")[-1]
                                            now = datetime.now().strftime(
                                                "%Y%m%d%H%M%S"
                                            )
                                            new_blob_name = f"{now}_{st.session_state.task_type_option[d['task_type']]}_{img_idx+1}.{extension}"
                                            replace_file.seek(0)
                                            upload_onedrive(
                                                f"Apps_Images/daily_report/{new_blob_name}",
                                                replace_file,
                                            )
                                            d["images"][img_idx]["name"] = new_blob_name
                                            st.success(
                                                f"{img['name']} を {new_blob_name} に差し替えました。"
                                            )
                                # 追加: 写真追加処理
                                if add_files:
                                    now = datetime.now().strftime("%Y%m%d%H%M%S")
                                    start_idx = len(d["images"]) + 1
                                    for i, add_file in enumerate(
                                        add_files, start=start_idx
                                    ):
                                        extension = add_file.name.split(".")[-1]
                                        blob_name = f"{now}_{st.session_state.task_type_option[d['task_type']]}_{i}.{extension}"
                                        add_file.seek(0)
                                        upload_onedrive(
                                            f"Apps_Images/daily_report/{blob_name}",
                                            add_file,
                                        )
                                        d["images"].append({"name": blob_name})
                                    st.success("写真を追加しました。")
                                # データを更新
                                d["users"] = edit_users
                                d["task_type"] = edit_task_type
                                d["task_date"] = edit_date.strftime("%Y-%m-%d")
                                d["start_time"] = edit_start_time
                                d["end_time"] = edit_end_time
                                d["comment"] = edit_comment
                                d["id"] = d["id"]
                                d["fy"] = d["fy"]
                                d["category"] = "daily"
                                d["images"] = d["images"]
                                submit_data(d)
                                # st.session_state["daily_reports"] からidで検索して更新
                                for i, report in enumerate(
                                    st.session_state["daily_reports"]
                                ):
                                    if report["id"] == d["id"]:
                                        st.session_state["daily_reports"][i] = d
                                        break
                                st.success("編集内容を保存しました")
                                st.session_state["editing_id"] = None
                                st.rerun()
                    if st.button("キャンセル", key=f"edit_cancel_{d['id']}"):
                        st.session_state["editing_id"] = None
                        st.rerun()
            with col2:
                # 削除確認用のキー
                confirm_key = f"confirm_delete_{d['id']}"
                if st.button("削除", key=f"delete_{d['id']}"):
                    st.session_state[confirm_key] = True
                if st.session_state.get(confirm_key, False):
                    st.warning(f"本当に削除しますか？")
                    if st.button("はい", key=f"confirm_yes_{d['id']}"):
                        with st.spinner("送信中...", show_time=True):
                            # データを削除
                            client.delete_item_from_container(d["id"], "daily")
                            st.session_state["daily_reports"].remove(d)
                            st.success("削除しました")
                            st.session_state[confirm_key] = False
                            st.rerun()
                    if st.button("キャンセル", key=f"confirm_cancel_{d['id']}"):
                        st.session_state[confirm_key] = False
