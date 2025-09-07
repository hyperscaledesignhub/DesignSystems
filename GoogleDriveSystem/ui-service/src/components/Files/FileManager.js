import React, { useState, useEffect } from 'react';
import { fileAPI, metadataAPI, notificationAPI, authAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { 
  Upload, 
  Download, 
  Trash2, 
  Edit3, 
  Share, 
  File, 
  Folder,
  MoreHorizontal,
  Eye,
  RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';

const FileManager = () => {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [folders, setFolders] = useState([]);
  const [currentPath, setCurrentPath] = useState('/');
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  useEffect(() => {
    loadFiles();
    loadFolders();
  }, [currentPath]);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const response = await fileAPI.list(currentPath);
      setFiles(response.data.files || []);
    } catch (error) {
      console.error('Failed to load files:', error);
      toast.error('Failed to load files');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  const loadFolders = async () => {
    try {
      const response = await metadataAPI.getFolders(currentPath);
      setFolders(response.data.folders || []);
    } catch (error) {
      console.error('Failed to load folders:', error);
      setFolders([]);
    }
  };

  const handleDownload = async (file) => {
    try {
      const response = await fileAPI.download(file.file_id);
      
      // Create blob URL and trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.filename || 'download');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('File downloaded successfully!');
      
      // Send notification
      await notificationAPI.send({
        user_id: user.user_id,
        type: 'file_download',
        message: `Downloaded: ${file.filename}`,
        data: { file_id: file.file_id, file_name: file.filename }
      });
    } catch (error) {
      console.error('Download failed:', error);
      toast.error('Failed to download file');
    }
  };

  const handleDelete = async (file) => {
    if (!window.confirm(`Are you sure you want to delete "${file.filename}"?`)) {
      return;
    }

    try {
      await fileAPI.delete(file.file_id);
      setFiles(files.filter(f => f.file_id !== file.file_id));
      toast.success('File deleted successfully!');
      
      // Send notification
      await notificationAPI.send({
        user_id: user.user_id,
        type: 'file_delete',
        message: `Deleted: ${file.filename}`,
        data: { file_id: file.file_id, file_name: file.filename }
      });
    } catch (error) {
      console.error('Delete failed:', error);
      toast.error('Failed to delete file');
    }
  };

  const handleRename = async () => {
    if (!selectedFile || !newFileName.trim()) return;

    try {
      await fileAPI.rename(selectedFile.file_id, newFileName.trim());
      
      // Update metadata with new filename
      try {
        await metadataAPI.update(selectedFile.file_id, {
          filename: newFileName.trim()
        });
      } catch (metaError) {
        console.warn('Failed to update metadata:', metaError);
      }
      
      setFiles(files.map(f => 
        f.file_id === selectedFile.file_id 
          ? { ...f, filename: newFileName.trim() }
          : f
      ));
      setShowRenameModal(false);
      setSelectedFile(null);
      setNewFileName('');
      toast.success('File renamed successfully!');
    } catch (error) {
      console.error('Rename failed:', error);
      toast.error('Failed to rename file');
    }
  };

  const handleShare = async (shareEmailOrUserId) => {
    if (!selectedFile || !shareEmailOrUserId.trim()) return;

    try {
      let targetUserId = shareEmailOrUserId.trim();
      
      // Check if it's an email (contains @) or already a user ID
      if (shareEmailOrUserId.includes('@')) {
        try {
          const lookupResponse = await authAPI.lookupUser(shareEmailOrUserId.trim());
          targetUserId = lookupResponse.data.user_id;
        } catch (lookupError) {
          console.error('User lookup failed:', lookupError);
          toast.error('User not found. Please check the email address.');
          return;
        }
      }

      await fileAPI.share(selectedFile.file_id, {
        shared_with_user_id: targetUserId,
        permission: 'read'
      });
      setShowShareModal(false);
      setSelectedFile(null);
      toast.success('File shared successfully!');
      
      // Send notification
      await notificationAPI.send({
        user_id: user.user_id,
        type: 'file_share',
        message: `Shared: ${selectedFile.filename} with ${shareEmailOrUserId}`,
        data: { 
          file_id: selectedFile.file_id, 
          file_name: selectedFile.filename,
          shared_with: shareEmailOrUserId
        }
      });
    } catch (error) {
      console.error('Share failed:', error);
      toast.error('Failed to share file');
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
      case 'pdf':
        return '📄';
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return '🖼️';
      case 'doc':
      case 'docx':
        return '📝';
      case 'xls':
      case 'xlsx':
        return '📊';
      case 'mp4':
      case 'avi':
      case 'mov':
        return '🎥';
      case 'mp3':
      case 'wav':
        return '🎵';
      default:
        return '📄';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">File Manager</h1>
          <p className="text-gray-600">Current path: {currentPath}</p>
        </div>
        <button
          onClick={() => { loadFiles(); loadFolders(); }}
          className="btn btn-secondary flex items-center space-x-2"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Navigation */}
      <div className="flex items-center space-x-2 text-sm">
        <button
          onClick={() => setCurrentPath('/')}
          className="text-google-blue hover:text-blue-600"
        >
          Home
        </button>
        {currentPath !== '/' && (
          <>
            {currentPath.split('/').filter(Boolean).map((segment, index, array) => (
              <React.Fragment key={segment}>
                <span className="text-gray-400">/</span>
                <button
                  onClick={() => setCurrentPath('/' + array.slice(0, index + 1).join('/'))}
                  className="text-google-blue hover:text-blue-600"
                >
                  {segment}
                </button>
              </React.Fragment>
            ))}
          </>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-google-blue"></div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Modified
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {/* Folders */}
                {folders.map((folder) => (
                  <tr
                    key={folder.folder_id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setCurrentPath(folder.path)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Folder className="h-5 w-5 text-blue-500 mr-3" />
                        <span className="text-sm font-medium text-gray-900">
                          {folder.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      Folder
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(folder.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <button className="text-gray-400 hover:text-gray-600">
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}

                {/* Files */}
                {files.map((file) => (
                  <tr key={file.file_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="text-lg mr-3">
                          {getFileIcon(file.filename)}
                        </span>
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {file.filename}
                          </div>
                          {file.is_shared && (
                            <div className="text-xs text-blue-600">Shared</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatFileSize(file.file_size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(file.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleDownload(file)}
                          className="text-blue-600 hover:text-blue-800"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedFile(file);
                            setNewFileName(file.filename);
                            setShowRenameModal(true);
                          }}
                          className="text-green-600 hover:text-green-800"
                          title="Rename"
                        >
                          <Edit3 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedFile(file);
                            setShowShareModal(true);
                          }}
                          className="text-purple-600 hover:text-purple-800"
                          title="Share"
                        >
                          <Share className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(file)}
                          className="text-red-600 hover:text-red-800"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {files.length === 0 && folders.length === 0 && (
              <div className="text-center py-12">
                <File className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No files</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Get started by uploading a file.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Rename Modal */}
      {showRenameModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Rename File</h3>
            <input
              type="text"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              className="input w-full mb-4"
              placeholder="Enter new file name"
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowRenameModal(false);
                  setSelectedFile(null);
                  setNewFileName('');
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleRename}
                className="btn btn-primary"
              >
                Rename
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Share Modal */}
      {showShareModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Share File</h3>
            <p className="text-sm text-gray-600 mb-4">
              Enter the user ID or email to share "{selectedFile?.filename}" with:
            </p>
            <input
              type="text"
              className="input w-full mb-4"
              placeholder="User ID or email"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleShare(e.target.value);
                }
              }}
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowShareModal(false);
                  setSelectedFile(null);
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const input = document.querySelector('input[placeholder="User ID or email"]');
                  handleShare(input.value);
                }}
                className="btn btn-primary"
              >
                Share
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileManager;