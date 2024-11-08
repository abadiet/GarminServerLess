from enum import Enum


class Datatype:
    class TransfertDirection(Enum):
        pass


class Datatype:
    """
    A class to represent a datatype with associated files and transfer directions.
    """

    class TransfertDirection(Enum):
        """
        Enum class representing the direction of data transfer.
        """

        InputToUnit = 1,
        OutputFromUnit = 2,
        InputOutput = 3

        @staticmethod
        def get(value: str) -> Datatype.TransfertDirection:
            """
            Converts a string value to a corresponding Datatype.TransfertDirection enum.

            Args:
                value (str): The string representation of the transfer direction.

            Returns:
                direction (Datatype.TransfertDirection): The corresponding enum value.

            Raises:
                ValueError: If the provided value does not match any known transfer direction.
            """

            match value:
                case "InputToUnit":
                    return Datatype.TransfertDirection.InputToUnit
                case "OutputFromUnit":
                    return Datatype.TransfertDirection.OutputFromUnit
                case "InputOutput":
                    return Datatype.TransfertDirection.InputOutput
                case _:
                    raise ValueError(f"Invalid value: {value}")

    class File:
        """
        A class to represent a file type on the device.
        """

        def __init__(
                self,
                path: str,
                identifier: str = None,
                basename: str = None,
                transfert_direction: Datatype.TransfertDirection = None,
                extension: str = None,
                support_backup: bool = None,
                external_path: str = None
            ):
            """
            Initialize a new instance of the File class.

            Args:
                path (str): The file path.
                identifier (str): Identifier for the file.
                basename (str): The base name of the file.
                transfert_direction (Datatype.TransfertDirection, optional): The direction of the transfer.
                extension (str): The file extension.
                support_backup (bool): Indicates if backup is supported.
                external_path (str): The external path.
            """

            self.identifier = identifier
            self.path = path
            self.basename = basename
            self.transfert_direction = transfert_direction
            self.extension = extension
            self.support_backup = support_backup
            self.external_path = external_path
    
    def __init__(self, name: str, files: list):
        """
        Initialize a new instance of the Datatype class.

        Args:
            name (str): The name of the datatype.
            files (list): A list of files associated to the datatype.
        """

        self.name = name
        self.files = files
