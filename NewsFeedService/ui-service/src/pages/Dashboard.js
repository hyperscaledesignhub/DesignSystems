import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Typography,
  Box,
  Button,
  Alert,
  CircularProgress,
  AppBar,
  Toolbar,
  IconButton,
  Badge,
  Menu,
  MenuItem,
  Divider
} from '@mui/material';
import {
  Logout as LogoutIcon,
  Notifications as NotificationsIcon,
  Refresh as RefreshIcon,
  People as PeopleIcon
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';
import { feedAPI, notificationAPI, postAPI } from '../services/api';
import CreatePost from '../components/CreatePost';
import PostCard from '../components/PostCard';
import FriendsPanel from '../components/FriendsPanel';
import NotificationPanel from '../components/NotificationPanel';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [posts, setPosts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [notificationAnchor, setNotificationAnchor] = useState(null);
  const [showFriends, setShowFriends] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const loadFeed = async () => {
    if (!user) return;
    
    try {
      const response = await feedAPI.getUserFeed(user.user_id, { limit: 20 });
      setPosts(response.data.posts || []);
    } catch (error) {
      console.error('Failed to load feed:', error);
      setError('Failed to load your news feed');
    }
  };

  const loadNotifications = async () => {
    if (!user) return;
    
    try {
      const response = await notificationAPI.getUserNotifications(user.user_id, { limit: 10 });
      setNotifications(response.data || []);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  const refreshFeed = async () => {
    if (!user) return;
    
    setRefreshing(true);
    try {
      await feedAPI.refreshFeed(user.user_id);
      await loadFeed();
    } catch (error) {
      console.error('Failed to refresh feed:', error);
      setError('Failed to refresh feed');
    } finally {
      setRefreshing(false);
    }
  };

  const handleDeletePost = async (postId) => {
    try {
      await postAPI.deletePost(postId);
      setPosts(posts.filter(post => post.id !== postId));
    } catch (error) {
      console.error('Failed to delete post:', error);
      setError('Failed to delete post');
    }
  };

  const handlePostCreated = () => {
    setTimeout(() => {
      loadFeed();
    }, 1000); // Give fanout service time to distribute
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([loadFeed(), loadNotifications()]);
      setLoading(false);
    };
    
    if (user) {
      init();
    }
  }, [user]);

  const unreadNotifications = notifications.filter(n => !n.is_read).length;

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            News Feed System
          </Typography>
          
          <Box display="flex" alignItems="center" gap={1}>
            <IconButton
              color="inherit"
              onClick={() => setShowNotifications(!showNotifications)}
            >
              <Badge badgeContent={unreadNotifications} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
            
            <IconButton
              color="inherit"
              onClick={() => setShowFriends(!showFriends)}
            >
              <PeopleIcon />
            </IconButton>
            
            <IconButton color="inherit" onClick={refreshFeed} disabled={refreshing}>
              <RefreshIcon />
            </IconButton>
            
            <Typography variant="body1" sx={{ ml: 2, mr: 1 }}>
              {user?.username} (ID: {user?.user_id})
            </Typography>
            
            <IconButton color="inherit" onClick={logout}>
              <LogoutIcon />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 3 }}>
        <Grid container spacing={3}>
          {/* Friends Panel */}
          {showFriends && (
            <Grid item xs={12} md={3}>
              <FriendsPanel />
            </Grid>
          )}

          {/* Main Feed */}
          <Grid item xs={12} md={showFriends && showNotifications ? 6 : showFriends || showNotifications ? 9 : 12}>
            <Box>
              <Typography variant="h4" gutterBottom>
                Your News Feed
              </Typography>

              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

              <CreatePost onPostCreated={handlePostCreated} />

              {refreshing && (
                <Box display="flex" justifyContent="center" mb={2}>
                  <CircularProgress />
                </Box>
              )}

              {posts.length === 0 ? (
                <Alert severity="info">
                  No posts in your feed yet. Add some friends or refresh your feed!
                </Alert>
              ) : (
                posts.map((post) => (
                  <PostCard
                    key={post.id}
                    post={post}
                    onDelete={handleDeletePost}
                  />
                ))
              )}
            </Box>
          </Grid>

          {/* Notifications Panel */}
          {showNotifications && (
            <Grid item xs={12} md={3}>
              <NotificationPanel 
                notifications={notifications}
                onNotificationUpdate={loadNotifications}
              />
            </Grid>
          )}
        </Grid>
      </Container>
    </Box>
  );
};

export default Dashboard;