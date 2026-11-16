'''
Created on Nov 13, 2026

@author: keith.chambers
'''
#===============================================================================
# Base Config Error object
#===============================================================================
class ConfigError(Exception):
    """Base exception for all configuration service errors
    Args:
        Exception (Exception): The configuration exception
    
    Returns:
        None
    
    Raises:
         None
    """    

    pass

#===============================================================================
# Config File Error object
#===============================================================================

class ConfigFileError(ConfigError):
    """Configuration file read/write errors.
    Args:
        Exception (Exception): The configuration exception
    
    Returns:
        None
    
    Raises:
         None
    """    

    pass



#===============================================================================
# Config Validation Error object
#===============================================================================
class ConfigValidationError(ConfigError):
    """Configuration validation errors.
    Args:
        Exception (Exception): The configuration exception
    
    Returns:
        None
    
    Raises:
         None
    """    

    pass


#===============================================================================
# Config secrets Error object
#===============================================================================

class ConfigSecretError(ConfigError):
    """Configuration secret management errors.
    Args:
        Exception (Exception): The configuration exception
    
    Returns:
        None
    
    Raises:
         None
    """    

    pass
