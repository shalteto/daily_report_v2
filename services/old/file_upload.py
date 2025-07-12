from azure_.one_drive import upload_blob
from services.gps import get_gps_coordinates
from datetime import datetime


task_dict = {
    "わな猟見回り": "trap_research",
    "わな猟調査": "trap_setting",
    "わな猟設置": "trap_remove",
    "わな猟撤去": "trap_resetting",
    "わな猟移設": "trap_check",
    "銃猟調査": "gun_research",
    "銃猟誘引狙撃": "gun_calling",
    "銃猟巻き狩り": "gun_driven_hunting",
    "銃猟忍び猟": "gun_sneak_hunting",
    "その他": "other",
}


def file_upload(uploaded_files, task_type):
    images = []
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    index = 0
    for uploaded_file in uploaded_files:
        gps_coordinates = get_gps_coordinates(uploaded_file.read())
        extension = uploaded_file.name.split(".")[-1]
        blob_name = f"{now}_{task_dict[task_type]}_{index}.{extension}"
        images.append({"name": blob_name})
        uploaded_file.seek(0)
        upload_blob(
            "",
            blob_name,
            uploaded_file,
        )
        index += 1
    return images
