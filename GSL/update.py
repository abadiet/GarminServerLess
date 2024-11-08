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
    """
    The Update class represents an abstract base class for different types of updates.
    """

    class Type(Enum):
        """
        Enum representing different types of updates.
        """

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
            """
            Converts a string representation of an update type to its corresponding Update.Type enum.

            Args:
                type_str (str): The string representation of the update type.

            Returns:
                type (Update.Type): The corresponding Update.Type enum value.

            Raises:
                Exception: If the provided type_str does not match any known update type.
            """

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
        """
        This is an abstract class and cannot be instantiated directly.

        Raises:
            Exception: Always raises an exception indicating that this is an abstract class.
        """

        raise Exception("This is an abstract class")

    def process(self, **kwargs) -> str:
        """
        This is an abstract method that should be implemented by subclasses.

        Raises:
            Exception: Always raises an exception indicating that this method is abstract.
        """

        raise Exception("This is an abstract method")


class FirmwareUpdate(Update):
    class ChangeSeverity(Enum):
        pass
    class Type(Enum):
        pass


class FirmwareUpdate(Update):
    """
    A class to represent a firmware update.
    """

    class ChangeSeverity(Enum):
        """
        Enum representing the severity of the update.
        """

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
        """
        Initialize a FirmwareUpdate object.

        Args:
            url_is_relative (bool): Indicates if the URL is relative.
            url (str): The URL for the update.
            unit_filepath (str): The path on the unit where to save the update.
            changes (list): A list of changes.
            display_name (str): The display name of the update.
            eula_url (str): The URL for the EULA.
            is_recommended (bool): Indicates if the update is recommended.
            md5 (str): The MD5 checksum of the update.
            size (int): The size of the update.
            is_restart_required (bool): Indicates if a restart is required.
            part_number (str): The part number of the update.
            major (int): The major version number.
            minor (int): The minor version number.
            is_primary_firmware (bool): Indicates if this is for the primary firmware.
            locale (str): The locale for the update.
            change_severity (FirmwareUpdate.ChangeSeverity): The severity of the change.
            is_reinstall (bool): Indicates if the update should be reinstalled.
            type (Update.Type): The type of the update.
            installation_order (int): The installation order of the update.

        Raises:
            Exception: If the update type is not PrimaryFirmware or Firmware.
        """

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
        """
        Downloads and verifies a firmware update, then saves it to the specified device root path.

        Args:
            device_rootpath (str): The root path of the device.

        Returns:
            path (str): The file path where the firmware update was saved.

        Raises:
            Exception: If the URL is relative.
            Exception: If the firmware update download fails (non-200 status code).
            Exception: If the downloaded firmware size does not match the expected size.
            Exception: If the downloaded firmware MD5 checksum does not match the expected checksum.
        """

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

        return filepath


class AppUpdate(Update):
    class Permission(Enum):
        pass


class AppUpdate(Update):
    """
    A class to represent an application update.
    """

    class Permission(Enum):
        """
        Enum representing the permissions of the update.
        """

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
            """
            Converts a permission string to the corresponding AppUpdate.Permission enum value.

            Args:
                permission_str (str): The permission string to convert.

            Returns:
                permission (AppUpdate.Permission): The corresponding AppUpdate.Permission enum value.

            Raises:
                Exception: If the permission string does not match any known permission.
            """

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
        """
        Initialize the application update object.

        Args:
            app_guid (str): The unique identifier for the app.
            unit_filepath (str): The file path on the unit where to save the update.
            developer_name (str): The name of the developer.
            name (str): The name of the app.
            type (App.Type): The type of the app.
            size (int): The size of the app.
            version_int (int): The integer representation of the app version.
            version_name (str): The name of the app version.
            has_permissions_changed (bool): Indicates if the permissions have changed.
            permissions (list): The list of permissions required by the app.
            has_settings (bool): Indicates if the app has settings.
            min_version_firmware (str): The minimum firmware version required.
            max_version_firmware (str): The maximum firmware version supported.
        """

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
        """
        Processes the application update.

        Args:
            device_rootpath (str): The root path of the device.
            device_url_name (str): The URL name of the device.
            session_cookie (str): The cookie named *session* when logged in to apps.garmin.com. Can be any Garmin account, even a junk one.

        Returns:
            path (str): The file path where the application was stored on the device.

        Raises:
            Exception: If the application download fails due to size mismatch or if writing to the device fails.
        """

        # retrieve the version guid
        version_guid = CIQ.get_last_app_version_guid(self.app_guid, session_cookie) # TODO: we want the version_int instead of the last version

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

        return filepath
