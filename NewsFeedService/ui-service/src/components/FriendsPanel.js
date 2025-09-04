import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
  TextField,
  Box,
  Alert,
  CircularProgress,
  Divider,
  Avatar
} from '@mui/material';
import {
  PersonAdd as PersonAddIcon,
  PersonRemove as PersonRemoveIcon,
  Person as PersonIcon
} from '@mui/icons-material';
import { useAuth } from '../hooks/useAuth';
import { graphAPI, userAPI } from '../services/api';

const FriendsPanel = () => {
  const { user } = useAuth();
  const [friends, setFriends] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newFriendId, setNewFriendId] = useState('');

  const loadFriends = async () => {
    if (!user) return;
    
    try {
      const response = await graphAPI.getFriends(user.user_id);
      const friendIds = response.data || [];
      
      // Get user details for each friend
      const friendsWithDetails = await Promise.all(
        friendIds.map(async (friendId) => {
          try {
            const userResponse = await userAPI.getUser(friendId);
            return userResponse.data;
          } catch (error) {
            return { id: friendId, username: `User${friendId}` };
          }
        })
      );
      
      setFriends(friendsWithDetails);
    } catch (error) {
      console.error('Failed to load friends:', error);
      setError('Failed to load friends');
    }
  };

  const loadSuggestions = async () => {
    if (!user) return;
    
    try {
      const response = await graphAPI.getFriendSuggestions(user.user_id);
      const suggestionIds = response.data || [];
      
      // Get user details for each suggestion
      const suggestionsWithDetails = await Promise.all(
        suggestionIds.slice(0, 5).map(async (suggestionId) => {
          try {
            const userResponse = await userAPI.getUser(suggestionId);
            return userResponse.data;
          } catch (error) {
            return { id: suggestionId, username: `User${suggestionId}` };
          }
        })
      );
      
      setSuggestions(suggestionsWithDetails);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const addFriend = async (friendId) => {
    if (!user) return;
    
    try {
      await userAPI.addFriend(user.user_id, friendId);
      await Promise.all([loadFriends(), loadSuggestions()]);
      setError('');
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to add friend');
    }
  };

  const removeFriend = async (friendId) => {
    if (!user) return;
    
    if (!window.confirm('Are you sure you want to remove this friend?')) return;
    
    try {
      await userAPI.removeFriend(user.user_id, friendId);
      await Promise.all([loadFriends(), loadSuggestions()]);
      setError('');
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to remove friend');
    }
  };

  const handleAddFriendById = async () => {
    const friendId = parseInt(newFriendId);
    if (!friendId || friendId === user.user_id) {
      setError('Invalid friend ID');
      return;
    }
    
    await addFriend(friendId);
    setNewFriendId('');
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([loadFriends(), loadSuggestions()]);
      setLoading(false);
    };
    
    if (user) {
      init();
    }
  }, [user]);

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Friends ({friends.length})
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {/* Add Friend by ID */}
        <Box sx={{ mb: 2 }}>
          <TextField
            size="small"
            label="Friend ID"
            value={newFriendId}
            onChange={(e) => setNewFriendId(e.target.value)}
            fullWidth
            sx={{ mb: 1 }}
          />
          <Button
            size="small"
            variant="outlined"
            onClick={handleAddFriendById}
            disabled={!newFriendId}
            fullWidth
            startIcon={<PersonAddIcon />}
          >
            Add Friend
          </Button>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Friends List */}
        {friends.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No friends yet
          </Typography>
        ) : (
          <List dense>
            {friends.map((friend) => (
              <ListItem key={friend.id} sx={{ px: 0 }}>
                <Avatar sx={{ mr: 2, width: 32, height: 32 }}>
                  <PersonIcon />
                </Avatar>
                <ListItemText
                  primary={friend.username}
                  secondary={`ID: ${friend.id}`}
                />
                <ListItemSecondaryAction>
                  <IconButton
                    size="small"
                    onClick={() => removeFriend(friend.id)}
                    color="error"
                  >
                    <PersonRemoveIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}

        {/* Friend Suggestions */}
        {suggestions.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom>
              Suggestions
            </Typography>
            <List dense>
              {suggestions.map((suggestion) => (
                <ListItem key={suggestion.id} sx={{ px: 0 }}>
                  <Avatar sx={{ mr: 2, width: 32, height: 32 }}>
                    <PersonIcon />
                  </Avatar>
                  <ListItemText
                    primary={suggestion.username}
                    secondary={`ID: ${suggestion.id}`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      size="small"
                      onClick={() => addFriend(suggestion.id)}
                      color="primary"
                    >
                      <PersonAddIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default FriendsPanel;