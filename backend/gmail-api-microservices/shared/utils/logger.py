# filepath: /gmail-api-microservices/gmail-api-microservices/shared/utils/logger.py
import logging
import os

def setup_logger(service_name: str):
    """Setup logger for microservice"""
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        f'%(asctime)s - {service_name} - %(levelname)s - %(message)s'
    )
    
    # Add formatter to console handler
    ch.setFormatter(formatter)
    
    # Add console handler to logger
    if not logger.handlers:
        logger.addHandler(ch)
    
    return logger