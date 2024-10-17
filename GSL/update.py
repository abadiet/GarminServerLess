from .ciq import CIQ
from .app import App
import requests
from enum import Enum
import hashlib
import os
import tempfile


class Update:
    class Type(Enum):
        pass


class Update:

    class Type(Enum):
        # Where is "HuntingAudio"? I am not sure of the types
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
        def get(type_str: str) -> Update.Type:
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

    def __init__(self, **kwargs):
        raise Exception("This is an abstract class")

    def process(self, **kwargs) -> str:
        raise Exception("This is an abstract method")


class FirmwareUpdate(Update):
    class ChangeSeverity(Enum):
        pass
    class Type(Enum):
        pass


class FirmwareUpdate(Update):

    class ChangeSeverity(Enum):
        UNSPECIFIED = 0
        CRITICAL = 1
        RECOMMENDED = 2
        OPTIONAL = 3

    def __init__(
            self,
            url_is_relative: bool,
            url: str,
            unit_filepath: str,
            changes: list = None,
            display_name: str = None,
            eula_url: str = None,
            is_recommended: bool = None,
            md5: str = None,
            size: int = None,
            is_restart_required: bool = None,
            part_number: str = None,
            major: int = None,
            minor: int = None,
            is_primary_firmware: bool = None,
            locale: str = None,
            change_severity: FirmwareUpdate.ChangeSeverity = None,
            is_reinstall: bool = None,
            type: Update.Type = None,
            installation_order: int = None
        ):
        self.changes = changes
        self.name = display_name
        self.eula_url = eula_url
        self.unit_filepath = unit_filepath
        self.is_recommended = is_recommended
        self.url = url
        self.md5 = md5
        self.size = size
        self.url_is_relative = url_is_relative
        self.is_restart_required = is_restart_required
        self.part_number = part_number
        self.major = major
        self.minor = minor
        self.is_primary_firmware = is_primary_firmware
        self.locale = locale
        self.change_severity = change_severity
        self.is_reinstall = is_reinstall    # if Id already there, force reinstall
        self.update_type = type
        if self.update_type != Update.Type.PrimaryFirmware and self.update_type != Update.Type.Firmware:
            raise Exception(f"Invalid firmware update type {self.type}")
        self.installation_order = installation_order


    def process(self, device_rootpath: str) -> str:
        if self.url_is_relative:
            raise Exception("Relative URLs are not supported for firmware updates")
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download the firmware update {self.name}:\n{resp.text}")
        if self.size is not None and self.size != len(resp.content):
            raise Exception(f"Failed to download the firmware update {self.name}: size does not match")
        if self.md5 is not None and self.md5 != hashlib.md5(resp.content).hexdigest():
            raise Exception(f"Failed to download the firmware update {self.name}: MD5 does not match")
        filepath = os.path.join(device_rootpath, self.unit_filepath)
        with open(filepath, "wb") as f:
            f.write(resp.content)

        # TODO: Update the xml file

        return filepath


class AppUpdate(Update):
    class Permission(Enum):
        pass


class AppUpdate(Update):

    class Permission(Enum):

        NonePermision = 0
        Positioning = 1
        Steps = 2
        Sensor = 4
        Fit = 8
        Communications = 0x10
        UserProfile = 0x20
        PersistedLocations = 0x40
        SensorHistory = 0x80
        FitContributor = 0x100
        PersistedContent = 0x200
        Background = 0x400
        Ant = 0x800
        PushNotification = 0x1000
        SensorLogging = 0x2000
        BluetoothLowEnergy = 0x4000
        DataFieldAlert = 0x8000
        ComplicationPublisher = 0x10000
        ComplicationSubscriber = 0x20000

        @staticmethod
        def get(permission_str: str) -> AppUpdate.Permission:
            match permission_str:
                case "None":
                    return AppUpdate.Permission.NonePermision
                case "Positioning":
                    return AppUpdate.Permission.Positioning
                case "Steps":
                    return AppUpdate.Permission.Steps
                case "Sensor":
                    return AppUpdate.Permission.Sensor
                case "Fit":
                    return AppUpdate.Permission.Fit
                case "Communications":
                    return AppUpdate.Permission.Communications
                case "UserProfile":
                    return AppUpdate.Permission.UserProfile
                case "PersistedLocations":
                    return AppUpdate.Permission.PersistedLocations
                case "SensorHistory":
                    return AppUpdate.Permission.SensorHistory
                case "FitContributor":
                    return AppUpdate.Permission.FitContributor
                case "PersistedContent":
                    return AppUpdate.Permission.PersistedContent
                case "Background":
                    return AppUpdate.Permission.Background
                case "Ant":
                    return AppUpdate.Permission.Ant
                case "PushNotification":
                    return AppUpdate.Permission.PushNotification
                case "SensorLogging":
                    return AppUpdate.Permission.SensorLogging
                case "BluetoothLowEnergy":
                    return AppUpdate.Permission.BluetoothLowEnergy
                case "DataFieldAlert":
                    return AppUpdate.Permission.DataFieldAlert
                case "ComplicationPublisher":
                    return AppUpdate.Permission.ComplicationPublisher
                case "ComplicationSubscriber":
                    return AppUpdate.Permission.ComplicationSubscriber
                case _:
                    raise Exception(f"Invalid permission: {permission_str}")

    def __init__(
            self,
            app_guid: str,
            unit_filepath: str,
            developer_name: str = None,
            name: str = None,
            type: App.Type = None,
            size: int = None,
            version_int: int = None,
            version_name: str = None,
            has_permissions_changed: bool = None,
            permissions: list = None,
            has_settings: bool = None,
            min_version_firmware: str = None,
            max_version_firmware: str = None
        ):
        self.app_guid = app_guid
        self.developer_name = developer_name
        self.name = name
        self.app_type = type
        self.size = size
        self.version_int = version_int
        self.version_name = version_name
        self.has_permissions_changed = has_permissions_changed
        self.permissions = permissions
        self.has_settings = has_settings
        self.min_version_firmware = min_version_firmware
        self.max_version_firmware = max_version_firmware
        self.unit_filepath = unit_filepath
        self.update_type = Update.Type.Application

    def process(self, device_rootpath, device_url_name, session_cookie) -> str:
        # retrieve the version guid
        version_guid = CIQ.get_last_app_version_guid(self.app_guid, session_cookie) # TODO: we want the version_int intead of the last version

        # download the app to a temporary file
        tmp = tempfile.NamedTemporaryFile()
        CIQ.download_app(self.app_guid, version_guid, device_url_name, tmp.name)
        if self.size is not None and self.size + 520 != os.path.getsize(tmp.name):  # TODO: why 520 bits bigger?!?
            raise Exception(f"Failed to download the application {self.name}: size does not match. This is an interesting error, please report it on GitHub (https://github.com/abadiet/GarminServerLess)")

        # move the temporary file to the device
        filepath = os.path.join(device_rootpath, self.unit_filepath)
        if os.path.exists(filepath):
            os.remove(filepath)
        try:
            with open(filepath, "wb") as f:
                f.write(tmp.read())
        except Exception as e:
            raise Exception(f"Failed to write the application {self.name} to the device: {e}")
        tmp.close()

        # TODO: Update the xml file

        return filepath
