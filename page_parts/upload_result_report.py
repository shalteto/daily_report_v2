import streamlit as st
from page_parts.trap_map import trap_map
from datetime import datetime, timedelta
from azure_.one_drive import upload_onedrive, download_onedrive_image
from page_parts.upload_daily_report import submit_data
from services.gps import get_gps_coordinates
from services.image import combine_images_with_band
import uuid
import os

users_df = st.session_state.users
user_options = list({u["user_name"] for u in users_df})


def get_result_id(user_code):
    """
    st.session_state["result"] から user_code で始まる result_id をカウントし、
    次の result_id を生成して返す。
    例: user_code='SS' なら 'SS-1', 'SS-2', ... のように付番
    実績がない場合も 'SS-1' となる。
    """
    results = st.session_state.get("result", [])
    count = sum(
        1
        for r in results
        if isinstance(r.get("result_id", ""), str)
        and r.get("result_id", "").startswith(user_code)
    )
    return f"{user_code}-{count + 1}"


def upsert_catch_result():
    catch_method = st.segmented_control(
        "捕獲方法を選択",
        list(st.session_state.catch_method_option.keys()),
        selection_mode="single",
    )
    if catch_method in ["くくり罠", "箱罠"]:
        trap_map(mode="稼働中", multi_select="single-object")
    if st.session_state.selected_objects:
        for p in st.session_state.selected_objects["map"]:
            st.write(f"選択中の罠：{p['trap_name']}")
    with st.form(key="catch_result"):
        st.caption("入力は１頭ずつ行って下さい")
        user_code = st.session_state["user"]["user_code"]
        result_id = get_result_id(user_code)
        st.markdown(f"捕獲識別番号: **{result_id}**")
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

        image_fields = [
            ("image1", "止め刺し前の捕獲確認"),
            ("image2", "止め刺し後の捕獲確認"),
            ("image3", "尻尾切除確認"),
            (
                "image4",
                "焼却・自家消費・食肉加工：トラックの荷台で撮影／埋設：穴に獲物を入れた状態を撮影",
            ),
            (
                "image5",
                "焼却・自家消費・食肉加工：施設搬入前で撮影／埋設：埋設後を撮影",
            ),
            ("image6", "歯列写真"),
        ]
        images = {}
        for key, label in image_fields:
            images[key] = st.file_uploader(
                label, accept_multiple_files=False, type=["jpg", "png"]
            )

        trap = (
            [obj["id"] for obj in st.session_state.selected_objects.get("map", [])]
            if "map" in st.session_state.selected_objects
            else ""
        )
        submit_button = st.form_submit_button(label="送信")

    if submit_button:
        # 入力チェック
        missing_fields = []
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
        for key, label in image_fields:
            if not images[key]:
                missing_fields.append(f"{label}画像をアップロードしてください。")
        if missing_fields:
            for msg in missing_fields:
                st.error(msg)
            return

        now = datetime.now().strftime("%Y%m%d%H%M%S")
        image_names = {}

        # combine_images_with_band用データ
        combine_data = {
            "捕獲日": date,
            "委託業務名": "渥美地区野生イノシシ根絶事業",
            "実施地域": "渥美地区",
            "捕獲者": st.session_state["user"]["user_name"],
        }

        # combine_images_with_bandで処理する画像キー
        combine_keys = ["image1", "image2", "image3", "image4"]
        with st.spinner("許可証画像をダウンロードしています...", show_time=True):
            permit_image_data, _ = download_onedrive_image(
                f"user_image/{st.session_state['user']['permit_img_name']}"
            )
            # permit_img で取得した画像を保存
            permit_image_path = "permit_image_data.png"
            with open(permit_image_path, "wb") as f:
                f.write(permit_image_data)

        for idx, (key, _) in enumerate(image_fields, 1):
            file = images[key]
            file.seek(0)
            if key in combine_keys:
                with st.spinner(
                    f"{key} の画像を処理・アップロード中...", show_time=True
                ):
                    # combine_images_with_bandで画像を処理
                    processed_img_path = combine_images_with_band(
                        file,
                        combine_data,
                        permit_img_path=permit_image_path,
                        font_path="NotoSansJP-Regular.ttf",
                    )
                    name = f"{now}_{st.session_state.catch_method_option[catch_method]}_{key}.png"
                    with open(processed_img_path, "rb") as processed_file:
                        processed_img = processed_file.read()
                    print(f"アップロード開始{key}：{name}")
                    upload_onedrive(f"catch_result/{name}", processed_img)
            else:
                with st.spinner(f"{key} の画像をアップロード中...", show_time=True):
                    ext = file.name.split(".")[-1]
                    name = f"{now}_{st.session_state.catch_method_option[catch_method]}_{key}.{ext}"
                    print(f"アップロード開始{key}：{name}")
                    upload_onedrive(f"catch_result/{name}", file)
            image_names[key] = name

        location_image = images["image2"]
        location_image.seek(0)
        gps_coordinates = get_gps_coordinates(location_image.read())
        if gps_coordinates:
            gps_data = True
        location_image.seek(0)
        lat, lon = gps_coordinates

        data = {
            "id": str(uuid.uuid4()),
            "category": "result",
            "fy": st.session_state.fy,
            "result_id": result_id,
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
        # 画像名をdataに追加
        data.update(image_names)
        with st.spinner("データを送信しています...", show_time=True):
            submit_data(data)
            st.session_state["catch_results"].append(data)


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
            f"{d.get('catch_date', '')} | {', '.join(d.get('users', []))} | {d.get('catch_method', '')}"
        ):
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
                            ("image1", "止め刺し前の捕獲確認"),
                            ("image2", "止め刺し後の捕獲確認"),
                            ("image3", "尻尾切除確認"),
                            ("image4", "処分方法に応じた画像1"),
                            ("image5", "処分方法に応じた画像2"),
                            ("image6", "歯列写真"),
                        ]
                        st.text("アップロード済み画像:")
                        for img_idx, (img_key, img_label) in enumerate(image_fields):
                            img_name = d.get(img_key)
                            if img_name:
                                file_path = f"catch_result/{img_name}"
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
                            # permit_img取得
                            permit_img = download_onedrive_image(
                                f"user_image/{st.session_state['user']['permit_img_name']}"
                            )
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
                                    if img_key in combine_keys:
                                        # combine_images_with_bandで画像を処理
                                        processed_img = combine_images_with_band(
                                            replace_file,
                                            combine_data,
                                            permit_img_path=permit_img,
                                            font_path="NotoSansJP-Regular.ttf",
                                        )
                                        upload_onedrive(
                                            f"catch_result/{new_img_name}",
                                            processed_img,
                                        )
                                    else:
                                        upload_onedrive(
                                            f"catch_result/{new_img_name}", replace_file
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
