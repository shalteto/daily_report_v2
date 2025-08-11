import streamlit as st
from datetime import datetime
from azure_.one_drive import upload_onedrive
import uuid
import hashlib
from zoneinfo import ZoneInfo


def get_file_hash(file, algo="sha256"):
    """アップロードファイルのハッシュ値を返す"""
    hash_func = hashlib.new(algo)
    file.seek(0)
    for chunk in iter(lambda: file.read(8192), b""):
        hash_func.update(chunk)
    file.seek(0)
    return hash_func.hexdigest()


def file_upload_daily(uploaded_files, now_form1, directory):
    images = []
    for idx, file in enumerate(uploaded_files):
        ext = file.name.split(".")[-1]
        name = f"Dialy-{now_form1}-{idx}.{ext}"
        file_hash = get_file_hash(file)

        upload_onedrive(f"{directory}/{name}", file)
        images.append({"name": name, "hash": file_hash})
    return {"images": images}


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
        uploaded_files = st.file_uploader(
            "写真をアップロード",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"],
        )
        submit_button = st.form_submit_button(label="送信")

    if submit_button:
        st.session_state.report_submitted = True
        if st.session_state.report_submitted:
            missing_fields = []
            if not uploaded_files:
                missing_fields.append("写真を選択してください")
            if missing_fields:
                for msg in missing_fields:
                    st.error(msg)
                return

        with st.spinner("写真を送信中...", show_time=True):
            print("Dialy: 送信処理開始")
            if uploaded_files:
                now = datetime.now(ZoneInfo("Asia/Tokyo"))
                now_form1 = now.strftime("%Y%m%d-%H%M%S")
                now_form2 = now.strftime("%Y-%m-%d %H:%M:%S")
                image_list = file_upload_daily(
                    uploaded_files, now_form1, "Apps_Images/daily_report"
                )
                data = {
                    "id": str(uuid.uuid4()),
                    "updata_date": now_form2,
                    "category": "daily_file",
                }
                data.update(image_list)
                submit_data(data)
                st.session_state.report_submitted = False
