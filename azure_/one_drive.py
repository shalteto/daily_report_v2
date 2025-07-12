import os
import requests


# Microsoft Entra ID の情報
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TARGET_USER = os.getenv("TARGET_USER")  # suzuki_shoichiro@atsumi-sat.com


def get_access_token():
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    response = requests.post(token_url, data=data)
    return response.json().get("access_token")


def upload_onedrive(filename, uploaded_file):
    access_token = get_access_token()
    if not access_token:
        return "アクセストークン取得失敗"
    # filename = "daily_report/" + filename
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }
    upload_url = f"https://graph.microsoft.com/v1.0/users/{TARGET_USER}/drive/root:/{filename}:/content"
    response = requests.put(upload_url, headers=headers, data=uploaded_file)

    return (
        "✅ アップロード成功"
        if response.status_code in [200, 201]
        else f"❌ アップロード失敗: {response.text}"
    )


def download_onedrive_image(file_path):
    """
    OneDriveから画像ファイルをダウンロードする
    :param file_path: OneDrive上のファイルパス（例: 'daily_report/sample.png'）
    :return: バイナリデータ or エラーメッセージ
    """
    access_token = get_access_token()
    if not access_token:
        return None, "アクセストークン取得失敗"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    download_url = f"https://graph.microsoft.com/v1.0/users/{TARGET_USER}/drive/root:/{file_path}:/content"
    response = requests.get(download_url, headers=headers, stream=True)
    if response.status_code == 200:
        return response.content, None
    else:
        return None, f"❌ ダウンロード失敗: {response.text}"


def dl_and_save_test():
    image_path = "daily_report/image02.jpg"
    image_data, error = download_onedrive_image(image_path)
    if error:
        print(error)
    else:
        with open("test.jpg", "wb") as f:
            f.write(image_data)
        print("✅ ダウンロード成功")


if __name__ == "__main__":
    # アップロードテスト
    # with open("test.txt", "rb") as f:
    #     print(upload_onedrive(None, "test.txt", f))

    # ダウンロードテスト
    dl_and_save_test()
