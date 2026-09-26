import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { invoiceAPI } from '../services/api';

function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError('Invalid file type. Please upload a PDF or image file (PNG, JPG, JPEG).');
      setFile(null);
      return;
    }
    
    // Validate file size (10MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File too large. Maximum size is 10MB.');
      setFile(null);
      return;
    }
    
    setError('');
    setFile(selectedFile);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file to upload.');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const response = await invoiceAPI.upload(file);
      setResult(response);
      
      // Navigate to invoice details after successful upload
      setTimeout(() => {
        navigate(`/invoice/${response.document_id}`);
      }, 1500);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload invoice. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-900 mb-2">Upload Document</h1>
        <p className="text-gray-600">Upload invoices, receipts, or other documents for AI-powered extraction.</p>
      </div>

      <div className="max-w-3xl">
        {/* Upload Area */}
        <div
          className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
            dragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.png,.jpg,.jpeg"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={uploading}
          />
          
          {!file ? (
            <>
              <div className="text-5xl mb-4">📤</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Drop your document here
              </h3>
              <p className="text-gray-600 mb-4">or browse files</p>
              <p className="text-sm text-gray-500">
                Supported formats: PDF, PNG, JPG, JPEG (max 10MB)
              </p>
            </>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg p-6 inline-block">
              <div className="flex items-center space-x-4">
                <div className="text-4xl">📄</div>
                <div className="text-left">
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-600">{formatFileSize(file.size)}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <span className="text-red-600 mr-2">⚠️</span>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center">
              <span className="text-green-600 mr-2">✅</span>
              <div>
                <p className="text-sm text-green-700 font-medium">Upload successful!</p>
                <p className="text-sm text-green-700">Document ID: {result.document_id}</p>
                <p className="text-sm text-green-700">Status: {result.status}</p>
                <p className="text-sm text-gray-600 mt-1">Redirecting to invoice details...</p>
              </div>
            </div>
          </div>
        )}

        {file && (
          <div className="mt-6 flex space-x-4">
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="flex-1 bg-primary-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? (
                <span className="flex items-center justify-center">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Processing...
                </span>
              ) : (
                'Upload & Process'
              )}
            </button>
            <button
              onClick={() => setFile(null)}
              disabled={uploading}
              className="px-6 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Cancel
            </button>
          </div>
        )}

        {/* Processing Steps */}
        <div className="mt-12">
          <h3 className="text-lg font-medium text-gray-900 mb-6">Processing Pipeline</h3>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">📤</span>
              </div>
              <p className="text-sm font-medium text-gray-900">Upload</p>
              <p className="text-xs text-gray-500">Document storage</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">🔍</span>
              </div>
              <p className="text-sm font-medium text-gray-900">OCR</p>
              <p className="text-xs text-gray-500">Text extraction</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">🧠</span>
              </div>
              <p className="text-sm font-medium text-gray-900">Extraction</p>
              <p className="text-xs text-gray-500">Field identification</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">✓</span>
              </div>
              <p className="text-sm font-medium text-gray-900">Validation</p>
              <p className="text-xs text-gray-500">Data integrity</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-2xl">📊</span>
              </div>
              <p className="text-sm font-medium text-gray-900">Routing</p>
              <p className="text-xs text-gray-500">Confidence-based</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Upload;
