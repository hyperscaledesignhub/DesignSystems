import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Avatar,
  IconButton,
  Chip
} from '@mui/material';
import {
  Person as PersonIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';

const PostCard = ({ post, onDelete }) => {
  const { user } = useAuth();
  const canDelete = user && post.user_id === user.user_id;

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

  const handleDelete = () => {
    if (onDelete && window.confirm('Are you sure you want to delete this post?')) {
      onDelete(post.id);
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center">
            <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
              <PersonIcon />
            </Avatar>
            <Box>
              <Typography variant="subtitle1" fontWeight="bold">
                {post.username}
              </Typography>
              <Box display="flex" alignItems="center">
                <ScheduleIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary">
                  {formatDate(post.created_at)}
                </Typography>
              </Box>
            </Box>
          </Box>
          
          <Box>
            {post.user_id === user?.user_id && (
              <Chip label="You" size="small" color="primary" variant="outlined" sx={{ mr: 1 }} />
            )}
            {canDelete && (
              <IconButton onClick={handleDelete} size="small" color="error">
                <DeleteIcon />
              </IconButton>
            )}
          </Box>
        </Box>

        <Typography variant="body1" sx={{ mt: 2, whiteSpace: 'pre-wrap' }}>
          {post.content}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default PostCard;