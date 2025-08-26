import { useState, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8900';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const useApi = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const makeRequest = useCallback(async (method, url, data = null, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const config = {
        method,
        url,
        ...options,
      };
      
      if (data) {
        config.data = data;
      }
      
      const response = await api(config);
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.error || err.message || 'An error occurred';
      setError(errorMessage);
      
      if (!options.silent) {
        toast.error(errorMessage);
      }
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const get = useCallback((url, options = {}) => {
    return makeRequest('GET', url, null, options);
  }, [makeRequest]);

  const post = useCallback((url, data, options = {}) => {
    return makeRequest('POST', url, data, options);
  }, [makeRequest]);

  const put = useCallback((url, data, options = {}) => {
    return makeRequest('PUT', url, data, options);
  }, [makeRequest]);

  const del = useCallback((url, options = {}) => {
    return makeRequest('DELETE', url, null, options);
  }, [makeRequest]);

  return {
    loading,
    error,
    get,
    post,
    put,
    delete: del,
  };
};