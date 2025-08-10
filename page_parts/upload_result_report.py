import streamlit as st
from page_parts.trap_map import trap_map
from datetime import datetime, timedelta
from azure_.one_drive import upload_onedrive, download_onedrive_image
from page_parts.upload_daily_report import submit_data
from services.gps import get_gps_coordinates
import uuid
import time

users_df = st.session_state.users
user_options = list({u["user_name"] for u in users_df})


# --- 新しいID発行・仮登録関数 ---
from page_parts.load_data import get_all_data


def get_result_ids(num=1, user_name=None):
    """
    DBから最新のcatch_resultsを取得し、未使用の連番IDをnum個発行・仮登録する。
    仮登録レコードは status="reserved" で保存。
    user_name: 発行ユーザー識別用
    戻り値: 発行したIDリスト（例: ["ﾀ-1", "ﾀ-2"]）
    """
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
            "reserved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        client.upsert_to_container(rec)
        reserved.append(rec)

    # session_stateも更新
    st.session_state.catch_results += reserved

    # A-付きで返却
    return [f"ﾀ-{rid_num}" for rid_num in next_ids]


def upsert_catch_result():
    st.subheader("捕獲実績登録")
    catch_method = st.segmented_control(
        "捕獲方法を選択",
        list(st.session_state.catch_method_option.keys()),
        selection_mode="single",
    )
    if catch_method in ["くくり罠", "箱罠", "囲い罠"]:
        trap_map(mode="稼働中", multi_select="single-object")
    if st.session_state.selected_objects:
        for p in st.session_state.selected_objects["map"]:
            st.write(
                f"{p["trap_name"]} / {round(p["latitude"],5)}, {round(p["longitude"],5)}"
            )
    if not catch_method:
        st.warning("捕獲方法を選択してください")

    # --- 予約済みIDの取得 ---
    user_name = st.session_state.user["user_name"] if st.session_state.user else None
    data_all = get_all_data()
    st.session_state.catch_results = data_all["catch_results"]
    reserved_ids = [
        d["result_id"]
        for d in st.session_state.catch_results
        if d.get("status") == "reserved" and d.get("reserved_by") == user_name
    ]
    # result_idが「ﾀ-数字」形式なので、数字部分でソート
    reserved_ids = sorted(
        reserved_ids,
        key=lambda x: int(x.split("-", 1)[1]) if isinstance(x, str) and "-" in x else 0,
    )

    if reserved_ids:
        result_id = reserved_ids[0]
    else:
        result_id = ""

    if reserved_ids:
        id_html = " ".join(
            [
                f"<span style='font-size: 32px; font-weight: bold; color: #d62728; background-color: #f9f9f9; padding: 8px 20px; border: 2px solid #d62728; border-radius: 8px; margin-right: 8px;'>{rid}</span>"
                for rid in reserved_ids
            ]
        )
    else:
        id_html = (
            "<span style='font-size: 16px; color: #999;'>予約済みIDはありません</span>"
        )

    st.markdown(
        f"""
        <div style='
            margin-top: 20px;
        '>
            <div style='
                font-size: 16px;
                color: #666;
                margin-bottom: 5px;
            '>発行済 捕獲番号:</div>
            <div>{id_html}</div>
        </div>
        <br>""",
        unsafe_allow_html=True,
    )

    # --- ID追加発行ボタン ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("捕獲番号追加")
        num_ids = 1
        if st.button("ID追加発行", key="add_result_id"):
            new_ids = get_result_ids(
                num=num_ids, user_name=st.session_state.user["user_name"]
            )
            data_all = get_all_data()
            st.session_state.catch_results = data_all["catch_results"]
            reserved_ids = [
                d["result_id"]
                for d in st.session_state.catch_results
                if d.get("status") == "reserved" and d.get("reserved_by") == user_name
            ]
            reserved_ids = sorted(
                reserved_ids,
                key=lambda x: (
                    int(x.split("-", 1)[1]) if isinstance(x, str) and "-" in x else 0
                ),
            )
            st.rerun()
    with col2:
        # 予約済み発行IDのうち、最大のIDを1件だけ削除
        if reserved_ids:
            if st.button("予約済みIDを削除", key="delete_reserved_id"):
                client = st.session_state["cosmos_client"]
                max_id = max(
                    reserved_ids,
                    key=lambda x: (
                        int(x.split("-", 1)[1])
                        if isinstance(x, str) and "-" in x
                        else 0
                    ),
                )
                # 仮登録レコードを削除
                rec = next(
                    (
                        d
                        for d in st.session_state.catch_results
                        if d.get("result_id") == max_id
                    ),
                    None,
                )
                if rec:
                    client.delete_item_from_container(rec["id"], "result")
                    # session_stateも更新
                    st.session_state.catch_results = [
                        d
                        for d in st.session_state.catch_results
                        if d.get("result_id") != max_id
                    ]
                    st.rerun()
        else:
            st.write("予約済みIDはありません")
    if not catch_method:
        return

    with st.form(key="catch_result"):
        st.caption("入力は１頭ずつ行って下さい")
        users = st.segmented_control(
            "従事者選択",
            user_options,
            key="user_select",
            selection_mode="multi",
            default=[st.session_state["user"]["user_name"]],
        )
        date = st.date_input("捕獲日を選択", datetime.today())

        sex = st.segmented_control("雌雄", ["オス", "メス"], selection_mode="single")
        adult = st.segmented_control(
            "成獣・幼獣", ["成獣", "幼獣"], selection_mode="single"
        )
        size = st.slider("頭胴長（cm）", 0, 150, 50)
        disposal = st.segmented_control(
            "処分方法",
            ["焼却", "自家消費", "埋設", "食肉加工"],
            selection_mode="single",
            default="焼却",
        )
        comment = st.text_input("(任意) コメントを入力")

        # --- 画像フィールド定義 ---
        image_fields = [
            ("image1", "止め刺し直後の写真"),
            ("image2", "尻尾切除前"),
            ("image3", "尻尾切除後"),
            (
                "image4",
                "焼却・自家消費・食肉加工：トラックの荷台で撮影／埋設：穴に獲物を入れた状態を撮影",
            ),
            ("image5", "埋設：埋設後を撮影"),
            ("image6", "歯列写真"),
        ]
        images = {}
        for key, label in image_fields:
            images[key] = st.file_uploader(
                label, accept_multiple_files=False, type=["jpg", "png"]
            )

        # --- 画像必須条件の判定 ---
        def is_required_image(key, adult, disposal):
            # 歯列写真は幼獣なら不要
            if key == "image6" and adult == "幼獣":
                return False
            # image5は埋設以外なら不要
            if key == "image5" and disposal != "埋設":
                return False
            return True

        trap = (
            [obj["id"] for obj in st.session_state.selected_objects.get("map", [])]
            if "map" in st.session_state.selected_objects
            else ""
        )
        submit_button = st.form_submit_button(label="送信")

        if submit_button:
            # 入力チェック
            missing_fields = []
            if not result_id:
                missing_fields.append("捕獲識別番号を発行・選択してください。")
            if not users:
                missing_fields.append("従事者を選択してください。")
            if not catch_method:
                missing_fields.append("捕獲方法を選択してください。")
            if not sex:
                missing_fields.append("雌雄を選択してください。")
            if not adult:
                missing_fields.append("成獣・幼獣を選択してください。")
            if not size:
                missing_fields.append("頭胴長サイズを選択してください。")
            if not disposal:
                missing_fields.append("処分方法を選択してください。")
            # 画像必須条件に応じてチェック
            for key, label in image_fields:
                if is_required_image(key, adult, disposal):
                    if not images[key]:
                        missing_fields.append(
                            f"{label}画像をアップロードしてください。"
                        )
            if missing_fields:
                for msg in missing_fields:
                    st.error(msg)
                return

        with st.spinner("データを送信しています...", show_time=True):
            now = datetime.now().strftime("%Y%m%d%H%M%S")
            image_names = {}

            for idx, (key, _) in enumerate(image_fields, 1):
                if not is_required_image(key, adult, disposal):
                    image_names[key] = None
                    continue  # 不要な画像はスキップ
                file = images[key]
                if file is None:
                    return
                file.seek(0)
                ext = file.name.split(".")[-1]
                name = f"{now}_{st.session_state.catch_method_option[catch_method]}_{key}.{ext}"
                upload_onedrive(f"Apps_Images/catch_result/{name}", file)
                image_names[key] = name

            location_image = images["image2"]
            location_image.seek(0)
            gps_coordinates = get_gps_coordinates(location_image.read())
            if gps_coordinates:
                gps_data = True
            location_image.seek(0)
            lat, lon = gps_coordinates

            # --- 仮登録レコードを正式登録に上書き ---
            client = st.session_state["cosmos_client"]
            # 最新データ取得
            data_all = get_all_data()
            st.session_state.catch_results = data_all["catch_results"]
            # 自分がreservedした最小IDのレコードを探す
            user_name = (
                st.session_state.user["user_name"] if st.session_state.user else None
            )
            reserved = [
                d
                for d in st.session_state.catch_results
                if d.get("result_id") == result_id
                and d.get("status") == "reserved"
                and d.get("reserved_by") == user_name
            ]
            if not reserved:
                st.error(
                    "指定したIDの仮登録レコードが見つかりません。他ユーザーが既に登録した可能性があります。再取得してください。"
                )
                return
            reserved_rec = reserved[0]
            # 上書きデータ作成
            data = {
                **reserved_rec,
                "status": "registered",
                "users": users,
                "catch_date": date.strftime("%Y-%m-%d"),
                "catch_method": catch_method,
                "trap": trap,
                "latitude": lat,
                "longitude": lon,
                "sex": sex,
                "adult": adult,
                "size": size,
                "disposal": disposal,
                "comment": comment,
            }
            data.update(image_names)

            client.upsert_to_container(data)
            # session_stateも更新
            for i, d in enumerate(st.session_state.catch_results):
                if d["id"] == reserved_rec["id"]:
                    st.session_state.catch_results[i] = data
                    break
            submit_button = False  # フォーム送信後は再送信防止
            st.success(f"{result_id}: 登録完了しました。")

        # 使用済みIDは選択肢から除外
        if "issued_result_ids" in st.session_state:
            st.session_state["issued_result_ids"] = [
                i for i in st.session_state["issued_result_ids"] if i != result_id
            ]


