'''
Created on Jan 15, 2026

@author: keith.chambers
'''

#===============================================================================
# Module logger
#===============================================================================
import logging
logger = logging.getLogger(__name__)

# common imports
import yaml 
from enum import Enum
from pathlib import Path
from dataclasses import asdict, is_dataclass, fields
from typing import TypeVar, Generic, Type, get_type_hints, get_origin, get_args
from types import UnionType
from typing import Union

from .exceptions import ConfigError, ConfigValidationError, ConfigFileError

# create a generic type variable
T = TypeVar("T")

#===============================================================================
# # Application configuration manager
#===============================================================================
class ConfigManager(Generic[T]):
    """
    Generic configuration manager.

    The application supplies its configuration dataclass and
    configuration file location.

    The manager handles:
        - Configuration creation
        - Configuration loading
        - Configuration saving
        - Configuration validation
        - Configuration file management
    """
 
    #===============================================================================
    # constructor
    #===============================================================================
    def __init__(
        self,
        config_type: Type[T],
        config_file_name: str,
        config_file_path: str | Path
    ) -> None:
        """
        Initialize the configuration manager.
    
        Args:
            config_type: Application configuration dataclass.
            config_file_name: Configuration filename.
            config_file_path: Directory containing the configuration file.
    
        Raises:
            ConfigValidationError: Invalid constructor arguments.
            ConfigFileError: Unable to resolve configuration path.
        """

        # Validate configuration type
        if not is_dataclass(config_type) or isinstance(config_type, type) is False:
            raise ConfigValidationError(
                "Configuration type must be a dataclass"
            )
        if not config_file_name:
            raise ConfigValidationError(
                "Configuration filename cannot be empty"
            )
        
        if (
            not isinstance(config_file_name, str)
            or not config_file_name.strip()
            or config_file_name in (".", "..")
        ):
            raise ConfigValidationError(
                "A valid configuration filename is required"
            )           
        
        if config_file_path is None:
            raise ConfigValidationError(
                "Configuration directory must be provided"
            ) 

        
        try:
            # Convert directory to Path
            directory = Path(config_file_path).expanduser()
    
            # Combine directory and filename
            self.config_file = directory / config_file_name
    
            # Resolve the full path
            self.config_file = self.config_file.resolve()
    
        except (TypeError, ValueError, OSError) as e:
            raise ConfigFileError(
                "Unable to construct configuration file path"
            ) from e
    
        self.config_type = config_type
    
        logger.debug(
            "Configuration manager initialized: %s",
            self.config_file
        )
    
    #===============================================================================
    # create
    #===============================================================================
    def create(self) -> T:
        """
        Create a configuration object using application defaults.
        """
        
        try:
            config = self.config_type()

        except TypeError as e:
            raise ConfigValidationError(
                "Unable to create default configuration"
            ) from e

        self.validate(config)
        
        return config
    
    #===============================================================================
    # load
    #===============================================================================
    def load(self, create_if_missing: bool = False) -> T:
        """
        Load configuration from YAML.

        Missing fields use the defaults defined by the
        application configuration dataclass.

        Unknown fields generate a validation error.
        """
        
        config_file = self.config_file
        
        if not config_file.exists():
            if create_if_missing:
                config = self.create()
                self.save(config)
                return config
        
            raise ConfigFileError(
                f"Config file not found: {config_file}"
            )           
            
        try:
            with config_file.open("r", encoding="utf-8") as file:
                raw_config = yaml.safe_load(file)
            
            if raw_config is None:
                raw_config = {}      
                
        except yaml.YAMLError as e:
            raise ConfigFileError("Configuration file is not valid YAML") from e

        except OSError as e:
            raise ConfigFileError(f"Unable to read config file: {self.config_file}") from e
    
        if not isinstance(raw_config, dict):
            raise ConfigValidationError(
                "Configuration file must contain a YAML mapping"
            )


        config = self._create_config(raw_config)    
        
        logger.info(
            "Configuration loaded: %s",
            self.config_file
        )

        return config
            
    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------
    def save(self, config: T) -> None:
        """
        Save configuration to YAML.
        """

        self.validate(config)

        try:
            self.config_file.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            config_values = self._serialize(config)

            temp_file = self.config_file.with_name(
                self.config_file.name + ".tmp"
            )

            try:
                with temp_file.open(
                    "w",
                    encoding="utf-8"
                ) as file:

                    yaml.safe_dump(
                        config_values,
                        file,
                        sort_keys=False,
                        allow_unicode=True
                    )

                temp_file.replace(self.config_file)

            finally:
                if temp_file.exists():
                    temp_file.unlink()

        except (OSError, yaml.YAMLError) as e:
            raise ConfigFileError(
                f"Unable to save configuration: {self.config_file}"
            ) from e

        logger.info(
            "Configuration saved: %s",
            self.config_file
        )

 
    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------
    def validate(self, config: T) -> None:
        """
        Validate a configuration object.

        Application-specific validation is performed by the
        configuration object's own validate() method.
        """

        if not isinstance(config, self.config_type):
            raise ConfigValidationError(
                f"Expected {self.config_type.__name__}, "
                f"received {type(config).__name__}"
            )

        validator = getattr(config, "validate", None)

        if not callable(validator):
            raise ConfigValidationError(
                "Configuration object must implement validate()"
            )

        validator()

    # --------------------------------------------------------
    # Exists
    # --------------------------------------------------------

    def exists(self) -> bool:
        """
        Check whether the configuration file exists.
        """

        return self.config_file.is_file()


    # ========================================================
    # Internal helper methods
    # ========================================================

    # --------------------------------------------------------
    # Create configuration object from dictionary
    # --------------------------------------------------------

    def _create_config(self, raw_config: dict) -> T:
        """
        Construct an application configuration object.

        Missing values use dataclass defaults.
        Unknown fields are rejected.
        """

        valid_fields = {
            field.name
            for field in fields(self.config_type)
            if field.init
        }

        unknown_fields = set(raw_config) - valid_fields

        if unknown_fields:
            raise ConfigValidationError(
                f"Unknown configuration fields: "
                f"{', '.join(sorted(unknown_fields))}"
            )

        try:
            # Instantiate defaults first. This also preserves
            # default objects such as nested dataclasses.
            defaults = self.config_type()

            config_values = {
                field.name: getattr(defaults, field.name)
                for field in fields(self.config_type)
                if field.init
            }

            # Apply values loaded from YAML.
            config_values.update(raw_config)

            # Convert YAML values to supported Python types.
            type_hints = get_type_hints(self.config_type)

            for name, value in config_values.items():

                if name in type_hints:
                    config_values[name] = self._coerce_value(
                        value,
                        type_hints[name]
                    )

            config = self.config_type(**config_values)

        except ConfigError:
            raise

        except (TypeError, ValueError) as e:
            raise ConfigValidationError(
                f"Unable to construct configuration: {e}"
            ) from e

        self.validate(config)

        return config

    # --------------------------------------------------------
    # Convert values to Python types
    # --------------------------------------------------------


    def _coerce_value(self, value, expected_type):
        """
        Convert YAML values into the Python types specified
        by the application configuration dataclass.
    
        Supported types:
            - str, int, float, bool
            - Path
            - Enum
            - Optional and Union
            - list, tuple, set, frozenset
            - dict
            - Nested dataclasses
    
        Raises:
            ConfigValidationError: Value cannot be converted
                                   to the expected type.
        """
    
        # --------------------------------------------------------
        # None values
        # --------------------------------------------------------
    
        if value is None:
    
            if expected_type is type(None):
                return None
    
            origin = get_origin(expected_type)
            args = get_args(expected_type)
    
            if origin in (Union, UnionType) and type(None) in args:
                return None
    
            raise ConfigValidationError(
                f"None is not valid for {expected_type}"
            )
    
        # --------------------------------------------------------
        # Resolve generic type information
        # --------------------------------------------------------
    
        origin = get_origin(expected_type)
        args = get_args(expected_type)
    
        # --------------------------------------------------------
        # Optional and Union
        # --------------------------------------------------------
    
        if origin in (Union, UnionType):
    
            errors = []
    
            for arg in args:
    
                if arg is type(None):
                    continue
    
                try:
                    return self._coerce_value(value, arg)
    
                except (TypeError, ValueError, ConfigError) as e:
                    errors.append(str(e))
    
            raise ConfigValidationError(
                f"Cannot convert {value!r} to {expected_type}. "
                f"Conversion errors: {'; '.join(errors)}"
            )
    
        # --------------------------------------------------------
        # List
        # --------------------------------------------------------
    
        if origin is list:
    
            if not isinstance(value, (list, tuple)):
                raise ConfigValidationError(
                    f"Expected a list for {expected_type}"
                )
    
            item_type = args[0] if args else object
    
            return [
                self._coerce_value(item, item_type)
                for item in value
            ]
    
        # --------------------------------------------------------
        # Tuple
        # --------------------------------------------------------
    
        if origin is tuple:
    
            if not isinstance(value, (list, tuple)):
                raise ConfigValidationError(
                    f"Expected a sequence for {expected_type}"
                )
    
            # Handle tuple[T, ...]
            if len(args) == 2 and args[1] is Ellipsis:
    
                return tuple(
                    self._coerce_value(item, args[0])
                    for item in value
                )
    
            # Handle tuple[T1, T2, ...]
            if args:
    
                if len(value) != len(args):
                    raise ConfigValidationError(
                        f"Expected {len(args)} tuple values, "
                        f"received {len(value)}"
                    )
    
                return tuple(
                    self._coerce_value(item, item_type)
                    for item, item_type in zip(value, args)
                )
    
            return tuple(value)
    
        # --------------------------------------------------------
        # Set and Frozenset
        # --------------------------------------------------------
    
        if origin in (set, frozenset):
    
            if not isinstance(value, (list, tuple, set, frozenset)):
                raise ConfigValidationError(
                    f"Expected a collection for {expected_type}"
                )
    
            item_type = args[0] if args else object
    
            converted = (
                self._coerce_value(item, item_type)
                for item in value
            )
    
            return origin(converted)
    
        # --------------------------------------------------------
        # Dictionary
        # --------------------------------------------------------
    
        if origin is dict:
    
            if not isinstance(value, dict):
                raise ConfigValidationError(
                    f"Expected a dictionary for {expected_type}"
                )
    
            key_type = args[0] if args else object
            value_type = args[1] if args else object
    
            return {
                self._coerce_value(key, key_type):
                self._coerce_value(item, value_type)
                for key, item in value.items()
            }
    
        # --------------------------------------------------------
        # Nested dataclasses
        # --------------------------------------------------------
    
        if isinstance(expected_type, type) and is_dataclass(expected_type):
    
            if isinstance(value, expected_type):
                return value
    
            if not isinstance(value, dict):
                raise ConfigValidationError(
                    f"Expected a mapping for {expected_type.__name__}"
                )
    
            nested_config = self._create_config_for_type(
                value,
                expected_type
            )
    
            return nested_config
    
        # --------------------------------------------------------
        # Enum
        # --------------------------------------------------------
    
        if isinstance(expected_type, type) and issubclass(
            expected_type, Enum
        ):
    
            if isinstance(value, expected_type):
                return value
    
            try:
                return expected_type(value)
    
            except ValueError as e:
                raise ConfigValidationError(
                    f"Invalid value {value!r} for "
                    f"enum {expected_type.__name__}"
                ) from e
    
        # --------------------------------------------------------
        # Path
        # --------------------------------------------------------
    
        if expected_type is Path:
    
            try:
                return Path(value)
    
            except (TypeError, ValueError) as e:
                raise ConfigValidationError(
                    f"Invalid path value: {value!r}"
                ) from e
    
        # --------------------------------------------------------
        # String
        # --------------------------------------------------------
    
        if expected_type is str:
    
            if isinstance(value, str):
                return value
    
            if isinstance(value, (int, float, bool)):
                return str(value)
    
            raise ConfigValidationError(
                f"Cannot convert {type(value).__name__} to str"
            )
    
        # --------------------------------------------------------
        # Boolean
        # --------------------------------------------------------
    
        if expected_type is bool:
    
            if isinstance(value, bool):
                return value
    
            if isinstance(value, str):
    
                normalized = value.strip().lower()
    
                if normalized in ("true", "yes", "1", "on"):
                    return True
    
                if normalized in ("false", "no", "0", "off"):
                    return False
    
            raise ConfigValidationError(
                f"Cannot convert {value!r} to bool"
            )
    
        # --------------------------------------------------------
        # Integer
        # --------------------------------------------------------
    
        if expected_type is int:
    
            if isinstance(value, bool):
                raise ConfigValidationError(
                    "Boolean values cannot be converted to integers"
                )
    
            try:
                if isinstance(value, float) and not value.is_integer():
                    raise ValueError("Non-integral float")
    
                return int(value)
    
            except (TypeError, ValueError, OverflowError) as e:
                raise ConfigValidationError(
                    f"Cannot convert {value!r} to int"
                ) from e
    
        # --------------------------------------------------------
        # Float
        # --------------------------------------------------------
    
        if expected_type is float:
    
            if isinstance(value, bool):
                raise ConfigValidationError(
                    "Boolean values cannot be converted to floats"
                )
    
            try:
                return float(value)
    
            except (TypeError, ValueError, OverflowError) as e:
                raise ConfigValidationError(
                    f"Cannot convert {value!r} to float"
                ) from e
    
        # --------------------------------------------------------
        # Other types
        # --------------------------------------------------------
    
        if expected_type is object:
            return value
    
        if isinstance(expected_type, type) and isinstance(value, expected_type):
            return value
    
        raise ConfigValidationError(
            f"Unsupported conversion: {type(value).__name__} "
            f"to {expected_type}"
        )
    # --------------------------------------------------------
    # Serialize configuration
    # --------------------------------------------------------

    def _serialize(self, config):
        """
        Convert configuration values into YAML-compatible values.

        Handles dataclasses, Enum, Path and nested collections.
        """

        if is_dataclass(config) and not isinstance(config, type):
            return self._serialize(asdict(config))

        if isinstance(config, Enum):
            return config.value

        if isinstance(config, Path):
            return str(config)

        if isinstance(config, dict):
            return {
                key: self._serialize(value)
                for key, value in config.items()
            }

        if isinstance(config, (list, tuple)):
            return [
                self._serialize(value)
                for value in config
            ]

        if config is None or isinstance(
            config, (str, int, float, bool)
        ):
            return config

        raise ConfigValidationError(
            f"Unsupported configuration value type: "
            f"{type(config).__name__}"
        )


