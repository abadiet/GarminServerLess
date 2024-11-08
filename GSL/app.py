from .ciq import CIQ
from enum import Enum


class App:
    class Type(Enum):
        pass




class App:
    """
    A class to represent a Garmin application.

    Attributes:
        _settings_datatype_key (str): A constant datatype key for the device XML.
    """

    _settings_datatype_key = "IQAppsSettingsFile"

    class Type(Enum):
        """
        An enumeration to represent the type of the application.
        """

        Unknown = 0
        WatchFace = 1
        WatchApp = 2
        Widget = 3
        DataField = 4
        MusicApp = 5
        Activity = 6

        @staticmethod
        def get(type_str: str) -> App.Type:
            """
            Get the App.Type from a string.

            Parameters:
                type_str (str): The string to convert to App.Type.

            Returns:
                type (App.Type): The App.Type corresponding to the string.
            """

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
            """
            Get the datatype key for the device XML.
            
            Parameters:
                type (App.Type): The type of the application.
            
            Returns:
                key (str): The datatype key for the device XML.
            """

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
            version_guid: int = None,
            compatible_devices_ids: int = None,
            has_settings: int = None,
            filename: str = None,
            name: str = None,
            force_load_info: bool = False
        ):
        """
        Initialize the App object.

        Args:
            ciq_url (str): The URL of the Garmin Connect IQ app. Necessary if ciq_guid is not provided.
            ciq_guid (str): The GUID of the Garmin Connect IQ app. Necessary if ciq_url is not provided.
            app_guid (str): The GUID of the app.
            type (App.Type): The type of the app.
            version_int (int): The internal version of the app.
            version_guid (int): The GUID of the version of the app.
            compatible_devices_ids (int): The IDs of the compatible devices.
            has_settings (int): The availability of settings.
            filename (str): The name of the file.
            name (str): The name of the app.
            force_load_info (bool): Whether to load the information from Garmin servers.
        """

        if ciq_url is not None:
            ciq_guid = CIQ.get_app_guid(ciq_url)
        self.guid = ciq_guid
        self.version_guid = version_guid
        self.version_int = version_int
        self.compatible_devices_ids = compatible_devices_ids
        self.has_settings = has_settings
        self.type = type
        self.filename = filename
        self.name = name
        self.local_guid = app_guid
        if force_load_info:
            self._load_info_latest()

    def _load_info_latest(self) -> None:
        """
        Load the information from Garmin servers.
        """

        info = CIQ.get_app_info(self.guid)
        version_int = info['latestInternalVersion']
        compatible_devices_ids = info['compatibleDeviceTypeIds']
        has_settings = info["settingsAvailabilityInfo"]["availabilityByDeviceTypeId"]
        type = App.Type(int(info["typeId"]))
        name = [info_locale["name"] for info_locale in info["appLocalizations"] if info_locale["locale"] == "en"][0]  # Get the english name
        if self.version_int is not None and version_int != self.version_int:
            print (f"[Warning] Version mismatch for app {self.guid}. Expected {self.version_int}, got {version_int}: overriding to {version_int}")
        self.version_int = version_int
        if self.compatible_devices_ids is not None and compatible_devices_ids != self.compatible_devices_ids:
            print (f"[Warning] Version mismatch for app {self.guid}. Expected {self.compatible_devices_ids}, got {compatible_devices_ids}: overriding to {compatible_devices_ids}")
        self.compatible_devices_ids = compatible_devices_ids
        if self.has_settings is not None and has_settings != self.has_settings:
            print (f"[Warning] Version mismatch for app {self.guid}. Expected {self.has_settings}, got {has_settings}: overriding to {has_settings}")
        self.has_settings = has_settings
        if self.type is not None and type != self.type:
            print (f"[Warning] Version mismatch for app {self.guid}. Expected {self.type}, got {type}: overriding to {type}")
        self.type = type
        if self.name is not None and name != self.name:
            print (f"[Warning] Version mismatch for app {self.guid}. Expected {self.name}, got {name}: overriding to {name}")
        self.name = name


    def download(self, device_url_name: str, output_path: str = "app.PRG", session_cookie: str = None) -> None:
        """
        Downloads the app from the specified device URL and saves it to the given output path.

        Args:
            device_url_name (str): The URL name of the device from which to download the app.
            output_path (str): The path where the downloaded app will be saved. Defaults to *app.PRG*.
            session_cookie (str): The session cookie for authentication. Required if version_guid is not set.
        Raises:
            Exception: If session_cookie is not provided and version_guid is None.
        """

        if self.version_guid is None:
            if session_cookie is None:
                raise Exception("Session cookie is required to download the app")
            self.version_guid = CIQ.get_last_app_version_guid(self.guid, session_cookie)
        CIQ.download_app(self.guid, self.version_guid, device_url_name, output_path)

    def download_settings(self, device_part_number: str, output_path: str = 'settings.SET', locale: str = 'en-us') -> None:
        """
        Downloads the settings for a specific device and saves them to a file.

        Args:
            device_part_number (str): The part number of the device for which to download settings.
            output_path (str): The path where the settings file will be saved. Defaults to *settings.SET*.
            locale (str): The locale for the settings. Defaults to *en-us*.

        Raises:
            Exception: If the server returns an error.
        """

        if self.version_int is None or self.has_settings is None or self.compatible_devices_ids is None:
            self._load_info()
        CIQ.download_app_settings(self.guid, self.version_int, device_part_number, locale, output_path)

    def parse_xml(self) -> str:
        """
        Parses the application details into an XML string.

        Returns:
            xml (str): An XML string representing the application details.
        """

        match self.type:
            case App.Type.WatchFace:
                app_type = "watchface"
            case App.Type.WatchApp:
                app_type = "watchapp"  # TODO: found watch-app in this xml: https://openmtbmap.org/GarminDevice.xml
            case App.Type.Widget:
                app_type = "widget"
            case App.Type.DataField:
                app_type = "datafield"  # TODO: found data-field in this xml: https://openmtbmap.org/GarminDevice.xml
            case App.Type.MusicApp:
                app_type = "audio-content-provider-app"
            case App.Type.Activity:
                app_type = "activity"
            case _:
                app_type = "unknown"

        app_xml = f"<App><AppName>{self.name}</AppName><StoreId>{self.guid}</StoreId><AppId>{''}</AppId><AppType>{app_type}</AppType><Version>{self.version_int}</Version><FileName>{self.filename}</FileName></App>"

        return app_xml
