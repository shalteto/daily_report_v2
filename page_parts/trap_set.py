import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, timedelta
from azure_.one_drive import upload_onedrive
from services.map_mesh import get_aichi_mesh
from page_parts.trap_map import trap_map
from services.gps import get_gps_coordinates
import time


def file_upload_trap(uploaded_files, trap_id):
    images = []
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    index = 1
    for uploaded_file in uploaded_files:
        extension = uploaded_file.name.split(".")[-1]
        blob_name = f"{now}_{trap_id}_{index}.{extension}"
        images.append({"name": blob_name})
        uploaded_file.seek(0)
        upload_onedrive(
            f"Apps_Images/trap_set/{blob_name}",
            uploaded_file,
        )
        index += 1
    return images


def get_trap_id():
    """
    st.session_state["trap"] をカウントし、次の trap_id を生成して返す。
    """
    traps = st.session_state.get("traps", [])
    print(f"現在の罠数: {len(traps)}")
    count = len(traps)
    # return f"T{count + 1}"
    return count + 1


def submit_data(data):
    client = st.session_state["cosmos_client"]
    try:
        client.upsert_to_container(data)
    except Exception as e:
        st.error(f"CosmosDB登録エラー: {e}")
        return


def trap_set():
    st.subheader("罠設置")

    # --- 座標取得方法を先に選択 ---
    st.markdown("#### 座標取得方法を選択")
    coord_method = st.radio(
        "座標取得方法", ("写真のGPSデータ", "手動入力"), horizontal=True
    )

    with st.form(key="trap_set_form"):
        st.write("1地点ずつ登録してください")
        trap_id = get_trap_id()
        st.markdown(f"罠番号: **{trap_id}**")

        # --- 選択に応じた入力欄表示 ---
        trap_images = None
        manual_lat, manual_lon = None, None

        if coord_method == "写真のGPSデータ":
            trap_images = st.file_uploader(
                "1地点で1つ写真撮影（GPS情報付き）",
                accept_multiple_files=True,
                type=["jpg", "png"],
            )
        else:  # 手動入力
            col1, col2 = st.columns(2)
            with col1:
                manual_lat = st.number_input(
                    "緯度", format="%.6f", value=34.600000, step=0.000001
                )
            with col2:
                manual_lon = st.number_input(
                    "経度", format="%.6f", value=137.200000, step=0.000001
                )

        trap_name = st.text_input(
            "罠の通称（地図に表示する任意の名称）", key="trap_name"
        )
        trap_type = st.segmented_control(
            "罠種類",
            ["くくり", "箱"],
            default="くくり",
            selection_mode="single",
        )
        number = st.segmented_control(
            "設置数(1地点中の個数)",
            [1, 2, 3, 4, 5],
            default=3,
            selection_mode="single",
        )
        date = st.date_input("日付")

        submit_button = st.form_submit_button(label="送信")

        # --- フォーム送信後の処理 ---
        if submit_button:
            gps_coordinates = None

            if coord_method == "写真のGPSデータ":
                if trap_images and len(trap_images) > 0:
                    with st.spinner("GPSデータ取得中...", show_time=True):
                        trap_images[0].seek(0)
                        gps_coordinates = get_gps_coordinates(trap_images[0].read())
                        trap_images[0].seek(0)
                else:
                    st.error("写真をアップロードしてください。")
                    return

            else:  # 手動入力
                if manual_lat and manual_lon:
                    gps_coordinates = (manual_lat, manual_lon)
                else:
                    st.error("緯度と経度を入力してください。")
                    return

            # --- 共通登録処理 ---
            if trap_name and gps_coordinates:
                images = []
                if coord_method == "写真のGPSデータ":
                    with st.spinner("画像アップロード中...", show_time=True):
                        images = file_upload_trap(trap_images, trap_id)

                lat, lon = gps_coordinates
                data = {
                    "id": str(uuid.uuid4()),
                    "category": "trap",
                    "fy": st.session_state.fy,
                    "trap_id": trap_id,
                    "latitude": lat,
                    "longitude": lon,
                    "mesh": get_aichi_mesh(lat, lon),
                    "number": number,
                    "status": "稼働中",
                    "start_date": date.strftime("%Y-%m-%d"),
                    "end_date": None,
                    "trap_name": trap_name,
                    "trap_type": trap_type,
                    "images": images,
                }

                try:
                    with st.spinner("CosmosDBへ登録中...", show_time=True):
                        submit_data(data=data)
                        st.session_state["traps"].append(data)
                    st.success("登録完了")
                except Exception as e:
                    st.error(f"CosmosDB登録エラー: {e}")
                    return
            else:
                if not trap_name:
                    st.error("罠の通称を入力してください。")


