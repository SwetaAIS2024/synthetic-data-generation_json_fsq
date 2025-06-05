import React, { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useParams, useNavigate } from '@tanstack/react-router';

interface SampleResponse {
  id: string;
  display_id: string;
  yaml_config_id: string;
  created_at: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  seed_value: number;
  model: string;
  response_text: string;
  input_request: string;
  prompt: string;
  tokens_per_second: number;
  time_to_first_token: number;
  latency: number;
  total_tokens: number;
}

interface ConfigProgress {
  completed: number;
  total: number;
  percent: number;
}

interface YAMLConfigInfo {
  id: string;
  name: string;
  progress: ConfigProgress;
  dataset_uploaded?: boolean;
  dataset_id?: string;
}

interface PaginationInfo {
  page: number;
  page_size: number;
  total_pages: number;
  total_count: number;
}

// Add this at the top of the file, outside of any components
declare global {
  interface ImportMeta {
    env: {
      VITE_WS_URL?: string;
      VITE_API_URL?: string;
    }
  }
}

const YAMLConfigDetailPage: React.FC = () => {
  const { configId } = useParams({ from: '/yaml/$configId' });
  const navigate = useNavigate();
  const [responses, setResponses] = useState<SampleResponse[]>([]);
  const [configInfo, setConfigInfo] = useState<YAMLConfigInfo | null>(null);
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    page_size: 10,
    total_pages: 1,
    total_count: 0
  });
  const [selectedResponse, setSelectedResponse] = useState<SampleResponse | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [testStatus, setTestStatus] = useState<string | null>(null);
  
  // Format number with decimal places
  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };
  
  // Format date values
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'data_update') {
      setResponses(message.data);
      setPagination(message.pagination);
      if (message.config) {
        setConfigInfo(message.config);
      }
    }
  }, []);
  
  // Initialize WebSocket connection
  const { sendMessage, connectionStatus } = useWebSocket(
    `${(import.meta as any).env.VITE_WS_URL || 'ws://localhost:5001'}/api/ws/config/${configId}/responses?page=${pagination.page}&page_size=${pagination.page_size}`,
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
  
  // View response details
  const handleViewResponse = (response: SampleResponse) => {
    setSelectedResponse(response);
    setShowModal(true);
  };
  
  // Close modal
  const closeModal = () => {
    setShowModal(false);
    setSelectedResponse(null);
  };
  
  // Get progress color based on percentage
  const getProgressColor = (percent: number) => {
    if (percent >= 100) return 'bg-green-500';
    if (percent >= 75) return 'bg-blue-500';
    if (percent >= 50) return 'bg-yellow-500';
    if (percent >= 25) return 'bg-orange-500';
    return 'bg-red-500';
  };
  
  // Handle dataset upload
  const handleUploadDataset = async () => {
    if (!configId) return;
    
    try {
      setUploading(true);
      setUploadStatus("Uploading dataset...");
      
      // Use the same pattern that works in other components
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001';
      const uploadUrl = `${apiUrl}/api/upload/dataset/${configId}`;
      
      console.log("Uploading dataset using URL:", uploadUrl);
      
      const response = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      console.log("Upload response status:", response.status);
      const data = await response.json();
      console.log("Upload response data:", data);
      
      if (response.ok) {
        // Include the file path in the success message if available
        setUploadStatus(`Dataset uploaded successfully! ${JSON.stringify(data, null, 2)}`);
      } else {
        setUploadStatus(`Error: ${data.detail || 'Failed to upload dataset'}`);
      }
    } catch (error) {
      console.error("Error uploading dataset:", error);
      setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setUploading(false);
      // Hide success message after 5 seconds
      // if (uploadStatus?.startsWith("Dataset uploaded")) {
      //   setTimeout(() => setUploadStatus(null), 5000);
      // }
    }
  };

  // Handle dataset download
  const handleDownloadDataset = () => {
    if (!configId) return;
    
    // Build download URL
    const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001';
    const downloadUrl = `${apiUrl}/api/upload/download/${configId}`;
    
    // Open download URL in a new tab or trigger download
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <button 
            onClick={() => navigate({ to: '/' })}
            className="mb-4 text-indigo-600 hover:text-indigo-800 flex items-center"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to YAML Configs
          </button>
          <h2 className="text-2xl font-bold">
            {configInfo?.name || 'YAML Config Details'}
          </h2>
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
      
      {/* Upload Dataset Button */}
      <div className="mb-6 bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-lg font-medium">Dataset Actions</h3>
            {configInfo?.dataset_uploaded && (
              <p className="text-sm text-green-600 mt-1">
                Dataset uploaded successfully! ID: {configInfo.dataset_id}
              </p>
            )}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleUploadDataset}
              disabled={uploading || configInfo?.progress.percent !== 100 || configInfo?.dataset_uploaded}
              className={`px-4 py-2 rounded-md text-white ${
                uploading ? 'bg-gray-400 cursor-not-allowed' :
                configInfo?.dataset_uploaded ? 'bg-green-400 cursor-not-allowed' :
                configInfo?.progress.percent !== 100 ? 'bg-gray-400 cursor-not-allowed' :
                'bg-green-600 hover:bg-green-700'
              }`}
            >
              {uploading ? 'Uploading...' : 
               configInfo?.dataset_uploaded ? 'Dataset Uploaded' : 
               'Upload Dataset'}
            </button>
            
            <button
              onClick={handleDownloadDataset}
              disabled={!configInfo?.dataset_uploaded && configInfo?.progress.percent !== 100}
              className={`px-4 py-2 rounded-md text-white ${
                (!configInfo?.dataset_uploaded && configInfo?.progress.percent !== 100)
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              Download Dataset
            </button>
          </div>
        </div>
        {uploadStatus && (
          <div className={`mt-2 p-2 text-sm rounded ${
            uploadStatus.includes('Error') 
              ? 'bg-red-100 text-red-700' 
              : 'bg-green-100 text-green-700'
          }`}>
            {uploadStatus}
          </div>
        )}
        {testStatus && (
          <div className={`mt-2 p-2 text-sm rounded ${
            testStatus.includes('Error') || testStatus.includes('failed')
              ? 'bg-red-100 text-red-700' 
              : 'bg-green-100 text-green-700'
          }`}>
            {testStatus}
          </div>
        )}
      </div>
      
      {/* Progress Bar */}
      {configInfo && (
        <div className="mb-6 bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-2">Generation Progress</h3>
          <div className="flex items-center">
            <div className="w-full bg-gray-200 rounded-full h-4 mr-4">
              <div 
                className={`h-4 rounded-full ${getProgressColor(configInfo.progress.percent)}`} 
                style={{ width: `${configInfo.progress.percent}%` }}
              ></div>
            </div>
            <span>
              {configInfo.progress.completed} / {configInfo.progress.total} 
              ({configInfo.progress.percent}%)
            </span>
          </div>
        </div>
      )}
      
      {/* Sample Responses Table */}
      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created At
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Model
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Input
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Temp
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Speed
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                TTFT
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Latency
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tokens
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {responses.length > 0 ? (
              responses.map((response) => (
                <tr 
                  key={response.id} 
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleViewResponse(response)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">...{response.display_id}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formatDate(response.created_at)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{response.model}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {response.input_request 
                        ? (response.input_request.length > 30 
                           ? response.input_request.substring(0, 30) + '...' 
                           : response.input_request)
                        : 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{response.temperature}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatNumber(response.tokens_per_second)} t/s
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatNumber(response.time_to_first_token)} ms
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatNumber(response.latency)} ms
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {response.total_tokens}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={9} className="px-6 py-4 text-center text-sm text-gray-500">
                  No sample responses found
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
      
      {/* Response Detail Modal */}
      {showModal && selectedResponse && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 lg:w-3/4 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center border-b pb-4 mb-4">
              <h3 className="text-lg font-medium">Response Details</h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Response ID</h4>
              <p className="text-sm">{selectedResponse.id}</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Created At</h4>
                <p className="text-sm">{formatDate(selectedResponse.created_at)}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Model</h4>
                <p className="text-sm">{selectedResponse.model}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Temperature</h4>
                <p className="text-sm">{selectedResponse.temperature}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Top-p</h4>
                <p className="text-sm">{selectedResponse.top_p}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Max Tokens</h4>
                <p className="text-sm">{selectedResponse.max_tokens}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Seed Value</h4>
                <p className="text-sm">{selectedResponse.seed_value}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Tokens Per Second</h4>
                <p className="text-sm">{formatNumber(selectedResponse.tokens_per_second)} t/s</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Time to First Token</h4>
                <p className="text-sm">{formatNumber(selectedResponse.time_to_first_token)} ms</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Latency</h4>
                <p className="text-sm">{formatNumber(selectedResponse.latency)} ms</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Total Tokens</h4>
                <p className="text-sm">{selectedResponse.total_tokens}</p>
              </div>
            </div>
            
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Input Request</h4>
              <div className="bg-gray-50 rounded p-4 max-h-40 overflow-y-auto">
                <pre className="text-sm whitespace-pre-wrap">{selectedResponse.input_request || 'No input request available'}</pre>
              </div>
            </div>
            
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Full Prompt</h4>
              <div className="bg-gray-50 rounded p-4 max-h-60 overflow-y-auto">
                <pre className="text-sm whitespace-pre-wrap">{selectedResponse.prompt}</pre>
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-1">Response Text</h4>
              <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                <pre className="text-sm whitespace-pre-wrap">{selectedResponse.response_text}</pre>
              </div>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
};

export default YAMLConfigDetailPage;