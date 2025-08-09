import streamlit as st
import pandas as pd
import pydeck as pdk
import uuid
from azure_.cosmosdb import CosmosDBClient
from services.map_mesh import meshcode_to_latlon_bounds
from services.gps import get_gps_coordinates, haversine

st.set_page_config(page_title="わな設置調査", layout="wide", page_icon="🐗")


# --- 地図表示 ---
def show_map(trap_points):
    import importlib.util
    import os

    # mesh_polygons.pyからtarget_mesh_code, special_target_mesh_codeを取得
    mesh_codes_path = os.path.join(os.path.dirname(__file__), "..", "mesh_polygons.py")
    mesh_codes_path = os.path.abspath(mesh_codes_path)
    spec = importlib.util.spec_from_file_location("mesh_polygons", mesh_codes_path)
    mesh_polygons_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mesh_polygons_mod)
    target_mesh_code = set(str(code) for code in mesh_polygons_mod.target_mesh_code)
    special_target_mesh_code = set(
        str(code) for code in mesh_polygons_mod.special_target_mesh_code
    )

    # target/special mesh codeからポリゴン生成
    def meshcode_to_polygon(code):
        bounds = meshcode_to_latlon_bounds(f"{int(code):08d}")
        if not bounds:
            return None
        return {
            "path": [
                [bounds["south_west"][1], bounds["south_west"][0]],
                [bounds["south_east"][1], bounds["south_east"][0]],
                [bounds["north_east"][1], bounds["north_east"][0]],
                [bounds["north_west"][1], bounds["north_west"][0]],
                [bounds["south_west"][1], bounds["south_west"][0]],
            ],
            "code": f"{int(code):08d}",
        }

    mesh_target = [
        meshcode_to_polygon(code)
        for code in target_mesh_code
        if code not in special_target_mesh_code
    ]
    mesh_special = [meshcode_to_polygon(code) for code in special_target_mesh_code]
    mesh_target = [m for m in mesh_target if m]
    mesh_special = [m for m in mesh_special if m]

    # 中心座標計算
    all_lats = []
    all_lons = []
    for mp in mesh_target + mesh_special:
        for coord in mp["path"]:
            all_lons.append(coord[0])
            all_lats.append(coord[1])
    if all_lats and all_lons:
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
    else:
        center_lat = 34.6321655
        center_lon = 137.150609

    layers = []
    # わな設置点のレイヤー
    if trap_points:
        filtered = [r for r in trap_points if "latitude" in r and "longitude" in r]
        if filtered:
            df = pd.DataFrame(filtered)
            df["color"] = [[0, 255, 0, 160]] * len(df)
            layer_trap_points = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position="[longitude, latitude]",
                get_radius=50,
                get_color="color",
                pickable=True,
                auto_highlight=True,
                id="trap_points_layer",
            )
            layers.append(layer_trap_points)

    # target_mesh_code: 青線, 幅25
    if mesh_target:
        df_mesh_target = pd.DataFrame(mesh_target)
        layer_mesh_target = pdk.Layer(
            "PolygonLayer",
            data=df_mesh_target,
            get_polygon="path",
            filled=False,
            stroked=True,
            get_line_color=[0, 0, 255, 255],  # 青
            get_line_width=15,
            pickable=True,
            auto_highlight=True,
            id="mesh_target_layer",
        )
        layers.append(layer_mesh_target)
    # special_target_mesh_code: 赤線, 幅50
    if mesh_special:
        df_mesh_special = pd.DataFrame(mesh_special)
        layer_mesh_special = pdk.Layer(
            "PolygonLayer",
            data=df_mesh_special,
            get_polygon="path",
            filled=False,
            stroked=True,
            get_line_color=[255, 0, 0, 255],  # 赤
            get_line_width=25,
            pickable=True,
            auto_highlight=True,
            id="mesh_special_layer",
        )
        layers.append(layer_mesh_special)

    map_style_options = {
        "衛星写真": "mapbox://styles/mapbox/satellite-v9",
        "アウトドア": "mapbox://styles/mapbox/outdoors-v11",
        "道路地図": "mapbox://styles/mapbox/streets-v11",
        "ライト（明るい）": "mapbox://styles/mapbox/light-v10",
        "ダーク（暗い）": "mapbox://styles/mapbox/dark-v10",
    }
    map_style_label = st.selectbox(
        "地図のスタイルを選択してください", list(map_style_options.keys()), index=0
    )
    map_style_url = map_style_options[map_style_label]

    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=14)
    chart = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style=map_style_url,
        tooltip={"html": "<b>メッシュコード:</b> {code}<br/><b>名前:</b> {name}"},
    )
    st.pydeck_chart(chart, height=600)


