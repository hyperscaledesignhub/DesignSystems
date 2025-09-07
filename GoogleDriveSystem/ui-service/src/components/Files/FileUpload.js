import React, { useState, useRef } from 'react';
import { fileAPI, blockAPI, metadataAPI, notificationAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { Upload, X, CheckCircle, AlertCircle, File, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

const FileUpload = () => {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadMode, setUploadMode] = useState('file'); // 'file' or 'block'
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    addFiles(selectedFiles);
  };

  const addFiles = (newFiles) => {
    const fileObjects = newFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      progress: 0,
      status: 'pending', // 'pending', 'uploading', 'completed', 'error'
      error: null,
      uploadedFileId: null
    }));
    setFiles(prev => [...prev, ...fileObjects]);
  };

  const removeFile = (fileId) => {
    setFiles(files.filter(f => f.id !== fileId));
  };

  const calculateFileHash = async (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = async (event) => {
        const arrayBuffer = event.target.result;
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        resolve(hashHex);
      };
      reader.readAsArrayBuffer(file);
    });
  };

  const uploadFile = async (fileObject, api, serviceName) => {
    const formData = new FormData();
    formData.append('file', fileObject.file);
    if (uploadMode === 'file') {
      formData.append('folder_path', '/uploads');
    }

    try {
      const response = await api.upload(formData, (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setFiles(prev => prev.map(f => 
          f.id === fileObject.id ? { ...f, progress, status: 'uploading' } : f
        ));
      });

      const uploadedFileId = response.data.file_id;
      
      setFiles(prev => prev.map(f => 
        f.id === fileObject.id 
          ? { ...f, status: 'completed', uploadedFileId }
          : f
      ));

      // Send notification
      await notificationAPI.send({
        user_id: user.user_id,
        type: 'file_upload',
        message: `Uploaded via ${serviceName}: ${fileObject.file.name}`,
        data: { 
          file_id: uploadedFileId, 
          file_name: fileObject.file.name,
          service: serviceName
        }
      });

      // Create metadata entry
      try {
        const checksum = await calculateFileHash(fileObject.file);
        await metadataAPI.create({
          file_id: uploadedFileId,
          filename: fileObject.file.name,
          file_size: fileObject.file.size,
          content_type: fileObject.file.type || 'application/octet-stream',
          file_path: `/uploads/${fileObject.file.name}`,
          checksum: checksum
        });
      } catch (metaError) {
        console.warn('Failed to create metadata:', metaError);
      }

      toast.success(`File uploaded successfully via ${serviceName}!`);
    } catch (error) {
      console.error(`${serviceName} upload failed:`, error);
      setFiles(prev => prev.map(f => 
        f.id === fileObject.id 
          ? { ...f, status: 'error', error: error.response?.data?.detail || 'Upload failed' }
          : f
      ));
      toast.error(`Upload failed via ${serviceName}`);
    }
  };

  const startUploads = async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    
    for (const fileObject of pendingFiles) {
      if (uploadMode === 'file') {
        await uploadFile(fileObject, fileAPI, 'File Service');
      } else {
        await uploadFile(fileObject, blockAPI, 'Block Service');
      }
    }
  };

  const clearCompleted = () => {
    setFiles(files.filter(f => f.status !== 'completed'));
  };

  const clearAll = () => {
    setFiles([]);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'text-gray-500';
      case 'uploading': return 'text-blue-600';
      case 'completed': return 'text-green-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'error': return <AlertCircle className="h-5 w-5 text-red-600" />;
      default: return <File className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">File Upload</h1>
          <p className="text-gray-600">Upload files to your Google Drive MVP</p>
        </div>
        
        {/* Upload Mode Toggle */}
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-gray-700">Upload Mode:</label>
          <div className="flex bg-gray-200 rounded-lg p-1">
            <button
              onClick={() => setUploadMode('file')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                uploadMode === 'file' 
                  ? 'bg-white text-google-blue shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Upload className="h-4 w-4 inline mr-1" />
              File Service
            </button>
            <button
              onClick={() => setUploadMode('block')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                uploadMode === 'block' 
                  ? 'bg-white text-google-blue shadow-sm' 
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Zap className="h-4 w-4 inline mr-1" />
              Block Service
            </button>
          </div>
        </div>
      </div>

      {/* Upload Mode Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-blue-100 rounded-full">
            {uploadMode === 'file' ? (
              <Upload className="h-5 w-5 text-blue-600" />
            ) : (
              <Zap className="h-5 w-5 text-blue-600" />
            )}
          </div>
          <div>
            <h3 className="font-medium text-blue-900">
              {uploadMode === 'file' ? 'File Service Upload' : 'Block Service Upload'}
            </h3>
            <p className="text-sm text-blue-700 mt-1">
              {uploadMode === 'file' 
                ? 'Upload files directly to the file service with metadata storage.'
                : 'Upload files with advanced block splitting, compression, and encryption.'}
            </p>
          </div>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging 
            ? 'border-google-blue bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Drop files here, or click to select
        </h3>
        <p className="text-gray-600 mb-4">
          Support for all file types up to 10GB
        </p>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="btn btn-primary"
        >
          Select Files
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">
              Upload Queue ({files.length} files)
            </h3>
            <div className="flex items-center space-x-3">
              {files.some(f => f.status === 'pending') && (
                <button
                  onClick={startUploads}
                  className="btn btn-primary btn-sm"
                >
                  Start Upload
                </button>
              )}
              {files.some(f => f.status === 'completed') && (
                <button
                  onClick={clearCompleted}
                  className="btn btn-secondary btn-sm"
                >
                  Clear Completed
                </button>
              )}
              <button
                onClick={clearAll}
                className="btn btn-secondary btn-sm"
              >
                Clear All
              </button>
            </div>
          </div>
          
          <div className="max-h-96 overflow-y-auto">
            {files.map((fileObject) => (
              <div key={fileObject.id} className="px-6 py-4 border-b border-gray-100 last:border-b-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1">
                    {getStatusIcon(fileObject.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {fileObject.file.name}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>{formatFileSize(fileObject.file.size)}</span>
                        <span className={getStatusColor(fileObject.status)}>
                          {fileObject.status.charAt(0).toUpperCase() + fileObject.status.slice(1)}
                        </span>
                        {fileObject.error && (
                          <span className="text-red-600">{fileObject.error}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    {fileObject.status === 'uploading' && (
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-google-blue h-2 rounded-full transition-all duration-300"
                            style={{ width: `${fileObject.progress}%` }}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-500 w-10">
                          {fileObject.progress}%
                        </span>
                      </div>
                    )}
                    
                    {fileObject.status === 'pending' && (
                      <button
                        onClick={() => removeFile(fileObject.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Stats */}
      {files.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow-sm border text-center">
            <div className="text-2xl font-bold text-gray-900">
              {files.filter(f => f.status === 'pending').length}
            </div>
            <div className="text-sm text-gray-600">Pending</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border text-center">
            <div className="text-2xl font-bold text-blue-600">
              {files.filter(f => f.status === 'uploading').length}
            </div>
            <div className="text-sm text-gray-600">Uploading</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border text-center">
            <div className="text-2xl font-bold text-green-600">
              {files.filter(f => f.status === 'completed').length}
            </div>
            <div className="text-sm text-gray-600">Completed</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border text-center">
            <div className="text-2xl font-bold text-red-600">
              {files.filter(f => f.status === 'error').length}
            </div>
            <div className="text-sm text-gray-600">Failed</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;