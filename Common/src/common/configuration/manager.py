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
from pathlib import Path
from dataclasses import dataclass, asdict, is_dataclass
from typing import TypeVar, Generic, Type

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
        config_path: str,
        config_file: str | Path
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
            directory = Path(config_path).expanduser()
    
            # Combine directory and filename
            self.config_path = directory / config_file
    
            # Resolve the full path
            self.config_path = self.config_path.resolve()
    
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
    # load_config
    #===============================================================================
    def load(self) -> T:
        """
        Load configuration from YAML.

        Missing fields use the defaults defined by the
        application configuration dataclass.

        Unknown fields generate a validation error.
        """
        
        config_path = self.config_path
        
        if not self.config_path.exists():
            raise ConfigError(f"Config file not found: {self.config_path}")
    
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError("Configuration file is not valid YAML") from e
        except OSError as e:
            raise ConfigError(f"Unable to read config file: {self.config_path}") from e
    
        try:
            config = create()    
                # Existing YAL files remain compatible; use the default if absent.
                prompt_instructions=raw.get("PROMPT_INSTRUCTIONS", DEFAULT_PROMPT_INSTRUCTIONS),
            )
        except KeyError as e:
            raise ConfigError(f"Missing required config key: {e.args[0]}") from e
    
        config.validate()
        return config
            
 
    def validate(self) -> None:
        ''' Doc string '''

        # ---- CHROMA DB NAME ----
        if not isinstance(self.chroma_db, str) or not self.chroma_db.strip():
            raise ConfigError("CHROMA_DB must be a non-empty string")

        invalid_chars = r'<>:"/\\|?*'
        if any(c in self.chroma_db for c in invalid_chars):
            raise ConfigError(
                f"CHROMA_DB contains invalid filesystem characters: {invalid_chars}"
            )

        # ---- CHROMA DB PATH ----
        if not isinstance(self.chroma_db_path, str) or not self.chroma_db_path.strip():
            raise ConfigError("CHROMA_DB_PATH must be a non-empty string")

        path = Path(self.chroma_db_path).expanduser()

        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ConfigError(f"Cannot create/access CHROMA_DB_PATH: {path}") from e

        if not path.is_dir():
            raise ConfigError(f"CHROMA_DB_PATH is not a directory: {path}")

        self.chroma_db_path = str(path)

        # ---- DEFAULT LLM ----
        if not isinstance(self.default_llm, LLM_types):
            raise ConfigError("DEFAULT_LLM must be a valid LLM_types enum value")

                # ---- PROMPT INSTRUCTIONS ----
        if not isinstance(self.prompt_instructions, str) or not self.prompt_instructions.strip():
            raise ConfigError("PROMPT_INSTRUCTIONS must be a non-empty string")


    def update(
        self,
        *,
        chroma_db: str,
        chroma_db_path: str,
        default_llm: LLM_types,
        prompt_instructions: str | None = None,
    ) -> None:

        self.chroma_db = chroma_db
        self.chroma_db_path = chroma_db_path
        self.default_llm = default_llm
        if prompt_instructions is not None:
            self.prompt_instructions = prompt_instructions  

        self.validate()


# # --------------------
# # Persistence
# # --------------------

#===============================================================================
# load_config
#===============================================================================
def load_config(config_file_name: str , config_file_path: str) -> AppConfig:
    ''' Doc string '''
    config_path = Path(config_file_path) / config_file_name

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError("Configuration file is not valid YAML") from e
    except OSError as e:
        raise ConfigError(f"Unable to read config file: {config_path}") from e

    try:
        config = AppConfig(
            chroma_db=raw["CHROMA_DB"],
            chroma_db_path=raw["CHROMA_DB_PATH"],
            default_llm=LLM_types(raw["DEFAULT_LLM"]),

            # Existing YAML files remain compatible; use the default if absent.
            prompt_instructions=raw.get("PROMPT_INSTRUCTIONS", DEFAULT_PROMPT_INSTRUCTIONS),
        )
    except KeyError as e:
        raise ConfigError(f"Missing required config key: {e.args[0]}") from e

    config.validate()
    return config


#===============================================================================
# save_config
#===============================================================================
def save_config(config: AppConfig) -> None:
    config_path = Path(CONFIG_FILE_PATH) / CONFIG_FILE_NAME
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {
                    "CHROMA_DB": config.chroma_db,
                    "CHROMA_DB_PATH": config.chroma_db_path,
                    "DEFAULT_LLM": config.default_llm.value,
                    "PROMPT_INSTRUCTIONS": config.prompt_instructions,
                },
                f,
            )
    except OSError as e:
        raise ConfigError("Failed to save configuration file") from e


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

