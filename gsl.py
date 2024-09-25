import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser
from enum import Enum
import xml.etree.ElementTree as ElementTree
import hashlib
import os
import re

class CIQ:
    @staticmethod
    def get_app_guid(ciq_url: str) -> str:
        app_guid = ciq_url.split("/apps/")
        if len(app_guid) < 2:
            raise Exception(f"Invalid CIQ URL: {ciq_url}")
        app_guid = app_guid[1].split("/")[0]
        return app_guid

    @staticmethod
    def get_last_app_version_guid(app_guid: str, session_cookie: str) -> str:
        resp = requests.post(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_guid}/install?unitId=a", cookies={"session": session_cookie})
        arr = resp.text.split("appVersionId=")
        if len(arr) != 2:
            raise Exception(f"Failed to get app version {resp.url}: {resp.text}")
        return arr[1].split(",")[0]
    
    @staticmethod
    def get_app_info(app_guid: str) -> str:
        resp = requests.get(f"https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/apps/{app_guid}")
        if resp.status_code != 200:
            raise Exception(f"Failed to get app version {resp.url}: {resp.text}")
        return resp.json()

    @staticmethod
    def download_app(app_guid: str, app_version_guid: str, device_urlName: str, output_path: str = "app.PRG") -> None:
        resp = requests.get(f"https://services.garmin.com/appsLibraryBusinessServices_v0/rest/apps/{app_guid}/versions/{app_version_guid}/binaries/{device_urlName}")
        if resp.status_code != 200:
            raise Exception(f"Failed to download app {resp.url}: {resp.text}")
        with open(output_path, "wb") as f:
            f.write(resp.content)

    @staticmethod
    def download_app_settings(app_guid: str, app_version: int, firmware_part_number: str, locale: str = 'en-us', output_path: str = 'settings.SET') -> str:
        # Get the html form
        html_form = requests.get(f"https://apps.garmin.com/{locale}/appSettings2/{app_guid}/versions/{app_version}/devices/{firmware_part_number}/edit")
        if html_form.status_code != 200:
            raise Exception(f"Failed to get the html settigns form {html_form.url}: {html_form.text}")
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
                settings_string = self.rfile.read(content_length)

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


