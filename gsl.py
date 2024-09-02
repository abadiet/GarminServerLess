import requests

class CIQ:
    def get_app_id(ciq_url: str) -> str:
        app_id = ciq_url.split("garmin.com/apps/")
        if len(app_id) < 2:
            raise Exception(f"Invalid CIQ URL: {ciq_url}")
        app_id = app_id[1].split("/")[0]
        return app_id

    def get_last_app_version(app_id: str, session_cookie: str) -> str:
        resp = requests.post(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_id}/install?unitId=a", cookies={"session": session_cookie})
        arr = resp.text.split("appVersionId=")
        if len(arr) != 2:
            raise Exception(f"Failed to get app version {resp.url}: {resp.text}")
        return arr[1].split(",")[0]

    def download_app(app_id: str, app_version: str, device_type: str, output_path: str) -> None:
        device_type = device_type.replace(' ', '').lower()
        resp = requests.get(f"https://services.garmin.com/appsLibraryBusinessServices_v0/rest/apps/{app_id}/versions/{app_version}/binaries/{device_type}")
        if resp.status_code != 200:
            raise Exception(f"Failed to download app {resp.url}: {resp.text}")
        with open(output_path, "wb") as f:
            f.write(resp.content)
