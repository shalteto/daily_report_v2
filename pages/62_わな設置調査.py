import streamlit as st
import pandas as pd
import pydeck as pdk
from PIL import Image
import piexif
import io
import math
import uuid
from azure_.cosmosdb import CosmosDBClient


# --- GPS座標抽出 ---
def get_gps_coordinates(file_data):
    img = Image.open(io.BytesIO(file_data))
    exif_data = img.info.get("exif")
    if not exif_data:
        return None
    exif_dict = piexif.load(exif_data)
    gps_info = exif_dict.get("GPS", {})
    if not gps_info:
        return None

    def convert_to_degrees(value):
        d, m, s = value
        return d[0] / d[1] + (m[0] / m[1]) / 60 + (s[0] / s[1]) / 3600

    try:
        lat = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLatitude])
        lon = convert_to_degrees(gps_info[piexif.GPSIFD.GPSLongitude])
        if gps_info[piexif.GPSIFD.GPSLatitudeRef] != b"N":
            lat = -lat
        if gps_info[piexif.GPSIFD.GPSLongitudeRef] != b"E":
            lon = -lon
        return lat, lon
    except Exception:
        return None


# --- 2点間距離（m） ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半径[m]
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# --- 3次メッシュ関連関数 ---
def latlon_to_meshcode(lat, lon, level=3):
    """
    緯度経度から地域メッシュコードを計算します。
    ここでは3次メッシュのみを対象とします。
    """
    if level != 3:
        st.error("現在、3次メッシュのみをサポートしています。")
        return None

    # 1次メッシュ
    p1 = int(lat * 1.5)
    u1 = int((lon - 100) / 1)

    # 2次メッシュ
    p2 = int((lat * 1.5 - p1) * 8)
    u2 = int(((lon - 100) - u1) * 8)

    # 3次メッシュ
    p3 = int(((lat * 1.5 - p1) * 8 - p2) * 10)
    u3 = int((((lon - 100) - u1) * 8 - u2) * 10)

    mesh_code = f"{p1}{u1}{p2}{u2}{p3}{u3}"
    return mesh_code


def meshcode_to_latlon_bounds(mesh_code, level=3):
    """
    地域メッシュコードから緯度経度の境界を計算します。
    """
    if level != 3 or len(mesh_code) != 8:
        st.error(
            "現在、3次メッシュのみをサポートしており、メッシュコードは8桁である必要があります。"
        )
        return None

    p1 = int(mesh_code[0:2])
    u1 = int(mesh_code[2:4])
    p2 = int(mesh_code[4])
    u2 = int(mesh_code[5])
    p3 = int(mesh_code[6])
    u3 = int(mesh_code[7])

    # 南西端の緯度経度
    lat_sw = (p1 + p2 / 8 + p3 / 80) / 1.5
    lon_sw = (u1 + u2 / 8 + u3 / 80) + 100

    # 北東端の緯度経度
    lat_ne = (p1 + p2 / 8 + p3 / 80 + 1 / 80) / 1.5
    lon_ne = (u1 + u2 / 8 + u3 / 80 + 1 / 80) + 100

    return {
        "south_west": (lat_sw, lon_sw),
        "north_east": (lat_ne, lon_ne),
        "north_west": (lat_ne, lon_sw),
        "south_east": (lat_sw, lon_ne),
    }


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
                get_radius=20,
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
            get_line_width=25,
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
            get_line_width=50,
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


# --- Streamlit UI ---
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
