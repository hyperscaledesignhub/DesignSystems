import React, { useState } from 'react';
import { metadataAPI } from '../../services/api';
import { Search, File, Calendar, HardDrive, Tag } from 'lucide-react';
import toast from 'react-hot-toast';

const SearchFiles = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);

  const handleSearch = async (searchQuery = query) => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    setLoading(true);
    try {
      const response = await metadataAPI.search(searchQuery.trim());
      setResults(response.data.files || []);
      
      // Add to search history
      setSearchHistory(prev => {
        const newHistory = [searchQuery, ...prev.filter(q => q !== searchQuery)].slice(0, 5);
        return newHistory;
      });
      
      if (response.data.files?.length === 0) {
        toast.info('No files found matching your search');
      } else {
        toast.success(`Found ${response.data.files?.length} files`);
      }
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString() + ' ' + 
           new Date(dateString).toLocaleTimeString();
  };

  const getFileIcon = (fileName) => {
    const extension = fileName?.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'pdf': return '📄';
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif': return '🖼️';
      case 'doc':
      case 'docx': return '📝';
      case 'xls':
      case 'xlsx': return '📊';
      case 'mp4':
      case 'avi':
      case 'mov': return '🎥';
      case 'mp3':
      case 'wav': return '🎵';
      default: return '📄';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Search Files</h1>
        <p className="text-gray-600">Find your files by name, content, or metadata</p>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent"
              placeholder="Search files by name, content, or metadata..."
            />
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="btn btn-primary px-6 disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Search History */}
        {searchHistory.length > 0 && (
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Recent searches:</p>
            <div className="flex flex-wrap gap-2">
              {searchHistory.map((historicalQuery, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setQuery(historicalQuery);
                    handleSearch(historicalQuery);
                  }}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {historicalQuery}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Search Results */}
      {results.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              Search Results ({results.length} files)
            </h3>
          </div>
          
          <div className="divide-y divide-gray-200">
            {results.map((file) => (
              <div key={file.file_id} className="p-6 hover:bg-gray-50">
                <div className="flex items-start space-x-4">
                  <span className="text-2xl flex-shrink-0">
                    {getFileIcon(file.filename)}
                  </span>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <h4 className="text-lg font-medium text-gray-900 truncate">
                        {file.filename}
                      </h4>
                      {file.version > 1 && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          v{file.version}
                        </span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
                      <div className="flex items-center space-x-2">
                        <HardDrive className="h-4 w-4" />
                        <span>{formatFileSize(file.file_size)}</span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDate(file.created_at)}</span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Tag className="h-4 w-4" />
                        <span>{file.file_type || 'Unknown'}</span>
                      </div>
                    </div>
                    
                    <div className="mt-3 text-sm text-gray-600">
                      <strong>Path:</strong> {file.file_path}
                    </div>
                    
                    {file.tags && file.tags.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {file.tags.map((tag, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0">
                    <div className="flex space-x-2">
                      <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
                        View
                      </button>
                      <button className="text-green-600 hover:text-green-800 text-sm font-medium">
                        Download
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-blue-900 mb-3">Search Tips</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800">
          <div>
            <h4 className="font-medium mb-2">Basic Search:</h4>
            <ul className="space-y-1">
              <li>• Search by filename: "document.pdf"</li>
              <li>• Search by extension: ".jpg"</li>
              <li>• Search by content: "meeting notes"</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Advanced Features:</h4>
            <ul className="space-y-1">
              <li>• Metadata search integration</li>
              <li>• Version history access</li>
              <li>• File type filtering</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Empty State */}
      {!loading && results.length === 0 && query && (
        <div className="text-center py-12">
          <Search className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
          <p className="mt-1 text-sm text-gray-500">
            Try adjusting your search query or check the search tips above.
          </p>
        </div>
      )}
    </div>
  );
};

export default SearchFiles;