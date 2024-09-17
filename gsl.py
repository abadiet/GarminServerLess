import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser


class CIQ:
    _device_types = None
    _devices_name_idx = dict()

    def get_app_guid(ciq_url: str) -> str:
        app_guid = ciq_url.split("/apps/")
        if len(app_guid) < 2:
            raise Exception(f"Invalid CIQ URL: {ciq_url}")
        app_guid = app_guid[1].split("/")[0]
        return app_guid

    def get_last_app_version_guid(app_guid: str, session_cookie: str) -> str:
        resp = requests.post(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_guid}/install?unitId=a", cookies={"session": session_cookie})
        arr = resp.text.split("appVersionId=")
        if len(arr) != 2:
            raise Exception(f"Failed to get app version {resp.url}: {resp.text}")
        return arr[1].split(",")[0]
    
    def get_app_info(app_guid: str) -> str:
        resp = requests.get(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_guid}")
        if resp.status_code != 200:
            raise Exception(f"Failed to get app version {resp.url}: {resp.text}")
        return resp.json()

    def download_app(app_guid: str, app_version_guid: str, device_urlName: str, output_path: str = "app.PRG") -> None:
        resp = requests.get(f"https://services.garmin.com/appsLibraryBusinessServices_v0/rest/apps/{app_guid}/versions/{app_version_guid}/binaries/{device_urlName}")
        if resp.status_code != 200:
            raise Exception(f"Failed to download app {resp.url}: {resp.text}")
        with open(output_path, "wb") as f:
            f.write(resp.content)

    def download_app_settings(app_guid: str, app_version: int, firmware_part_number: str, locale: str = 'en-us', output_path: str = 'settings.SET') -> str:
        # Get the html form
        html_form = requests.get(f"https://apps.garmin.com/{locale}/appSettings2/{app_guid}/versions/{app_version}/devices/{firmware_part_number}/edit")
        if html_form.status_code != 200:
            raise Exception(f"Failed to get the html settigns form {resp.url}: {resp.text}")
        html_form = html_form.text
        html_form = html_form.replace('="//', '="https://').replace('="/', '="https://apps.garmin.com/')
        html_form = html_form.replace('</head>', "<script type='text/javascript'>document.addEventListener('DOMContentLoaded', function() {let btn = document.createElement('button');btn.innerHTML = 'Validate';btn.style.width = '100%';btn.style.backgroundColor = 'lightgreen';btn.style.minHeight = '70px';btn.style.fontSize = 'large';btn.style.fontWeight = 'bold';btn.addEventListener('click', function() {const settings_str = handleFormSubmit();if (settings_str != '' && settings_str !== undefined) {const xhr = new XMLHttpRequest();xhr.open('POST', '/');xhr.addEventListener('load', function() {close();});xhr.send(settings_str);}});document.body.appendChild(btn);});</script></head>")

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html_form.encode())

            def do_POST(self):
                content_length = int(self.headers['Content-Length'])
                settings_string = self.rfile.read(content_length).decode()

                # Get the binaries
                resp = requests.post(
                    f"https://apps.garmin.com/{locale}/appSettings2/{app_guid}/versions/{app_version}/devices/{firmware_part_number}/binary",
                    data=settings_string
                )
                if resp.status_code != 200:
                    raise Exception(f"Failed to retrieve the settings file {resp.url}: {resp.text}")

                # Write the settings file
                with open(output_path, "wb") as f:
                    f.write(resp.content)

                # Send the response to close the window
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")

        server = HTTPServer(('localhost', 8080), Handler)
        webbrowser.open(f"http://localhost:8080")
        server.handle_request() # Open the html form
        server.handle_request() # Get the settings string and then the file
        server.server_close()

    def _load_devices() -> None:
        resp = requests.get("https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/deviceTypes")
        if resp.status_code != 200:
            raise Exception(f"Failed to get the device types {resp.url}: {resp.text}")
        CIQ._device_types = resp.json()

        for i, device in enumerate(CIQ._device_types):
            CIQ._devices_name_idx[device['name']] = i

    def get_devices_info() -> list:
        if CIQ._device_types is None:
            CIQ._load_devices()
        return CIQ._device_types

    def get_devices_names() -> list:
        if CIQ._device_types is None:
            CIQ._load_devices()
        return list(CIQ._devices_name_idx.keys())
    
    def get_device_info(device_name: str) -> dict:
        if CIQ._device_types is None:
            CIQ._load_devices()
        if device_name not in CIQ._devices_name_idx:
            raise Exception(f"Invalid device name: {device_name}")
        return CIQ._device_types[CIQ._devices_name_idx[device_name]]


class App:
    def __init__(self, ciq_url: str = None, app_guid: str = None) -> None:
        self.guid = CIQ.get_app_guid(ciq_url) if ciq_url else app_guid
        if self.guid is None:
            raise Exception("Invalid CIQ URL or app GUID")
        self.latest_version_guid = None
        self.latest_version = None
        self.compatible_devices_ids = None
        self.has_settings = None

    def _load_info(self) -> None:
        info = CIQ.get_app_info(self.guid)
        self.latest_version = info['latestInternalVersion']
        self.compatible_devices_ids = info['compatibleDeviceTypeIds']
        self.has_settings = info["settingsAvailabilityInfo"]["availabilityByDeviceTypeId"]

    def download(self, device_name: str, output_path: str = "app.PRG", session_cookie: str = None) -> None:
        if self.latest_version_guid is None:
            if session_cookie is None:
                raise Exception("Session cookie is required to download the app")
            self.latest_version_guid = CIQ.get_last_app_version_guid(self.guid, session_cookie)
        device = CIQ.get_device_info(device_name)
        if self.compatible_devices_ids is None:
            self._load_info()
        if device["id"] not in self.compatible_devices_ids:
            raise Exception(f"Device {device_name} is not compatible with this app")
        CIQ.download_app(self.guid, self.latest_version_guid, device["urlName"], output_path)

    def download_settings(self, device_name: str, output_path: str = 'settings.SET', locale: str = 'en-us') -> None:
        if self.latest_version is None or self.has_settings is None or self.compatible_devices_ids is None:
            self._load_info()
        if device_name is None:
            raise Exception("Either device name or firmware part number is required to download the settings")
        device = CIQ.get_device_info(device_name)
        if device["id"] not in self.compatible_devices_ids:
            raise Exception(f"Device {device_name} is not compatible with this app")
        if not self.has_settings[device["id"]]:
            raise Exception(f"Settings are not available for device {device_name}")
        CIQ.download_app_settings(self.guid, self.latest_version, device["partNumber"], locale, output_path)
