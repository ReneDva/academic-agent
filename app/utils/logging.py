import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.database.mongo_client import MongoManager

class AppLogger:
    """
    Handles structured logging to console and MongoDB.
    Supports QUERY and PDF logs into dedicated collections, with console-only APP logs.
    Singleton pattern ensures a single instance.
    """
    _instance = None
    _initialized = False
    db_manager: Optional["MongoManager"] = None

    def __new__(cls, db_manager: Optional["MongoManager"] = None):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_manager: Optional["MongoManager"] = None):
        if not self._initialized:
            if db_manager is not None:
                self.db_manager = db_manager

            self.logger = logging.getLogger('app_console_logger')
            self.logger.setLevel(logging.INFO)

            if not self.logger.handlers:
                ch = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                ch.setFormatter(formatter)
                self.logger.addHandler(ch)

            self._initialized = True
            self.logger.info("AppLogger (console) instance initialized.")

    def set_db_manager(self, db_manager: "MongoManager"):
        if self.db_manager is not None and db_manager is not self.db_manager:
            self.logger.warning("Replacing existing MongoManager in AppLogger.")
        self.db_manager = db_manager
        self.logger.info("MongoManager assigned. MongoDB logging is now active.")

    def log_app_event(self, level: str, message: str, exc_info: bool = False,
                      extra_data: Optional[Dict[str, Any]] = None):
        """
        Logs to console at the specified level with optional metadata.
        """
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_message = message
        if extra_data:
            log_message += f" - Data: {extra_data}"
        log_method(log_message, exc_info=exc_info)

    def log_to_mongodb(self, log_type: str, data: Dict[str, Any]):
        """
        Logs structured data to MongoDB, restricted to QUERY and PDF log types.
        APP logs are excluded from persistence (printed to console only).
        """
        log_type_upper = log_type.upper()
        if log_type_upper == "APP":
            self.log_app_event("info", f"[APP LOG] {data.get('message', '')} - Data: {data}")
            return None

        if self.db_manager is None:
            self.log_app_event("error", "MongoDB manager not initialized.")
            return None

        if log_type_upper not in {"QUERY", "PDF"}:
            self.log_app_event("error", f"Invalid MongoDB log type: {log_type_upper}")
            return None

        log_record = {
            "type": log_type_upper,
            "timestamp": datetime.utcnow(),
            **data
        }

        #cleaned_record = LoggingUtils.clean_log_data(log_record)

        try:
            # Uses MongoManager method that inserts to correct collection
            mongo_id = self.db_manager.insert_record_by_type(log_type_upper, log_record)
            self.logger.info(f"Inserted {log_type_upper} log with ID: {mongo_id}")
            return mongo_id
        except Exception as e:
            self.logger.error(f"MongoDB log insertion failed: {e}", exc_info=True)
            return None

    def get_mongodb_logs(self, log_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Returns logs for a specific type (QUERY or PDF) from the correct collection.
        """
        if self.db_manager is None:
            self.log_app_event('error', "MongoDB manager not set.")
            return []

        log_type_upper = log_type.upper()
        if log_type_upper not in {"QUERY", "PDF"}:
            self.log_app_event('error', f"Invalid log type requested: {log_type_upper}")
            return []

        try:
            logs = self.db_manager.get_log_records_by_collection(log_type_upper, limit=limit)
            self.logger.info(f"Retrieved {len(logs)} '{log_type_upper}' logs from MongoDB.")
            return logs
        except Exception as e:
            self.logger.error(f"Error fetching logs for type '{log_type_upper}': {e}", exc_info=True)
            return []


# class LoggingUtils:
#     @staticmethod
#     def clean_log_data(log_data: Dict[str, Any]) -> Dict[str, Any]:
#         """
#         Cleans a log dictionary from null/empty values recursively.
#         Preserves 'confidence_score' even if None.
#         """
#         def _clean(obj):
#             if isinstance(obj, dict):
#                 return {
#                     k: _clean(v)
#                     for k, v in obj.items()
#                     if (v is not None and v != '' and v != [] and v != {}) or k == "confidence_score"
#                 }
#             elif isinstance(obj, list):
#                 return [_clean(item) for item in obj if item not in (None, '', [], {})]
#             else:
#                 return obj
#
#         return _clean(log_data)