class App:

    class Type(Enum):
        UNKNOWN = 0
        WATCHFACE = 1
        WATCHAPP = 2
        WIDGET = 3
        DATAFIELD = 4
        MUSICAPP = 5
        ACTIVITY = 6

        @staticmethod
        def get(type_str: str):
            match type_str:
                case "watchface":
                    return App.Type.WATCHFACE
                case "watchapp":
                    return App.Type.WATCHAPP
                case "widget":
                    return App.Type.WIDGET
                case "datafield":
                    return App.Type.DATAFIELD
                case "audio-content-provider-app":
                    return App.Type.MUSICAPP
                case "activity":
                    return App.Type.ACTIVITY
                case _:
                    return App.Type.UNKNOWN

    def __init__(self, ciq_url: str = None, ciq_guid: str = None, type: Type = None, version_int: int = None, filename: str = None, name: str = None):
        self.guid = CIQ.get_app_guid(ciq_url) if ciq_url else ciq_guid
        if self.guid is None:
            raise Exception("Invalid CIQ URL or CIQ GUID")
        self.version_guid = None
        self.version_int = version_int
        self.compatible_devices_ids = None
        self.has_settings = None
        self.type = type
        self.filename = filename
        self.name = name

    def _load_info(self) -> None:
        info = CIQ.get_app_info(self.guid)
        self.version_int = info['latestInternalVersion']
        self.compatible_devices_ids = info['compatibleDeviceTypeIds']
        self.has_settings = info["settingsAvailabilityInfo"]["availabilityByDeviceTypeId"]
        self.type = App.Type(int(info["typeId"]))
        self.name = [info_locale["name"] for info_locale in info["appLocalizations"] if info_locale["locale"] == "en"][0]  # Get the english name

    def download(self, device_name: str = None, device_url_name: str = None, output_path: str = "app.PRG", session_cookie: str = None) -> None:
        if self.version_guid is None:
            if session_cookie is None:
                raise Exception("Session cookie is required to download the app")
            self.version_guid = CIQ.get_last_app_version_guid(self.guid, session_cookie)
        if device_name is None and device_url_name is None:
            raise Exception("Device name or device url name is required to download the app")
        if device_name is not None:
            device = Device.get_device_info(device_name)
            if self.compatible_devices_ids is None:
                self._load_info()
            if device["id"] not in self.compatible_devices_ids:
                raise Exception(f"Device {device_name} is not compatible with this app")
            device_url_name = device["urlName"]
        CIQ.download_app(self.guid, self.version_guid, device_url_name, output_path)

    def download_settings(self, device_name: str = None, device_part_number: str = None, output_path: str = 'settings.SET', locale: str = 'en-us') -> None:
        if self.version_int is None or self.has_settings is None or self.compatible_devices_ids is None:
            self._load_info()
        if device_name is None and device_part_number is None:
            raise Exception("Device name or device part number is required to download the settings")
        if device_name is not None:
            device = Device.get_device_info(device_name)
            if device["id"] not in self.compatible_devices_ids:
                raise Exception(f"Device {device_name} is not compatible with this app")
            if not self.has_settings[device["id"]]:
                raise Exception(f"Settings are not available for device {device_name}")
            device_part_number = device["partNumber"]
        CIQ.download_app_settings(self.guid, self.version_int, device_part_number, locale, output_path)

    def parse_xml(self) -> ElementTree.Element:
        match self.type:
            case App.Type.WATCHFACE:
                app_type = "watchface"
            case App.Type.WATCHAPP:
                app_type = "watchapp"
            case App.Type.WIDGET:
                app_type = "widget"
            case App.Type.DATAFIELD:
                app_type = "datafield"
            case App.Type.MUSICAPP:
                app_type = "audio-content-provider-app"
            case App.Type.ACTIVITY:
                app_type = "activity"
            case _:
                app_type = "unknown"

        app_xml = ElementTree.Element("App")
        ElementTree.SubElement(app_xml, "AppName").text = self.name
        ElementTree.SubElement(app_xml, "StoreId").text = self.guid
        ElementTree.SubElement(app_xml, "AppId").text = ""
        ElementTree.SubElement(app_xml, "AppType").text = app_type
        ElementTree.SubElement(app_xml, "Version").text = str(self.version_int)
        ElementTree.SubElement(app_xml, "FileName").text = self.filename

        return app_xml