def change_trap_status(map_data, status, end_date=None):
    client = st.session_state["cosmos_client"]
    # データからcolorカラムを除去し、statusを更新
    updated_data = []
    for data in map_data:
        data.pop("color")
        data["status"] = status
        if status == "撤去済み":
            data["end_date"] = end_date.strftime("%Y-%m-%d")
        else:
            data["end_date"] = None
        updated_data.append(data)

    for data in updated_data:
        client.upsert_to_container(data)

    for updated_record in updated_data:
        for i, trap in enumerate(st.session_state.traps):
            if trap["id"] == updated_record["id"]:
                st.session_state.traps[i] = updated_record
                break

    return True


def trap_stasus_change():
    st.subheader("罠状況変更")

    trap_map_mode = st.segmented_control(
        "表示する罠",
        ["すべて", "稼働中", "撤去済み"],
        default="すべて",
        selection_mode="single",
    )
    trap_map(mode=trap_map_mode)
    st.caption("選択中の罠")
    if st.session_state.selected_objects:
        for p in st.session_state.selected_objects["map"]:
            st.write(
                f"{p["trap_name"]} / {round(p["latitude"],5)}, {round(p["longitude"],5)}"
            )

    end_date = st.date_input("撤去日", value=datetime.now())
    col1, col2 = st.columns(2)
    success = False
    with col2:
        if st.button("稼働中に戻す"):
            success = change_trap_status(
                st.session_state.selected_objects["map"], "稼働中"
            )
    with col1:
        if st.button("撤去済みにする"):
            success = change_trap_status(
                st.session_state.selected_objects["map"], "撤去済み", end_date=end_date
            )
    if success == True:
        st.success("罠の状況を変更しました")
        if st.button("罠マップの再読み込み"):
            st.rerun()


def trap_edit():
    client = st.session_state["cosmos_client"]
    st.subheader("罠の名称等を変更")

    trap_map_mode = st.segmented_control(
        "表示する罠",
        ["すべて", "稼働中", "撤去済み"],
        default="すべて",
        selection_mode="single",
    )
    trap_map(mode=trap_map_mode, multi_select="single-object")
    if st.session_state.selected_objects != {"map": []}:
        selected_trap = st.session_state.selected_objects["map"][0]
        trap_name = st.text_input(
            "罠の通称（地図に表示する名称）", value=selected_trap["trap_name"]
        )
        trap_type = st.segmented_control(
            "罠種類",
            ["くくり", "箱"],
            default=selected_trap["trap_type"],
            selection_mode="single",
        )
        number = st.segmented_control(
            "設置数(1スポット中の個数)",
            [1, 2, 3, 4, 5],
            selection_mode="single",
            default=selected_trap["number"],
        )

        start_date = st.date_input(
            "設置日",
            value=(
                datetime.strptime(selected_trap["start_date"], "%Y-%m-%d")
                if selected_trap.get("start_date")
                else datetime.now()
            ),
        )
        end_date = st.date_input(
            "撤去日（未撤去の場合は空欄）",
            value=(
                datetime.strptime(selected_trap["end_date"], "%Y-%m-%d")
                if selected_trap.get("end_date")
                else None
            ),
        )

    if st.button("更新"):
        selected_trap["trap_name"] = trap_name
        selected_trap["trap_type"] = trap_type
        selected_trap["number"] = number
        selected_trap["start_date"] = start_date.strftime("%Y-%m-%d")
        selected_trap["end_date"] = end_date.strftime("%Y-%m-%d") if end_date else None

        try:
            client.upsert_to_container(data=selected_trap)
            st.success("更新完了")

            for trap in st.session_state.traps:
                if trap["id"] == selected_trap["id"]:
                    trap["trap_name"] = trap_name
                    trap["trap_type"] = trap_type
                    trap["number"] = number
                    trap["start_date"] = selected_trap["start_date"]
                    trap["end_date"] = selected_trap["end_date"]
                    break
        except Exception as e:
            st.error(f"CosmosDB登録エラー: {e}")
