# 緯度経度の情報から、メッシュ情報を取得する
def aichi_mesh_convert(mesh):
    """
    mesh番号の上4桁を以下のルールで記号に変換する。
    meshは5桁以上であった場合は、上4桁を記号に変換して5桁以下を結合する。
    """
    mesh_dict = {
        "5237": "A",
        "5137": "B",
        "5236": "C",
        "5237": "D",
        "5336": "E",
        "5337": "F",
    }

    mesh_str = str(mesh)
    prefix = mesh_str[:4]
    suffix = mesh_str[4:]

    if prefix in mesh_dict:
        return mesh_dict[prefix] + suffix
    else:
        return mesh_str


def get_mesh(lat, lon):
    # 1次メッシュ
    mesh1_lat = int(lat * 1.5)
    mesh1_lon = int(lon - 100)

    # 2次メッシュ
    mesh2_lat = int((lat * 1.5 - mesh1_lat) * 8)
    mesh2_lon = int((lon - 100 - mesh1_lon) * 8)

    # 3次メッシュ
    mesh3_lat = int(((lat * 1.5 - mesh1_lat) * 8 - mesh2_lat) * 10)
    mesh3_lon = int(((lon - 100 - mesh1_lon) * 8 - mesh2_lon) * 10)

    # 2.5次メッシュの計算
    if mesh3_lat < 5:
        if mesh3_lon < 5:
            mesh2_5_lat = 2
            mesh2_5_lon = 2
        else:
            mesh2_5_lat = 2
            mesh2_5_lon = 7
    else:
        if mesh3_lon < 5:
            mesh2_5_lat = 7
            mesh2_5_lon = 2
        else:
            mesh2_5_lat = 7
            mesh2_5_lon = 7

    return f"{mesh1_lat}{mesh1_lon}{mesh2_lat}{mesh2_lon}{mesh2_5_lat}{mesh2_5_lon}"


def get_aichi_mesh(lat, lon):
    """
    緯度経度からメッシュ番号を取得し、Aichi Meshに変換する。
    """
    mesh = get_mesh(lat, lon)
    aichi_mesh = aichi_mesh_convert(mesh)
    return aichi_mesh


# 使い方
# lat, lon = 34.649484, 137.149225
# aichi_mesh = aichi_mesh_convert(get_mesh(lat, lon))