class Update:
    class ChangeSeverity(Enum):
        UNSPECIFIED = 0
        CRITICAL = 1
        RECOMMENDED = 2
        OPTIONAL = 3

    class Type(Enum):
        PrimaryFirmware = 0
        Firmware = 1
        Map = 2
        Garage  = 3
        Computer = 4
        LanguagePack = 5
        ConnectItem = 6
        Application = 7
        SafetyCamera = 8
        MarineChart = 9
        GeneralDlc = 10

        @staticmethod
        def get(type_str: str):
            match type_str:
                case "PrimaryFirmware":
                    return Update.Type.PrimaryFirmware
                case "Firmware":
                    return Update.Type.Firmware
                case "Map":
                    return Update.Type.Map
                case "Garage":
                    return Update.Type.Garage
                case "Computer":
                    return Update.Type.Computer
                case "LanguagePack":
                    return Update.Type.LanguagePack
                case "ConnectItem":
                    return Update.Type.ConnectItem
                case "Application":
                    return Update.Type.Application
                case "SafetyCamera":
                    return Update.Type.SafetyCamera
                case "MarineChart":
                    return Update.Type.MarineChart
                case "GeneralDlc":
                    return Update.Type.GeneralDlc
                case _:
                    raise Exception(f"Invalid update type: {type_str}")

    def __init__(self, changes: list = None, display_name: str = None, eula_url: str = None, unit_filepath: str = None, is_recommended: bool = None, url: str = None, md5: str = None, size: int = None, url_is_relative: bool = None, is_restart_required: bool = None, part_number: str = None, version: str = None, is_primary_firmware: bool = None, locale: str = None, change_severity: ChangeSeverity = None, is_reinstall: bool = None, type: Type = None):
        self.changes = changes
        self.display_name = display_name
        self.eula_url = eula_url
        self.unit_filepath = unit_filepath
        self.is_recommended = is_recommended
        self.url = url
        self.md5 = md5
        self.size = size
        self.url_is_relative = url_is_relative
        self.is_restart_required = is_restart_required
        self.part_number = part_number
        self.version = version
        self.is_primary_firmware = is_primary_firmware
        self.locale = locale
        self.change_severity = change_severity
        self.is_reinstall = is_reinstall
        self.type = type

    def process(self, device_path: str) -> str:
        if self.url_is_relative:
            raise Exception("Relative URLs are not supported")
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download the update {self.name}: {resp.text}")
        if self.size != len(resp.content):
            raise Exception(f"Failed to download the update {self.name}: size does not match")
        if self.md5 != hashlib.md5(resp.content).hexdigest():
            raise Exception(f"Failed to download the update {self.name}: MD5 does not match")
        filepath = os.path.join(device_path, self.unit_filepath)
        with open(filepath, "wb") as f:
            f.write(resp.content)

        # TODO: Update the xml file

        return filepath


