import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class NotificationStatusTracker:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.status_prefix = "notification_status:"
        self.ttl = 7 * 24 * 3600  # 7 days
    
    def track_notification(self, notification_id: str, user_id: int, 
                          notification_type: str, status: str = "queued"):
        """Track a notification status"""
        try:
            status_data = {
                "notification_id": notification_id,
                "user_id": user_id,
                "type": notification_type,
                "status": status,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            key = f"{self.status_prefix}{notification_id}"
            self.redis.setex(key, self.ttl, json.dumps(status_data))
            
            logger.info(f"Tracked notification {notification_id} with status: {status}")
            
        except Exception as e:
            logger.error(f"Failed to track notification {notification_id}: {e}")
    
    def update_status(self, notification_id: str, status: str, 
                     error_message: Optional[str] = None):
        """Update notification status"""
        try:
            key = f"{self.status_prefix}{notification_id}"
            existing_data = self.redis.get(key)
            
            if existing_data:
                status_data = json.loads(existing_data)
                status_data["status"] = status
                status_data["updated_at"] = datetime.utcnow().isoformat()
                
                if error_message:
                    status_data["error_message"] = error_message
                
                self.redis.setex(key, self.ttl, json.dumps(status_data))
                logger.info(f"Updated notification {notification_id} status to: {status}")
            else:
                logger.warning(f"Notification {notification_id} not found for status update")
                
        except Exception as e:
            logger.error(f"Failed to update notification {notification_id} status: {e}")
    
    def get_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Get notification status"""
        try:
            key = f"{self.status_prefix}{notification_id}"
            data = self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get notification {notification_id} status: {e}")
            return None
    
    def get_user_notifications(self, user_id: int, limit: int = 50) -> list:
        """Get recent notifications for a user"""
        try:
            # This is a simple implementation - in production you'd want indexed queries
            pattern = f"{self.status_prefix}*"
            keys = self.redis.keys(pattern)
            
            user_notifications = []
            for key in keys:
                data = self.redis.get(key)
                if data:
                    notification = json.loads(data)
                    if notification.get("user_id") == user_id:
                        user_notifications.append(notification)
            
            # Sort by created_at descending
            user_notifications.sort(
                key=lambda x: x.get("created_at", ""), 
                reverse=True
            )
            
            return user_notifications[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            return []