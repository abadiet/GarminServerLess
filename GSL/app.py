from .ciq import CIQ
from enum import Enum
import xml.etree.ElementTree as ElementTree


class App:
    class Type(Enum):
        pass


class App:
    _settings_datatype_key = "IQAppsSettingsFile"

    class Type(Enum):

        Unknown = 0
        WatchFace = 1
        WatchApp = 2
        Widget = 3
        DataField = 4
        MusicApp = 5
        Activity = 6

        @staticmethod
        def get(type_str: str) -> App.Type:
            match type_str:
                case "unknown":
                    return App.Type.Unknown
                case "watchface":
                    return App.Type.WatchFace
                case "watchapp":
                    return App.Type.WatchApp
                case "widget":
                    return App.Type.Widget
                case "datafield":
                    return App.Type.DataField
                case "musicapp":
                    return App.Type.MusicApp
                case "activity":
                    return App.Type.Activity
                case _:
                    raise Exception(f"Invalid update type: {type_str}")

        @staticmethod
        def get_datatype_key(type: App.Type) -> str:
            match type:
                case App.Type.WatchFace:
                    return "IQWatchFaces"
                case App.Type.WatchApp:
                    return "IQWatchApps"
                case App.Type.Widget:
                    return "IQWidgets"
                case App.Type.DataField:
                    return "IQDataFields"
                case App.Type.MusicApp:
                    raise NotImplementedError("MusicApp update not implemented")
                case App.Type.Activity:
                    raise NotImplementedError("Activity update not implemented")
                case App.Type.Unknown:
                    raise NotImplementedError("Unknown update not implemented")

    def __init__(
            self,
            ciq_url: str = None,
            ciq_guid: str = None,
            app_guid: str = None,
            type: Type = None,
            version_int: int = None,
            filename: str = None,
            name: str = None,
            force_load_info: bool = False
        ):
        if ciq_url is not None:
            ciq_guid = CIQ.get_app_guid(ciq_url)
        self.guid = ciq_guid
        self.version_guid = None
        self.version_int = version_int
        self.compatible_devices_ids = None
        self.has_settings = None
        self.type = type
        self.filename = filename
        self.name = name
        self.local_guid = app_guid
        if force_load_info:
            self._load_info()

    def _load_info(self) -> None:
        info = CIQ.get_app_info(self.guid)
        self.version_int = info['latestInternalVersion']
        self.compatible_devices_ids = info['compatibleDeviceTypeIds']
        self.has_settings = info["settingsAvailabilityInfo"]["availabilityByDeviceTypeId"]
        self.type = App.Type(int(info["typeId"]))
        self.name = [info_locale["name"] for info_locale in info["appLocalizations"] if info_locale["locale"] == "en"][0]  # Get the english name

    def download(self, device_url_name: str, output_path: str = "app.PRG", session_cookie: str = None) -> None:
        if self.version_guid is None:
            if session_cookie is None:
                raise Exception("Session cookie is required to download the app")
            self.version_guid = CIQ.get_last_app_version_guid(self.guid, session_cookie)
        CIQ.download_app(self.guid, self.version_guid, device_url_name, output_path)

    def download_settings(self, device_part_number: str, output_path: str = 'settings.SET', locale: str = 'en-us') -> None:
        if self.version_int is None or self.has_settings is None or self.compatible_devices_ids is None:
            self._load_info()
        CIQ.download_app_settings(self.guid, self.version_int, device_part_number, locale, output_path)

    def parse_xml(self) -> ElementTree.Element:
        match self.type:
            case App.Type.WatchFace:
                app_type = "watchface"
            case App.Type.WatchApp:
                app_type = "watchapp"
            case App.Type.Widget:
                app_type = "widget"
            case App.Type.DataField:
                app_type = "datafield"
            case App.Type.MusicApp:
                app_type = "audio-content-provider-app"
            case App.Type.Activity:
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
