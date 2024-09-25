from .ciq import CIQ
from .device import Device
from enum import Enum
import xml.etree.ElementTree as ElementTree


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