from st_init import with_init


@with_init
def main():
    st.subheader("わな設置調査 - 座標登録＆地図表示")
    # CosmosDBクライアント
    if "cosmos_client_traps" not in st.session_state:
        st.session_state["cosmos_client_traps"] = CosmosDBClient(container_name="traps")
    client = st.session_state["cosmos_client_traps"]

    # 既存座標データ取得
    query = "SELECT c.latitude, c.longitude, c.name FROM c"
    existing = client.search_container_by_query(query, [])
    existing_coords = [
        (r["latitude"], r["longitude"])
        for r in existing
        if r.get("latitude") and r.get("longitude")
    ]

    st.caption("画像ファイルから座標登録")
    uploaded_files = st.file_uploader(
        "画像ファイルをアップロード（複数可）",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )
    if uploaded_files and st.button("座標登録"):
        # 画像→座標抽出
        coords = []
        file_names = []
        for f in uploaded_files:
            f.seek(0)
            c = get_gps_coordinates(f.read())
            if c:
                coords.append(c)
                file_names.append(f.name)
        # 画像内15m以内の重複除去
        filtered = []
        for c in coords:
            if all(haversine(c[0], c[1], fc[0], fc[1]) > 1 for fc in filtered):
                filtered.append(c)
        # 既存座標と15m以内のものを除外
        new_points = []
        for c in filtered:
            if all(haversine(c[0], c[1], ec[0], ec[1]) > 1 for ec in existing_coords):
                new_points.append(c)
        # CosmosDBへ登録（id必須）
        # new_pointsとcoords/file_namesの順序を合わせるため、coords→filtered→new_pointsのindexを追跡
        to_insert = []
        for c in new_points:
            # filteredのindexを取得（coords, file_namesと同じ順序）
            try:
                idx = filtered.index(c)
                fname = file_names[idx]
            except Exception:
                fname = ""
            to_insert.append(
                {
                    "id": str(uuid.uuid4()),
                    "name": fname,
                    "latitude": c[0],
                    "longitude": c[1],
                }
            )
        if to_insert:
            client.upsert_to_container(to_insert)
            st.success(f"{len(to_insert)}件の座標を登録しました")
        else:
            st.info("新規登録すべき座標はありませんでした")

    # 座標手動入力フォーム
    st.caption("座標を手動で入力")
    manual_lat = st.number_input("緯度", format="%.6f")
    manual_lon = st.number_input("経度", format="%.6f")
    manual_name = st.text_input("名前")

    if st.button("手動で座標登録"):
        if manual_lat and manual_lon and manual_name:
            new_manual_point = {
                "id": str(uuid.uuid4()),
                "name": manual_name,
                "latitude": manual_lat,
                "longitude": manual_lon,
            }
            client.upsert_to_container([new_manual_point])
            st.success("手動で入力された座標を登録しました")
        else:
            st.warning("緯度、経度、名前をすべて入力してください")

    # 最新データ取得
    traps = client.search_container_by_query(
        "SELECT c.latitude, c.longitude, c.name FROM c", []
    )
    # Noneや不正なデータを除外
    traps = [
        r for r in traps if isinstance(r, dict) and "latitude" in r and "longitude" in r
    ]
    st.session_state["traps_point"] = traps

    st.subheader("地図上に座標を表示")

    show_map(st.session_state["traps_point"])


if __name__ == "__main__":
    main()
