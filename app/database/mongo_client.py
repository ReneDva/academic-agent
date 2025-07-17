import logging
import time
import pytz
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure, OperationFailure
from bson.errors import InvalidId
from app.config import Config

if TYPE_CHECKING:
    from app.utils.logging import AppLogger


class MongoManager:
    """
    Handles MongoDB operations for PDF records and logs.
    """

    def __init__(self, config: Config, app_logger: "AppLogger"):
        self.config = config
        self.app_logger = app_logger
        self.client = None
        self.db = None
        self._connect()

    def _connect(self):
        """
        Initializes MongoDB connection and verifies connectivity.
        """
        try:
            self.client = MongoClient(self.config.MONGODB_URL)
            self.db = self.client[self.config.MONGODB_DATABASE]
            self.db.command('ping')  # Quick connection check
            self.app_logger.log_app_event('info', "Connected to MongoDB successfully.")
        except ConnectionFailure as e:
            self.app_logger.log_app_event('error', f"MongoDB connection failed: {e}", exc_info=True)
            raise
        except PyMongoError as e:
            self.app_logger.log_app_event('error', f"MongoDB error during connection: {e}", exc_info=True)
            raise
        except Exception as e:
            self.app_logger.log_app_event('error', f"Unexpected error during MongoDB connection: {e}", exc_info=True)
            raise

    def insert_record_by_type(self, record_type: str, data: Dict[str, Any]) -> str:
        """
        Inserts a record into the appropriate MongoDB collection based on the record type.

        Args:
            record_type (str): The type of record to insert ('QUERY' or 'PDF').
            data (Dict[str, Any]): The record data to be stored.

        Returns:
            str: MongoDB document ID of the inserted record.

        Raises:
            ValueError: If record_type is not supported.
            PyMongoError: If the insertion fails.
        """
        record_type = record_type.upper()
        if record_type not in {'QUERY', 'PDF'}:
            raise ValueError(f"Unsupported record type: {record_type}. Must be 'QUERY' or 'PDF'.")

        # Ensure timestamp field is present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()

        try:
            # Determine target collection
            if record_type == 'QUERY':
                collection_name = self.config.MONGODB_QUERY_COLLECTION
            else:  # PDF
                collection_name = self.config.MONGODB_PDF_COLLECTION

            result = self.db[collection_name].insert_one(data)

            # Log to console (only) based on type
            if record_type == 'PDF':
                self.app_logger.log_app_event('info', f"Inserted PDF record ID: {result.inserted_id}")
            else:
                self.app_logger.log_app_event('debug', f"Inserted QUERY log ID: {result.inserted_id}")

            return str(result.inserted_id)

        except PyMongoError as e:
            self.app_logger.log_app_event('error', f"Insert failed for type '{record_type}': {e}", exc_info=True)
            raise

    def get_latest_pdf_record(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the most recent processed PDF record.
        """
        try:
            latest_record = self.db[self.config.MONGODB_PDF_COLLECTION].find_one(
                filter={'processed_in_chroma': True},
                sort=[('upload_time', -1)]
            )
            if latest_record:
                latest_record['_id'] = str(latest_record['_id'])
                self.app_logger.log_app_event('info', f"Latest PDF record: {latest_record.get('filename')}")
                return latest_record
            else:
                self.app_logger.log_app_event('info', "No processed PDF records found.")
                return None
        except PyMongoError as e:
            self.app_logger.log_app_event('error', f"Failed to fetch latest PDF record: {e}", exc_info=True)
            raise

    def update_pdf_processed_status(self, record_id: str, status: bool, chroma_chunk_ids: List[str]):
        """
        Updates processing status and chunk IDs for a PDF record.
        """
        try:
            self.db[self.config.MONGODB_PDF_COLLECTION].update_one(
                {'_id': ObjectId(record_id)},
                {'$set': {
                    'processed_in_chroma': status,
                    'chroma_chunk_ids': chroma_chunk_ids
                }}
            )
            self.app_logger.log_app_event('info', f"Updated status for PDF ID: {record_id}")
        except PyMongoError as e:
            self.app_logger.log_app_event('error', f"Failed to update PDF status: {e}", exc_info=True)
            raise

    def update_log_field(self, log_id, update_data):
        """
        Updates fields in a log document by its MongoDB ID.
        :param log_id: ObjectId or string of the log document
        :param update_data: Dictionary of fields to update
        """
        self.db[self.config.MONGODB_QUERY_COLLECTION].update_one(
            {'_id': ObjectId(log_id)},
            {'$set': update_data}
        )

    def get_log_records_by_collection(
            self,
            log_type: str,
            query_filter: Optional[Dict[str, Any]] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Unified method for retrieving log records from MongoDB based on log type.
        Replaces get_pdf_records() and get_query_records() by using log_type ('PDF' or 'QUERY').

        Args:
            log_type (str): Type of collection to fetch from ('PDF' or 'QUERY').
            query_filter (Optional[Dict[str, Any]]): MongoDB query filter (default: all records).
            limit (int): Maximum number of records to return (default: 100).

        Returns:
            List[Dict[str, Any]]: Sorted log records by descending timestamp.
        """
        log_type_upper = log_type.upper()
        if log_type_upper not in {'PDF', 'QUERY'}:
            raise ValueError(f"Unsupported log type: {log_type}")

        # Map type to config collection name
        if log_type_upper == 'PDF':
            collection_name = self.config.MONGODB_PDF_COLLECTION
            sort_field = 'upload_time'
        else:
            collection_name = self.config.MONGODB_QUERY_COLLECTION
            sort_field = 'timestamp'

        try:
            records = list(
                self.db[collection_name]
                .find(query_filter or {})
                .sort(sort_field, -1)
                .limit(limit)
            )

            self.app_logger.log_app_event('info', f"Fetched {len(records)} records from '{collection_name}'")
            return records

        except Exception as e:
            self.app_logger.log_app_event('error', f"Failed to fetch records from '{collection_name}': {e}",
                                          exc_info=True)
            return []

    def get_pdf_record_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific PDF record by MongoDB ID.
        """
        try:
            try:
                obj_id = ObjectId(record_id)
                query = {"_id": obj_id}
            except Exception:
                query = {"_id": record_id}

            pdf_record = self.db[self.config.MONGODB_PDF_COLLECTION].find_one(query)

            if pdf_record:
                self.app_logger.log_app_event('info', f"Retrieved PDF record ID: {record_id}")
            else:
                self.app_logger.log_app_event('warning', f"PDF record not found (ID: {record_id})")
                return None

            return pdf_record

        except Exception as e:
            self.app_logger.log_app_event('error', f"Error fetching PDF record by ID: {e}", exc_info=True)
            return None

    def drop_collection_by_type(self, log_type: str):
        """
        Drops the specified collection from MongoDB based on type ('PDF' or 'QUERY').

        Args:
            log_type (str): Type of collection to drop.

        Raises:
            ValueError: If log_type is invalid.
            PyMongoError: If drop fails.
        """
        log_type_upper = log_type.upper()
        if log_type_upper == 'PDF':
            collection_name = self.config.MONGODB_PDF_COLLECTION
        elif log_type_upper == 'QUERY':
            collection_name = self.config.MONGODB_QUERY_COLLECTION
        else:
            raise ValueError(f"Unsupported log type: {log_type}")

        try:
            self.db.drop_collection(collection_name)
            self.app_logger.log_app_event('info', f"Dropped collection: {collection_name}")
        except PyMongoError as e:
            self.app_logger.log_app_event('error',
                                          f"Drop failed for collection '{collection_name}': {e}", exc_info=True)
            raise

