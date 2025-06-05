import React, { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useNavigate } from '@tanstack/react-router';

interface YAMLConfig {
  id: string;
  display_id: string;
  name: string;
  created_at: string;
  model: string;
  number_of_samples: number;
  total_responses_generated: number;
  progress_percent: number;
  progress_status: string;
  output_format: string;
  avg_tokens_per_second: number;
  avg_time_to_first_token: number;
  avg_queries_per_second: number;
  avg_latency: number;
  temperature_range: number[];
  top_p: number;
  max_tokens: number;
}

interface PaginationInfo {
  page: number;
  page_size: number;
  total_pages: number;
  total_count: number;
}

interface FileUploadState {
  file: File;
  status: "pending" | "uploading" | "completed" | "error";
  message?: string;
}

const YAMLConfigDashboard: React.FC = () => {
  const [configs, setConfigs] = useState<YAMLConfig[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    page_size: 10,
    total_pages: 1,
    total_count: 0
  });
  const [liveMode, setLiveMode] = useState<boolean>(true);
  const navigate = useNavigate();
  
  // File upload states
  const [files, setFiles] = useState<FileUploadState[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  
  // Format number with decimal places and unit
  const formatMetric = (value: number, unit: string, decimals: number = 1) => {
    return `${value.toFixed(decimals)}${unit}`;
  };
  
  // Format number with decimal places (kept for backward compatibility)
  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };
  
  // Format date values
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  // Format model path to extract just the model name
  const formatModelName = (modelPath: string) => {
    if (!modelPath) return 'N/A';
    
    // Try to extract the model name from the path format "account/{account-id}/models/{model_name}"
    const modelMatch = modelPath.match(/\/models\/([^\/]+)$/);
    if (modelMatch && modelMatch[1]) {
      return modelMatch[1];
    }
    
    // If we can't match the expected format, just return the last part of the path
    const parts = modelPath.split('/');
    return parts[parts.length - 1];
  };
  
  // Extract account ID from model path
  const extractAccountId = (modelPath: string) => {
    if (!modelPath) return null;
    
    const accountMatch = modelPath.match(/account\/([^\/]+)/);
    if (accountMatch && accountMatch[1]) {
      return accountMatch[1];
    }
    
    return null;
  };
  
  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'data_update') {
      setConfigs(message.data);
      setPagination(message.pagination);
      if (message.live_mode !== undefined) {
        setLiveMode(message.live_mode);
      }
    }
  }, []);
  
  // Initialize WebSocket connection
  const { sendMessage, connectionStatus } = useWebSocket(
    `${(import.meta as any).env.VITE_WS_URL || 'ws://localhost:5001'}/api/ws/yaml_configs?page=${pagination.page}&page_size=${pagination.page_size}&live_mode=${liveMode}`,
    handleMessage
  );
  
  // Handle pagination change
  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > pagination.total_pages) return;
    
    setPagination(prev => ({ ...prev, page: newPage }));
    sendMessage(JSON.stringify({
      type: 'pagination',
      page: newPage,
      page_size: pagination.page_size
    }));
  };
  
  // Get progress color based on percentage
  const getProgressColor = (percent: number) => {
    if (percent >= 100) return 'bg-green-500';
    if (percent >= 75) return 'bg-blue-500';
    if (percent >= 50) return 'bg-yellow-500';
    if (percent >= 25) return 'bg-orange-500';
    return 'bg-red-500';
  };
  
  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Complete':
        return 'bg-green-100 text-green-800';
      case 'In Progress':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Toggle live mode
  const toggleLiveMode = () => {
    const newLiveMode = !liveMode;
    setLiveMode(newLiveMode);
    sendMessage(JSON.stringify({
      type: 'toggle_live_mode',
      live_mode: newLiveMode
    }));
  };
  
  // Toggle upload panel
  const toggleUploadPanel = () => {
    setIsUploadOpen(!isUploadOpen);
  };
  
  // File upload functions
  const validateFileType = (file: File): boolean => {
    const validTypes = ['application/x-yaml', 'text/yaml', 'text/x-yaml'];
    const validExtensions = ['.yaml', '.yml'];
    
    // Check file extension
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!validExtensions.includes(extension)) {
      return false;
    }
    
    // Check MIME type (note: some systems might not recognize YAML MIME types correctly)
    return validTypes.includes(file.type) || validExtensions.includes(extension);
  };

  const uploadFile = async (file: File) => {
    if (!validateFileType(file)) {
      setFiles((prevFiles) =>
        prevFiles.map((f) =>
          f.file === file ? { ...f, status: "error", message: "Invalid file type. Only YAML files are allowed." } : f
        )
      );
      return;
    }

    // Update file status to uploading
    setFiles((prevFiles) =>
      prevFiles.map((f) =>
        f.file === file ? { ...f, status: "uploading" } : f
      )
    );

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", file.name.replace(/\.[^/.]+$/, "")); // Remove extension for name

      const response = await fetch(`${(import.meta as any).env.VITE_API_URL || 'http://localhost:5001'}/api/upload/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Update file status to completed
      setFiles((prevFiles) =>
        prevFiles.map((f) =>
          f.file === file ? { ...f, status: "completed", message: data.message } : f
        )
      );

    } catch (error: any) {
      console.error("Error uploading file:", error);
      // Update file status to error
      setFiles((prevFiles) =>
        prevFiles.map((f) =>
          f.file === file ? { ...f, status: "error", message: error.message } : f
        )
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map((file) => ({
        file,
        status: "pending" as const,
      }));

      setFiles((prev) => [...prev, ...newFiles]);
      newFiles.forEach(({ file }) => uploadFile(file));
      // Clear the input value so the same file can be uploaded again
      e.target.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files).map((file) => ({
        file,
        status: "pending" as const,
      }));

      setFiles((prev) => [...prev, ...newFiles]);

      // Automatically start uploading each file
      newFiles.forEach(({ file }) => uploadFile(file));
      e.dataTransfer.clearData();
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragOut = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const removeFile = (index: number) => {
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">YAML Config Dashboard</h2>
        <div className="flex items-center space-x-4">
          <button
            onClick={toggleUploadPanel}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center"
          >
            <svg
              className="w-5 h-5 mr-2"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            Upload Config
          </button>
          <div className="flex items-center">
            <span className="mr-2 text-sm">Live Mode:</span>
            <button 
              onClick={toggleLiveMode}
              className={`relative inline-flex items-center h-6 rounded-full w-11 ${
                liveMode ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            >
              <span className="sr-only">Toggle live mode</span>
              <span 
                className={`${
                  liveMode ? 'translate-x-6' : 'translate-x-1'
                } inline-block w-4 h-4 transform bg-white rounded-full transition-transform duration-200 ease-in-out`}
              />
            </button>
          </div>
          <div className="text-sm">
            Connection Status: 
            <span className={`ml-2 px-2 py-1 rounded-full ${
              connectionStatus === 'Connected' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {connectionStatus}
            </span>
          </div>
        </div>
      </div>
      
      {/* Upload Area */}
      {isUploadOpen && (
        <div className="mb-6 bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-medium mb-4">Upload Configuration</h3>
          <div className="mb-4">
            <label
              htmlFor="file-upload"
              className={`flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer transition-colors duration-300 ${
                isDragging
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-300 bg-gray-50 hover:bg-gray-100"
              }`}
              onDragEnter={handleDragIn}
              onDragLeave={handleDragOut}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <div className="flex flex-col items-center justify-center pt-3 pb-3">
                <svg
                  className={`w-6 h-6 mb-2 ${isDragging ? "text-blue-500" : "text-gray-500"}`}
                  aria-hidden="true"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 20 16"
                >
                  <path
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"
                  />
                </svg>
                <p className={`mb-1 text-sm ${isDragging ? "text-blue-500" : "text-gray-500"}`}>
                  <span className="font-semibold">Click to upload</span> or drag and drop
                </p>
                <p className={`text-xs ${isDragging ? "text-blue-500" : "text-gray-500"}`}>
                  YAML files only (.yaml, .yml)
                </p>
              </div>
              <input
                id="file-upload"
                type="file"
                className="hidden"
                multiple
                accept=".yaml,.yml"
                onChange={handleFileChange}
              />
            </label>
          </div>
          
          {/* File previews */}
          {files.length > 0 && (
            <div>
              <h4 className="text-md font-medium mb-2">Uploaded Files</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 max-h-[200px] overflow-y-auto">
                {files.map((fileState, index) => (
                  <div key={index} className="bg-gray-50 rounded-lg shadow-sm p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium truncate max-w-[180px]" title={fileState.file.name}>
                        {fileState.file.name}
                      </span>
                      <button
                        onClick={() => removeFile(index)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-4 w-4"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                        >
                          <path
                            fillRule="evenodd"
                            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </button>
                    </div>
                    <div className="text-xs text-gray-500 mb-1">
                      {(fileState.file.size / 1024).toFixed(2)} KB
                    </div>
                    <div className={`text-xs ${
                      fileState.status === "completed"
                        ? "text-green-500"
                        : fileState.status === "error"
                          ? "text-red-500"
                          : "text-blue-500"
                    }`}>
                      {fileState.status === "completed"
                        ? "Uploaded successfully"
                        : fileState.status === "error"
                          ? "Failed to upload"
                          : fileState.status === "uploading"
                            ? "Uploading..."
                            : "Pending"}
                    </div>
                    {fileState.message && (
                      <div className="text-xs mt-1 text-gray-600">{fileState.message}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* YAML Config Table */}
      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="w-full table-fixed divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[16%]">
                Config Name
              </th>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[18%]" title="Model name and account ID">
                Model / Account
              </th>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[13%]">
                Created
              </th>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[23%]">
                Progress
              </th>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[10%]" title="Tokens Per Second">
                TPS
              </th>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[10%]" title="Time To First Token">
                TTFT
              </th>
              <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-[10%]" title="Average Response Latency">
                Latency
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {configs.length > 0 ? (
              configs.map((config) => (
                <tr 
                  key={config.id} 
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => {
                    navigate({ to: '/yaml/$configId', params: { configId: config.id } });
                  }}
                >
                  <td className="px-3 py-3 whitespace-normal break-words">
                    <div className="text-sm font-medium text-gray-900">{config.name}</div>
                    <div className="text-xs text-gray-500">...{config.display_id}</div>
                  </td>
                  <td className="px-3 py-3 whitespace-normal break-words">
                    <div className="text-sm font-medium text-gray-900 flex items-start">
                      <span className="break-words">{formatModelName(config.model)}</span>
                      <div className="ml-1.5 inline-flex items-center cursor-help relative group">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-indigo-500 hover:text-indigo-700" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        
                        {/* Tooltip that appears on hover */}
                        <div className="invisible group-hover:visible absolute z-50 bottom-full left-0 md:left-1/2 md:-translate-x-1/2 mb-2 bg-gray-800 text-white text-xs rounded-md py-2 px-3 w-auto min-w-[180px] max-w-[250px] whitespace-normal shadow-lg pointer-events-none transition-all duration-150 opacity-0 group-hover:opacity-100">
                          <div className="font-medium mb-1 border-b border-gray-700 pb-1">Model Path</div>
                          <div className="break-all text-xs pt-1">{config.model}</div>
                          {extractAccountId(config.model) && (
                            <div className="mt-2 text-xs pt-1 border-t border-gray-700">
                              <span className="font-medium">Account:</span> {extractAccountId(config.model)}
                            </div>
                          )}
                          {/* Arrow pointing down */}
                          <div className="absolute left-4 md:left-1/2 top-full md:-translate-x-1/2 border-solid border-t-gray-800 border-t-4 border-x-transparent border-x-4 border-b-0"></div>
                        </div>
                      </div>
                    </div>
                    {extractAccountId(config.model) && (
                      <div className="text-xs text-gray-500 truncate pl-0">
                        {extractAccountId(config.model)!.length > 15
                          ? `${extractAccountId(config.model)!.substring(0, 13)}...`
                          : extractAccountId(config.model)}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-3 whitespace-normal">
                    <div className="text-sm text-gray-900">{formatDate(config.created_at)}</div>
                  </td>
                  <td className="px-3 py-3 whitespace-normal">
                    <div className="flex flex-col">
                      <div className="flex items-center mb-1">
                        <div className="w-full bg-gray-200 rounded-full h-2.5 mr-2">
                          <div 
                            className={`h-2.5 rounded-full ${getProgressColor(config.progress_percent)}`} 
                            style={{ width: `${config.progress_percent}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-900 min-w-[80px] text-right">
                          {config.total_responses_generated} / {config.number_of_samples}
                        </span>
                      </div>
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(config.progress_status)}`}>
                        {config.progress_status}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-3 whitespace-normal text-sm text-gray-900">
                    {formatMetric(config.avg_tokens_per_second, "t/s")}
                  </td>
                  <td className="px-3 py-3 whitespace-normal text-sm text-gray-900">
                    {formatMetric(config.avg_time_to_first_token, "ms")}
                  </td>
                  <td className="px-3 py-3 whitespace-normal text-sm text-gray-900">
                    {formatMetric(config.avg_latency, "ms")}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="px-3 py-3 text-center text-sm text-gray-500">
                  No YAML configurations found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <div className="flex-1 flex justify-between sm:hidden">
          <button
            onClick={() => handlePageChange(pagination.page - 1)}
            disabled={pagination.page === 1}
            className={`relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md ${
              pagination.page === 1 
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Previous
          </button>
          <button
            onClick={() => handlePageChange(pagination.page + 1)}
            disabled={pagination.page === pagination.total_pages}
            className={`ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md ${
              pagination.page === pagination.total_pages 
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            Next
          </button>
        </div>
        <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-700">
              Showing <span className="font-medium">{(pagination.page - 1) * pagination.page_size + 1}</span> to{' '}
              <span className="font-medium">
                {Math.min(pagination.page * pagination.page_size, pagination.total_count)}
              </span>{' '}
              of <span className="font-medium">{pagination.total_count}</span> results
            </p>
          </div>
          <div>
            <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
              <button
                onClick={() => handlePageChange(1)}
                disabled={pagination.page === 1}
                className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium ${
                  pagination.page === 1 
                    ? 'text-gray-300 cursor-not-allowed' 
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                <span className="sr-only">First</span>
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </button>
              <button
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className={`relative inline-flex items-center px-2 py-2 border border-gray-300 bg-white text-sm font-medium ${
                  pagination.page === 1 
                    ? 'text-gray-300 cursor-not-allowed' 
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                <span className="sr-only">Previous</span>
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </button>
              
              {/* Page numbers */}
              {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                const pageNum = pagination.page <= 3 
                  ? i + 1 
                  : pagination.page >= pagination.total_pages - 2 
                    ? pagination.total_pages - 4 + i 
                    : pagination.page - 2 + i;
                
                if (pageNum <= pagination.total_pages && pageNum > 0) {
                  return (
                    <button
                      key={pageNum}
                      onClick={() => handlePageChange(pageNum)}
                      className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                        pagination.page === pageNum
                          ? 'z-10 bg-indigo-50 border-indigo-500 text-indigo-600'
                          : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                }
                return null;
              })}
              
              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.total_pages}
                className={`relative inline-flex items-center px-2 py-2 border border-gray-300 bg-white text-sm font-medium ${
                  pagination.page === pagination.total_pages 
                    ? 'text-gray-300 cursor-not-allowed' 
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                <span className="sr-only">Next</span>
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              </button>
              <button
                onClick={() => handlePageChange(pagination.total_pages)}
                disabled={pagination.page === pagination.total_pages}
                className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium ${
                  pagination.page === pagination.total_pages 
                    ? 'text-gray-300 cursor-not-allowed' 
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                <span className="sr-only">Last</span>
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>
  );
};

export default YAMLConfigDashboard; 