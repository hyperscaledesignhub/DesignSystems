import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Button,
  Box,
  Chip,
  Divider
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  PersonAdd as PersonAddIcon,
  Article as ArticleIcon,
  CheckCircle as CheckCircleIcon,
  MarkEmailRead as MarkEmailReadIcon
} from '@mui/icons-material';
import { notificationAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const NotificationPanel = ({ notifications, onNotificationUpdate }) => {
  const { user } = useAuth();

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'friend_request':
        return <PersonAddIcon color="primary" />;
      case 'new_post':
        return <ArticleIcon color="info" />;
      default:
        return <NotificationsIcon />;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const markAsRead = async (notificationId) => {
    if (!user) return;
    
    try {
      await notificationAPI.markAsRead(user.user_id, notificationId);
      if (onNotificationUpdate) onNotificationUpdate();
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    if (!user) return;
    
    try {
      await notificationAPI.markAllAsRead(user.user_id);
      if (onNotificationUpdate) onNotificationUpdate();
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Notifications
            {unreadCount > 0 && (
              <Chip
                label={unreadCount}
                size="small"
                color="error"
                sx={{ ml: 1 }}
              />
            )}
          </Typography>
          {unreadCount > 0 && (
            <IconButton size="small" onClick={markAllAsRead} title="Mark all as read">
              <MarkEmailReadIcon />
            </IconButton>
          )}
        </Box>

        {notifications.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No notifications yet
          </Typography>
        ) : (
          <List dense>
            {notifications.map((notification, index) => (
              <React.Fragment key={notification.id}>
                <ListItem
                  sx={{
                    px: 0,
                    backgroundColor: notification.is_read ? 'transparent' : 'action.hover',
                    borderRadius: 1,
                    mb: 0.5
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {getNotificationIcon(notification.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box>
                        <Typography variant="body2">
                          {notification.message}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(notification.created_at)}
                        </Typography>
                      </Box>
                    }
                  />
                  {!notification.is_read && (
                    <IconButton
                      size="small"
                      onClick={() => markAsRead(notification.id)}
                      title="Mark as read"
                    >
                      <CheckCircleIcon fontSize="small" />
                    </IconButton>
                  )}
                </ListItem>
                {index < notifications.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
};

export default NotificationPanel;