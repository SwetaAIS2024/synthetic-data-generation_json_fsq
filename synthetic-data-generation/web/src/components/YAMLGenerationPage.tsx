import React, { useState, useEffect } from 'react';
import * as yaml from 'js-yaml'; // Import js-yaml for parsing

const YAMLGenerationPage: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [generatedYaml, setGeneratedYaml] = useState<string | null>(null);
  const [editableYaml, setEditableYaml] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // State for upload status
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatusMessage, setUploadStatusMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  // Clear upload status when generated YAML changes
  useEffect(() => {
      setIsUploading(false);
      setUploadStatusMessage(null);
      setUploadError(null);
  }, [generatedYaml]);

  // Update editable YAML when generated YAML changes
  useEffect(() => {
    setEditableYaml(generatedYaml);
  }, [generatedYaml]);

  const handleInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(event.target.value);
  };

  const handleYamlEdit = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditableYaml(event.target.value);
  };

  const handleGenerateClick = async () => {
    if (!inputText.trim()) {
      setError('Please enter a description for the dataset.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setGeneratedYaml(null);
    // Clear previous upload status on new generation
    setIsUploading(false);
    setUploadStatusMessage(null);
    setUploadError(null);


    try {
      // Use the actual backend endpoint URL
      // Ensure VITE_API_URL is set in your .env file (e.g., VITE_API_URL=http://localhost:5001)
      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/generation/generate-yaml`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ description: inputText }),
      });

      if (!response.ok) {
        // Try to parse error message from backend, provide generic fallback
        let errorMessage = 'Failed to generate YAML. Please try again.';
        try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || `HTTP error! status: ${response.status}`;
        } catch (parseError) {
             errorMessage = `HTTP error! status: ${response.status}`;
             console.error("Failed to parse error response:", parseError);
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      // Assuming the backend returns { yaml: "..." }
      if (data.yaml) {
        setGeneratedYaml(data.yaml);
      } else {
        throw new Error('Invalid response format from server. Expected { yaml: "..." }.');
      }

    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
      console.error("Generation failed:", err);
    } finally {
      setIsLoading(false);
    }
    // --- Actual API Call END ---
  };

  const handleCopyToClipboard = () => {
    if (editableYaml) {
      navigator.clipboard.writeText(editableYaml)
        .then(() => {
          // Optional: Show a temporary "Copied!" message
          console.log('YAML copied to clipboard!');
          // Set a success message for copy
          setUploadStatusMessage('Copied to clipboard!');
          setUploadError(null);
          // Clear message after a few seconds
          setTimeout(() => setUploadStatusMessage(null), 3000);
        })
        .catch(err => {
          console.error('Failed to copy YAML: ', err);
          setUploadError('Failed to copy YAML to clipboard.');
          setUploadStatusMessage(null);
        });
    }
  };
  
  // Function to handle uploading the generated YAML
  const handleUploadClick = async () => {
    if (!editableYaml) return;

    setIsUploading(true);
    setUploadStatusMessage(null);
    setUploadError(null);

    let configName = 'generated-config'; // Default name
    try {
      // Attempt to parse the YAML to get the name field
      const parsedYaml = yaml.load(editableYaml) as { name?: string };
      if (parsedYaml && typeof parsedYaml === 'object' && parsedYaml.name) {
        configName = parsedYaml.name.replace(/[^a-zA-Z0-9_-]/g, '-').substring(0, 50); // Sanitize and shorten
      }
    } catch (parseError) {
      console.warn("Could not parse YAML to extract name, using default.", parseError);
    }
    
    // Create a filename
    const filename = `${configName}.yaml`;

    try {
      const blob = new Blob([editableYaml], { type: 'application/x-yaml' });
      const formData = new FormData();
      formData.append('file', blob, filename);
      // Use the extracted/default name for the 'name' field expected by the endpoint
      formData.append('name', configName);

      const apiUrl = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/upload/upload`, { // Target the upload endpoint
        method: 'POST',
        body: formData,
        // Note: Don't set Content-Type header when using FormData, browser handles it
      });

      if (!response.ok) {
         let errorMessage = 'Upload failed. Please try again.';
        try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || `HTTP error! status: ${response.status}`;
        } catch (parseError) {
             errorMessage = `HTTP error! status: ${response.status}`;
             console.error("Failed to parse upload error response:", parseError);
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      setUploadStatusMessage(data.message || 'YAML uploaded successfully!'); // Use message from backend if available

    } catch (err: any) {
      setUploadError(err.message || 'An unexpected error occurred during upload.');
      console.error("Upload failed:", err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold mb-6">Generate YAML Configuration</h2>

      {/* Input Section */}
      <div className="mb-6">
        <label htmlFor="description-input" className="block text-sm font-medium text-gray-700 mb-1">
          Describe the synthetic dataset you want to generate:
        </label>
        <textarea
          id="description-input"
          rows={5}
          className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="e.g., Create a realistic customer support dataset for an auto insurance company focusing on claim inquiries."
          value={inputText}
          onChange={handleInputChange}
          disabled={isLoading || isUploading}
        />
        <button
          onClick={handleGenerateClick}
          disabled={isLoading || isUploading || !inputText.trim()}
          className={`mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[150px] ${isLoading ? 'bg-indigo-400' : ''}`}
        >
          {isLoading ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating...
            </>
          ) : (
            'Generate YAML'
          )}
        </button>
      </div>

      {/* Output/Status Section */}
      <div className="mt-8">
        <h3 className="text-xl font-semibold mb-4">Generated Output</h3>
        {isLoading && !error && (
          <div className="text-gray-600">Generating configuration... Please wait.</div>
        )}
        {error && (
          <div className="p-4 mb-4 text-sm text-red-700 bg-red-100 rounded-lg" role="alert">
            <span className="font-medium">Generation Error:</span> {error}
          </div>
        )}
        
        {generatedYaml && !isLoading && !error && (
          <div className="relative mb-4">
            <div className="absolute top-2 right-2 flex space-x-2">
               <button
                  onClick={handleCopyToClipboard}
                  className="px-3 py-1 bg-gray-200 text-gray-700 text-xs font-medium rounded hover:bg-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Copy to Clipboard"
                  disabled={isUploading}
               >
                  Copy
               </button>
               <button
                  onClick={handleUploadClick}
                  className="px-3 py-1 bg-blue-500 text-white text-xs font-medium rounded hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                  title="Upload Generated YAML"
                  disabled={isUploading}
               >
                 {isUploading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                         <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                         <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Uploading...
                    </>
                 ) : (
                    'Upload'
                 )}
               </button>
            </div>
            <textarea
              className="w-full p-4 rounded-md border border-gray-200 bg-gray-50 text-sm text-gray-800 font-mono min-h-[300px] max-h-[500px]"
              value={editableYaml || ''}
              onChange={handleYamlEdit}
              disabled={isUploading}
              spellCheck="false"
            />
          </div>
        )}
        
        {uploadStatusMessage && (
          <div className="p-3 mb-4 text-sm text-green-700 bg-green-100 rounded-lg" role="alert">
            {uploadStatusMessage}
          </div>
        )}
        {uploadError && (
          <div className="p-3 mb-4 text-sm text-red-700 bg-red-100 rounded-lg" role="alert">
             <span className="font-medium">Upload Error:</span> {uploadError}
          </div>
        )}

        {!generatedYaml && !isLoading && !error && (
          <div className="text-gray-500 italic">Generated YAML will appear here once generated.</div>
        )}
      </div>
    </div>
  );
};

export default YAMLGenerationPage; 