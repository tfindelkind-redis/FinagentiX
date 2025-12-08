"""Progress tracking with resume capability"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class TickerStatus(Enum):
    """Status of ticker download"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TickerProgress:
    """Track progress for individual ticker"""
    ticker: str
    status: TickerStatus
    attempts: int = 0
    last_attempt: Optional[str] = None
    error_message: Optional[str] = None
    record_count: Optional[int] = None
    file_path: Optional[str] = None
    checksum: Optional[str] = None
    completed_at: Optional[str] = None

class ProgressTracker:
    """Track download progress with resume capability"""
    
    def __init__(self, manifest_path: str, tickers: List[str]):
        self.manifest_path = manifest_path
        self.tickers = tickers
        self.progress: Dict[str, TickerProgress] = {}
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Load existing progress or initialize new"""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                data = json.load(f)
                for ticker_data in data.get('tickers', []):
                    status = TickerStatus(ticker_data['status'])
                    self.progress[ticker_data['ticker']] = TickerProgress(
                        ticker=ticker_data['ticker'],
                        status=status,
                        attempts=ticker_data.get('attempts', 0),
                        last_attempt=ticker_data.get('last_attempt'),
                        error_message=ticker_data.get('error_message'),
                        record_count=ticker_data.get('record_count'),
                        file_path=ticker_data.get('file_path'),
                        checksum=ticker_data.get('checksum'),
                        completed_at=ticker_data.get('completed_at')
                    )
        else:
            # Initialize all tickers as pending
            for ticker in self.tickers:
                self.progress[ticker] = TickerProgress(
                    ticker=ticker,
                    status=TickerStatus.PENDING
                )
            self.save()
    
    def save(self):
        """Persist current progress"""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'total_tickers': len(self.tickers),
            'completed': len(self.get_completed()),
            'failed': len(self.get_failed()),
            'pending': len(self.get_pending()),
            'tickers': [
                {
                    **asdict(p),
                    'status': p.status.value
                }
                for p in self.progress.values()
            ]
        }
        with open(self.manifest_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def mark_in_progress(self, ticker: str):
        """Mark ticker as currently being processed"""
        self.progress[ticker].status = TickerStatus.IN_PROGRESS
        self.progress[ticker].attempts += 1
        self.progress[ticker].last_attempt = datetime.now().isoformat()
        self.save()
    
    def mark_completed(self, ticker: str, record_count: int, 
                       file_path: str, checksum: str):
        """Mark ticker as successfully completed"""
        self.progress[ticker].status = TickerStatus.COMPLETED
        self.progress[ticker].record_count = record_count
        self.progress[ticker].file_path = file_path
        self.progress[ticker].checksum = checksum
        self.progress[ticker].completed_at = datetime.now().isoformat()
        self.progress[ticker].error_message = None
        self.save()
    
    def mark_failed(self, ticker: str, error: str):
        """Mark ticker as failed"""
        self.progress[ticker].status = TickerStatus.FAILED
        self.progress[ticker].error_message = error
        self.save()
    
    def get_pending(self) -> List[str]:
        """Get list of pending tickers"""
        return [
            t for t, p in self.progress.items()
            if p.status == TickerStatus.PENDING
        ]
    
    def get_completed(self) -> List[str]:
        """Get list of completed tickers"""
        return [
            t for t, p in self.progress.items()
            if p.status == TickerStatus.COMPLETED
        ]
    
    def get_failed(self) -> List[str]:
        """Get list of failed tickers"""
        return [
            t for t, p in self.progress.items()
            if p.status == TickerStatus.FAILED
        ]
    
    def should_retry(self, ticker: str, max_retries: int) -> bool:
        """Check if ticker should be retried"""
        p = self.progress[ticker]
        return (p.status == TickerStatus.FAILED and 
                p.attempts < max_retries)
    
    def get_summary(self) -> Dict:
        """Get progress summary"""
        total = len(self.tickers)
        completed = len(self.get_completed())
        return {
            'total': total,
            'completed': completed,
            'failed': len(self.get_failed()),
            'pending': len(self.get_pending()),
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }
