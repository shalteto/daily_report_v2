import streamlit as st
from datetime import datetime
from azure_.one_drive import upload_onedrive
from page_parts.upload_daily_report import submit_data
import uuid
import hashlib
from zoneinfo import ZoneInfo

説明テキスト = """次の写真を撮影してアップロードしてください
1. 捕獲台帳の写真
1. 止め刺し直後の写真
1. 尻尾切除前（赤マーキング後）
1. 尻尾切除後
1. 歯列写真（ウリ坊は除外）
1. 処分方法に応じた写真
   - 焼却：トラックにイノシシを載せた写真
   - 自家消費：獲物にナイフを構えている写真
   - 埋設：穴に獲物を入れた状態を撮影
1. 埋設のみ：埋設後を撮影"""


def upsert_catch_result():
    st.subheader("捕獲実績登録")
    st.markdown(説明テキスト)

    with st.form(key="catch_result"):
        uploaded_file = st.file_uploader(
            "写真ファイルをアップロード",
            accept_multiple_files=True,
            type=["jpg", "png"],
        )
        submit_button = st.form_submit_button(label="送信")

        if submit_button:
            st.session_state.report_submitted = True

            if st.session_state.report_submitted:
                missing_fields = []
                if not uploaded_file:
                    missing_fields.append("写真を選択してください")
                if missing_fields:
                    for msg in missing_fields:
                        st.error(msg)
                    return

                with st.spinner("写真を送信中...", show_time=True):
                    print("Result: 送信処理開始")
                    now = datetime.now(ZoneInfo("Asia/Tokyo"))
                    now_form1 = now.strftime("%Y%m%d-%H%M%S")
                    now_form2 = now.strftime("%Y-%m-%d %H:%M:%S")
                    image_list = file_upload_daily(
                        uploaded_file, now_form1, "Apps_Images/catch_result"
                    )
                    data = {
                        "id": str(uuid.uuid4()),
                        "updata_date": now_form2,
                        "category": "result_files",
                    }
                    data.update(image_list)
                    submit_data(data)
                    st.session_state.report_submitted = False


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
        name = f"Result-{now_form1}-{idx}.{ext}"
        file_hash = get_file_hash(file)

        upload_onedrive(f"{directory}/{name}", file)
        images.append({"name": name, "hash": file_hash, "type": None})
    return {"images": images}


def submit_data(data):
    client = st.session_state["cosmos_client"]
    try:
        client.upsert_to_container(data)
    except Exception as e:
        st.error(f"CosmosDB登録エラー: {e}")
        return
    st.success("送信完了")