def edit_catch_result():
    client = st.session_state["cosmos_client"]
    data = st.session_state["catch_results"]

    st.subheader("捕獲実績編集")
    with st.form(key="edit_catch_result_filter"):
        filter_users = st.multiselect("従事者で絞り込み", user_options)
        filter_catch_method = st.selectbox(
            "捕獲方法で絞り込み",
            [""] + list(st.session_state.catch_method_option.keys()),
        )
        filter_date_from = st.date_input(
            "捕獲日(開始)", value=None, key="filter_date_from"
        )
        filter_date_to = st.date_input("捕獲日(終了)", value=None, key="filter_date_to")
        filter_button = st.form_submit_button("実績絞り込み")

    filtered = data
    if filter_users:
        filtered = [
            d for d in filtered if any(u in d.get("users", []) for u in filter_users)
        ]
    if filter_catch_method:
        filtered = [d for d in filtered if d.get("catch_method") == filter_catch_method]
    if filter_date_from:
        filtered = [
            d
            for d in filtered
            if "catch_date" in d
            and d["catch_date"] >= filter_date_from.strftime("%Y-%m-%d")
        ]
    if filter_date_to:
        filtered = [
            d
            for d in filtered
            if "catch_date" in d
            and d["catch_date"] <= filter_date_to.strftime("%Y-%m-%d")
        ]

    st.caption(f"該当件数: {len(filtered)}")
    for idx, d in enumerate(filtered):
        with st.expander(
            f"{d.get('result_id', '')} | {d.get('catch_date', '')} | {', '.join(d.get('users', []))} | {d.get('catch_method', '')}"
        ):
            st.write(f"捕獲識別番号: {d.get('result_id', '')}")
            st.write(f"捕獲日: {d.get('catch_date', '')}")
            st.write(f"従事者: {', '.join(d.get('users', []))}")
            st.write(f"捕獲方法: {d.get('catch_method', '')}")
            st.write(f"雌雄: {d.get('sex', '')}")
            st.write(f"成獣・幼獣: {d.get('adult', '')}")
            st.write(f"頭胴長: {d.get('size', '')} cm")
            st.write(f"処分方法: {d.get('disposal', '')}")
            st.write(f"コメント: {d.get('comment', '')}")

            col1, col2 = st.columns([2, 1])
            with col1:
                edit_key = f"edit_{d['id']}"
                if st.button("編集", key=edit_key):
                    st.session_state["editing_result_id"] = d["id"]
                if st.session_state.get("editing_result_id") == d["id"]:
                    with st.form(key=f"edit_form_{d['id']}"):
                        edit_users = st.multiselect(
                            "従事者",
                            user_options,
                            default=d.get("users", []),
                            key=f"edit_users_{d['id']}",
                        )
                        edit_catch_method = st.selectbox(
                            "捕獲方法",
                            list(st.session_state.catch_method_option.keys()),
                            index=list(
                                st.session_state.catch_method_option.keys()
                            ).index(d.get("catch_method", "")),
                            key=f"edit_catch_method_{d['id']}",
                        )
                        edit_date = st.date_input(
                            "捕獲日",
                            value=datetime.strptime(
                                d.get("catch_date", ""), "%Y-%m-%d"
                            ),
                            key=f"edit_date_{d['id']}",
                        )
                        edit_sex = st.segmented_control(
                            "雌雄",
                            ["オス", "メス"],
                            selection_mode="single",
                            default=d.get("sex", "オス"),
                            key=f"edit_sex_{d['id']}",
                        )
                        edit_adult = st.segmented_control(
                            "成獣・幼獣",
                            ["成獣", "幼獣"],
                            selection_mode="single",
                            default=d.get("adult", "成獣"),
                            key=f"edit_adult_{d['id']}",
                        )
                        edit_size = st.slider(
                            "頭胴長（cm）",
                            0,
                            150,
                            int(d.get("size", 50)),
                            key=f"edit_size_{d['id']}",
                        )
                        edit_disposal = st.segmented_control(
                            "処分方法",
                            ["焼却", "自家消費", "埋設", "食肉加工"],
                            selection_mode="single",
                            default=d.get("disposal", "焼却"),
                            key=f"edit_disposal_{d['id']}",
                        )
                        edit_comment = st.text_input(
                            "コメント",
                            value=d.get("comment", ""),
                            key=f"edit_comment_{d['id']}",
                        )
                        # 画像フィールド
                        image_fields = [
                            ("image1", "止め刺し直後"),
                            ("image2", "尻尾切除前"),
                            ("image3", "尻尾切除後"),
                            ("image4", "処分方法に応じた画像1"),
                            ("image5", "処分方法に応じた画像2"),
                            ("image6", "歯列写真"),
                        ]
                        st.text("アップロード済み画像:")
                        for img_idx, (img_key, img_label) in enumerate(image_fields):
                            img_name = d.get(img_key)
                            if img_name:
                                file_path = f"Apps_Images/catch_result/{img_name}"
                                image_data, error = download_onedrive_image(file_path)
                                if error:
                                    st.warning(f"{img_name} の取得失敗: {error}")
                                else:
                                    st.image(
                                        image_data,
                                        caption=img_name,
                                        use_container_width=True,
                                    )
                                # 差し替え機能
                                replace_file = st.file_uploader(
                                    f"{img_label} ({img_name}) を差し替える",
                                    type=["jpg", "jpeg", "png"],
                                    key=f"replace_{d['id']}_{img_key}",
                                    accept_multiple_files=False,
                                )
                        # 追加: 写真追加用アップローダー（捕獲実績は6枚固定なので追加は不要）

                        submit_edit = st.form_submit_button("保存")
                        if submit_edit:
                            now = datetime.now().strftime("%Y%m%d%H%M%S")
                            # 差し替え時combine_images_with_bandを適用する画像キー
                            combine_keys = ["image1", "image2", "image3", "image4"]
                            # combine_images_with_band用データ
                            combine_data = {
                                "捕獲日": edit_date,
                                "委託業務名": "渥美地区野生イノシシ根絶事業",
                                "実施地域": "渥美地区",
                                "捕獲者": ", ".join(edit_users),
                            }
                            for img_idx, (img_key, img_label) in enumerate(
                                image_fields
                            ):
                                replace_file = st.session_state.get(
                                    f"replace_{d['id']}_{img_key}"
                                )
                                if replace_file:
                                    ext = replace_file.name.split(".")[-1]
                                    new_img_name = f"{now}_{st.session_state.catch_method_option[edit_catch_method]}_{img_key}.{ext}"
                                    replace_file.seek(0)
                                    upload_onedrive(
                                        f"Apps_Images/catch_result/{new_img_name}",
                                        replace_file,
                                    )
                                    d[img_key] = new_img_name
                                    st.success(
                                        f"{img_label} を {new_img_name} に差し替えました。"
                                    )
                            # データを更新
                            d["users"] = edit_users
                            d["catch_method"] = edit_catch_method
                            d["catch_date"] = edit_date.strftime("%Y-%m-%d")
                            d["sex"] = edit_sex
                            d["adult"] = edit_adult
                            d["size"] = edit_size
                            d["disposal"] = edit_disposal
                            d["comment"] = edit_comment
                            d["id"] = d["id"]
                            d["fy"] = d["fy"]
                            d["category"] = "result"
                            submit_data(d)
                            # st.session_state["catch_results"] からidで検索して更新
                            for i, result in enumerate(
                                st.session_state["catch_results"]
                            ):
                                if result["id"] == d["id"]:
                                    st.session_state["catch_results"][i] = d
                                    break
                            st.success("編集内容を保存しました")
                            st.session_state["editing_result_id"] = None
                            st.rerun()
                    if st.button("キャンセル", key=f"edit_cancel_{d['id']}"):
                        st.session_state["editing_result_id"] = None
                        st.rerun()
            with col2:
                confirm_key = f"confirm_delete_{d['id']}"
                if st.button("削除", key=f"delete_{d['id']}"):
                    st.session_state[confirm_key] = True
                if st.session_state.get(confirm_key, False):
                    st.warning("本当に削除しますか？")
                    if st.button("削除", key=f"confirm_yes_{d['id']}"):
                        client.delete_item_from_container(d["id"], "result")
                        st.session_state["catch_results"].remove(d)
                        st.success("削除しました")
                        st.session_state[confirm_key] = False
                        st.rerun()
                    if st.button("キャンセル", key=f"confirm_cancel_{d['id']}"):
                        st.session_state[confirm_key] = False
