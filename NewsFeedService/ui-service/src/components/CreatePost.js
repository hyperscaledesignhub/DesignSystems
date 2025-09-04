import React, { useState } from 'react';
import {
  Card,
  CardContent,
  TextField,
  Button,
  Box,
  Typography,
  Alert,
  CircularProgress
} from '@mui/material';
import { postAPI } from '../services/api';

const CreatePost = ({ onPostCreated }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;

    setLoading(true);
    setError('');

    try {
      await postAPI.createPost({ content: content.trim() });
      setContent('');
      if (onPostCreated) onPostCreated();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to create post');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          What's on your mind?
        </Typography>
        
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        
        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            multiline
            rows={3}
            fullWidth
            placeholder="Share something with your friends..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={loading}
            sx={{ mb: 2 }}
          />
          <Box display="flex" justifyContent="flex-end">
            <Button
              type="submit"
              variant="contained"
              disabled={!content.trim() || loading}
            >
              {loading ? <CircularProgress size={24} /> : 'Post'}
            </Button>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default CreatePost;