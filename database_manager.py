import sqlite3
import os
import shutil
import datetime
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    filename='data/database.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DatabaseManager:
    def __init__(self, db_path='data/targets.db'):
        self.db_path = db_path
        self.backup_dir = 'data/backups'
        self.log_dir = 'data/logs'
        
        # Ensure directories exist
        Path('data').mkdir(exist_ok=True)
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def create_backup(self):
        """Create a timestamped backup of the database"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(self.backup_dir, f'targets_backup_{timestamp}.db')
            
            # Create backup only if source database exists
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, backup_path)
                logging.info(f'Database backup created: {backup_path}')
                
                # Clean up old backups (keep last 5)
                self._cleanup_old_backups()
            else:
                logging.warning(f'Source database not found at {self.db_path}')
                
        except Exception as e:
            logging.error(f'Backup creation failed: {str(e)}')
            raise

    def _cleanup_old_backups(self, keep_last_n=5):
        """Keep only the n most recent backups"""
        try:
            backups = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith('targets_backup_')],
                reverse=True
            )
            
            for old_backup in backups[keep_last_n:]:
                os.remove(os.path.join(self.backup_dir, old_backup))
                logging.info(f'Removed old backup: {old_backup}')
                
        except Exception as e:
            logging.error(f'Backup cleanup failed: {str(e)}')

    def log_database_change(self, operation, details):
        """Log database operations with detailed information"""
        try:
            logging.info(f'Database {operation}: {details}')
        except Exception as e:
            logging.error(f'Failed to log database change: {str(e)}')

    def verify_database_integrity(self):
        """Verify the integrity of the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            if result == 'ok':
                logging.info('Database integrity check passed')
                return True
            else:
                logging.error(f'Database integrity check failed: {result}')
                return False
                
        except Exception as e:
            logging.error(f'Database integrity check failed: {str(e)}')
            return False
        finally:
            conn.close()

# Create a global instance
db_manager = DatabaseManager()
