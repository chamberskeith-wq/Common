'''
Created on Jan 15, 2026

@author: keith.chambers
'''

#===============================================================================
# Module logger
#===============================================================================
import logging
from os import path
from sympy.printing import str
logger = logging.getLogger(__name__)

# common imports
import yaml 
import os
import keyring
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, asdict, is_dataclass, fields
from typing import TypeVar, Generic, Type, get_type_hints, get_origin, get_args
from types import UnionType
from typing import Union

from .exceptions import ConfigError, ConfigValidationError, ConfigFileError, ConfigSecretError

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
            self.config_path
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
    def load(self) -> T:
        """
        Load configuration from YAML.

        Missing fields use the defaults defined by the
        application configuration dataclass.

        Unknown fields generate a validation error.
        """
        
        config_file = self.config_path
        
        if not config_file.exists():
            raise ConfigError(f"Config file not found: {config_file}")
    
        try:
            with config_file.open("r", encoding="utf-8") as file:
                raw_config = yaml.safe_load(file) or {}  
                
        except yaml.YAMLError as e:
            raise ConfigError("Configuration file is not valid YAML") from e

        except OSError as e:
            raise ConfigError(f"Unable to read config file: {self.config_path}") from e
    
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

# --------------------
# Secrets
# --------------------

SERVICE_NAME = "AskMeApp"
KEY_NAME = "google_api_key"


#===============================================================================
# get_google_api_key
#===============================================================================
def get_google_api_key() -> str | None:
    try:
        key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    except Exception:
        key = None

    return key or os.environ.get("GOOGLE_API_KEY")


#===============================================================================
# set_google_api_key
#===============================================================================
def set_google_api_key(value: str) -> None:
    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, value)
    except Exception as e:
        raise ConfigError("Failed to store Google API key in keyring") from e


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
        Convert YAML values into supported Python types.

        Handles Enum, Path and Optional/Union annotations.
        """

        if value is None:
            return None

        origin = get_origin(expected_type)
        args = get_args(expected_type)

        # Handle Optional and Union types.
        if origin in (Union, UnionType):

            for arg in args:
                if arg is type(None):
                    continue

                try:
                    return self._coerce_value(value, arg)
                except (TypeError, ValueError):
                    continue

            raise ConfigValidationError(
                f"Cannot convert value {value!r} "
                f"to {expected_type}"
            )

        # Handle Enum values.
        if isinstance(expected_type, type) and issubclass(
            expected_type, Enum
        ):
            if isinstance(value, expected_type):
                return value

            return expected_type(value)

        # Handle filesystem paths.
        if expected_type is Path:
            return Path(value)

        return value

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


