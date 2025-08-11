import streamlit as st
from datetime import datetime
from azure_.one_drive import upload_onedrive
from page_parts.upload_daily_report import submit_data
import uuid
from zoneinfo import ZoneInfo

# --- 新しいID発行・仮登録関数 ---
from page_parts.load_data import get_all_data


def get_result_ids(num=1, user_name=None):
    # 最新データ取得
    data = get_all_data()
    st.session_state.catch_results = data["catch_results"]

    # 既存IDの数値部分だけを抽出
    used_ids = set()
    for d in st.session_state.catch_results:
        rid = d.get("result_id", "")
        if isinstance(rid, str) and rid.startswith("ﾀ-"):
            try:
                used_ids.add(int(rid.split("-", 1)[1]))
            except ValueError:
                pass
        else:
            # 旧フォーマットにも対応
            try:
                used_ids.add(int(rid))
            except Exception:
                pass

    # 連番で未使用IDをnum個探す
    next_ids = []
    i = 1
    while len(next_ids) < num:
        if i not in used_ids:
            next_ids.append(i)
        i += 1
    # 仮登録レコードをDBに保存
    client = st.session_state["cosmos_client"]
    fy = st.session_state.get("fy", "2025年度")
    reserved = []
    for rid_num in next_ids:
        rid_str = f"ﾀ-{rid_num}"
        rec = {
            "id": str(uuid.uuid4()),
            "category": "result",
            "fy": fy,
            "result_id": rid_str,
            "status": "reserved",
            "reserved_by": user_name,
            "reserved_at": datetime.now(ZoneInfo("Asia/Tokyo")).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        client.upsert_to_container(rec)
        reserved.append(rec)

    # session_stateも更新
    st.session_state.catch_results += reserved

    # A-付きで返却
    return [f"ﾀ-{rid_num}" for rid_num in next_ids]


def result_id_display():
    data_all = get_all_data()
    st.session_state.catch_results = data_all["catch_results"]

    all_records = [
        {
            "捕獲番号": d["result_id"],
            "発行者": d.get("reserved_by", ""),
            "発行日時": d.get("reserved_at", ""),
        }
        for d in st.session_state.catch_results
        if "result_id" in d and d["result_id"]
    ]

    # 数字部分でソート
    all_records = sorted(
        all_records,
        key=lambda x: (
            int(x["捕獲番号"].split("-", 1)[1])
            if isinstance(x["捕獲番号"], str) and "-" in x["捕獲番号"]
            else 0
        ),
        reverse=True,  # 降順
    )

    # Markdownテーブル文字列作成
    if all_records:
        table_md = "| 捕獲番号 | 発行者 | 発行日時 |\n"
        table_md += "|---|---|---|\n"
        for rec in all_records:
            table_md += f"| {rec['捕獲番号']} | {rec['発行者']} | {rec['発行日時']} |\n"

        st.subheader("発行済 捕獲番号")
        st.markdown(table_md)
    else:
        st.info("発行済みIDはありません")
    st.markdown("---")

    st.subheader("捕獲番号の発行")
    users_df = st.session_state.users
    user_options = [f"{u['user_name']}" for u in users_df] if users_df else []
    selected_user_name = st.segmented_control(
        "ユーザーを選択",
        user_options,
        key="selectbox_user",
        selection_mode="single",
        # on_change=st.rerun(),
    )
    if not selected_user_name:
        st.info("ユーザーを選択してください。")
        return

    # --- ID追加発行ボタン ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("捕獲番号追加")
        num_ids = 1
        if st.button("捕獲番号追加"):
            user_record = next(
                u for u in users_df if u["user_name"] == selected_user_name
            )
            st.session_state.user = user_record
            get_result_ids(num=num_ids, user_name=st.session_state.user["user_name"])
            data_all = get_all_data()
            st.session_state.catch_results = data_all["catch_results"]
            all_records = [
                d["result_id"]
                for d in st.session_state.catch_results
                if "result_id" in d and d["result_id"]  # Noneや空文字を除外
            ]
            all_records = sorted(
                all_records,
                key=lambda x: (
                    int(x.split("-", 1)[1]) if isinstance(x, str) and "-" in x else 0
                ),
            )
            st.rerun()
