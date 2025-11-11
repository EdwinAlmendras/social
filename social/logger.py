from logging import getLogger, StreamHandler, Formatter
import logging
import os

# Cache de loggers configurados para evitar duplicados
_configured_loggers = set()

# Variable global para controlar el nivel de logging
_global_log_level = None

def set_log_level(level: int):
    """
    Establece el nivel de logging global para todos los loggers.
    
    Args:
        level: Nivel de logging (logging.DEBUG, logging.INFO, etc.)
    """
    global _global_log_level
    _global_log_level = level
    
    # Actualizar todos los loggers ya configurados
    for logger_name in _configured_loggers:
        existing_logger = getLogger(logger_name)
        existing_logger.setLevel(level)

def get_default_log_level() -> int:
    """
    Obtiene el nivel de logging por defecto basado en variables de entorno.
    
    Returns:
        Nivel de logging apropiado
    """
    # Si ya se estableció un nivel global, usarlo
    if _global_log_level is not None:
        return _global_log_level
    
    # Verificar variable de entorno para desarrollo
    if os.getenv('SOCIAL_DEBUG', '').lower() in ('1', 'true', 'yes'):
        return logging.DEBUG
    
    # Por defecto, nivel INFO (profesional)
    return logging.INFO

def get_logger(name: str):
    """
    Obtiene o crea un logger con configuración estándar.
    Evita duplicar handlers si el logger ya fue configurado.
    """
    logger = getLogger(name)
    
    # Si ya configuramos este logger, solo retornarlo
    if name in _configured_loggers:
        return logger
    
    # Si el logger ya tiene handlers (configurado externamente), no agregar más
    if logger.handlers:
        _configured_loggers.add(name)
        return logger
    
    # Configurar el logger
    handler = StreamHandler()
    handler.setFormatter(Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    
    # Usar el nivel apropiado
    logger.setLevel(get_default_log_level())
    
    # Evitar que los mensajes se propaguen al logger raíz (que podría duplicarlos)
    logger.propagate = False
    
    # Marcar como configurado
    _configured_loggers.add(name)
    
    return logger


# Default logger instance
logger = get_logger('social')