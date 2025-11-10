from logging import getLogger, StreamHandler, Formatter
import logging

# Cache de loggers configurados para evitar duplicados
_configured_loggers = set()

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
    logger.setLevel(logging.DEBUG)
    
    # Evitar que los mensajes se propaguen al logger raíz (que podría duplicarlos)
    logger.propagate = False
    
    # Marcar como configurado
    _configured_loggers.add(name)
    
    return logger


# Default logger instance
logger = get_logger('social')