class Device:
    _types = None
    _names_idx = dict()
    _part_numbers_idx = dict()

    @staticmethod
    def _load_devices() -> None:
        resp = requests.get("https://apps.garmin.com/api/appsLibraryExternalServices/api/asw/deviceTypes")
        if resp.status_code != 200:
            raise Exception(f"Failed to get the device types {resp.url}: {resp.text}")
        Device._types = resp.json()

        for i, device in enumerate(Device._types):
            Device._names_idx[device['name']] = i
            Device._part_numbers_idx[device['partNumber']] = i

    @staticmethod
    def get_devices_info() -> list:
        if Device._types is None:
            Device._load_devices()
        return Device._types

    @staticmethod
    def get_devices_names() -> list:
        if Device._types is None:
            Device._load_devices()
        return list(Device._names_idx.keys())

    @staticmethod
    def get_devices_part_numbers() -> list:
        if Device._types is None:
            Device._load_devices()
        return list(Device._part_numbers_idx.keys())

    @staticmethod
    def get_device_info(name: str = None, part_number: str = None) -> dict:
        if name is not None:
            if name not in Device.get_devices_names():
                raise Exception(f"Invalid device name: {name}")
            return Device.get_devices_info()[Device._names_idx[name]]
        if part_number is not None:
            if part_number not in Device.get_devices_part_numbers():
                raise Exception(f"Invalid device part number: {part_number}")
            return Device.get_devices_info()[Device._part_numbers_idx[part_number]]
        raise Exception("Either device name or part number is required")

    def __init__(self, device_path: str):
        self.device_path = device_path
        self.xml_filepath = os.path.join(device_path, "GARMIN/GarminDevice.xml")
        with open(self.xml_filepath, "r") as f:
            self.xml_raw = f.read()
        self.xml = ElementTree.parse(self.xml_filepath)
        self.part_number = self.xml.getroot().find('{*}Model').find('{*}PartNumber').text
        self.max_nb_apps = int(self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}MaxApps').text)
        self.apps = [
            App(name=app_xml.find('{*}AppName').text, ciq_guid=app_xml.find('{*}StoreId').text, version_int=int(app_xml.find('{*}Version').text), filename=app_xml.find('{*}FileName').text, type=App.Type.get(app_xml.find('{*}AppType').text))
            for app_xml in self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}Apps')    
        ]
        info = Device.get_device_info(part_number=self.part_number)
        self.name = info["name"]
        self.url_name = info["urlName"]
        self.additional_names = info["additionalNames"]
        self.image_url = info["imageUrl"]
        self.updates = None

    def get_updates(self, force_reload: bool = False) -> list:
        if self.updates is not None and not force_reload:
            return self.updates

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        json = {
            "ClientInfo": {
                "ClientType": "web",
                "LocaleCode": "en-US",
                "OperatingSystemType": "WINDOWS",
                "OperatingSystemVersion": "AppVersion { Version = 4}"
            },
            "GarminDeviceXml": self.xml_raw,        # TODO: use only part of the xml to keep privacy
            "IsUserInteractive": True
        }
        resp = requests.post("https://omt.garmin.com/Rce/ProtobufApi/SoftwareUpdateService/GetAllUnitSoftwareUpdates", headers=headers, json=json)
        if resp.status_code != 200:
            raise Exception(f"Failed to get the updates {resp.url}: {resp.text}")

        resp = resp.json()
        self.updates = []
        for update_json in resp["SoftwareUpdateOptions"]:
            update = Update(update_json["Changes"], update_json["DisplayName"], update_json["EulaUrl"], update_json["FilePathOnUnit"].replace('\\', '/'), update_json["IsRecommended"], update_json["Url"]["Url"], update_json["Url"]["Md5"], update_json["Url"]["Size"], update_json["Url"]["IsRelative"], update_json["IsRestartRequired"], update_json["PartNumber"], update_json["SoftwareVersion"], update_json["IsPrimaryFirmware"], update_json["Locale"], update_json["ChangeSeverity"], update_json["IsReinstall"], Update.Type.get(update_json["DataType"]))
            self.updates.append(update)

        return self.updates

    def get_updates_names(self) -> list:
        return [update.name for update in self.get_updates()]

    def update(self, update_id: int = None, update_name: str = None) -> list:
        if self.updates is None:
            self.get_updates()
        if update_name is not None:
            if update_name not in self.get_updates_names():
                raise Exception(f"Invalid update name: {update_name}")
            for i, update in enumerate(self.updates):
                if update.name == update_name:
                    return [self.updates.pop(i).process(self.device_path)]
        if update_id is not None:
            if update_id >= len(self.updates):
                raise Exception(f"Invalid update id: {update_id}")
            return [self.updates.pop(update_id).process(self.device_path)]
        paths = []
        for update in self.updates:
            paths.append(update.process(self.device_path))
        self.updates = []
        return paths

    def install(self, session_cookie: str, app: App = None, locale: str = 'en-us', **kwargs) -> None:
        if len(self.apps) >= self.max_nb_apps:
            raise Exception("The maximum number of apps is already installed")
        if app is None:
            app = App(**kwargs)
        if app.guid in [app.guid for app in self.apps]:
            raise Exception("The app is already installed")
        app_filepath = os.path.join(self.device_path, f"GARMIN/APPS/{app.guid}.PRG")
        set_filepath = os.path.join(self.device_path, f"GARMIN/APPS/SETTINGS/{app.guid}.SET")
        app.filename = f'{app.guid}.PRG'
        app.download(device_url_name=self.url_name, output_path=app_filepath, session_cookie=session_cookie)
        app.download_settings(device_part_number=self.part_number, output_path=set_filepath, locale=locale)
        app_xml = app.parse_xml()
        self.xml.getroot().find('{*}Extensions').find('{*}IQAppExt').find('{*}Apps').append(app_xml)
        xml_str = ElementTree.tostring(self.xml.getroot(), encoding='unicode', method='xml')
        xml_str = re.sub(r"ns\d+:", "", xml_str)
        with open(self.xml_filepath, "w") as f:
            f.write(xml_str)
        self.apps.append(app)
        # TODO: What are doing 'AppSpace', 'AppId' and RSA keys in the xml file?
