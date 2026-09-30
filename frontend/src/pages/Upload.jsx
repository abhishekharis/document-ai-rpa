import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, X, Loader2, Upload as UploadIcon, ScanText, Brain, ShieldCheck, GitBranch } from 'lucide-react';
import { invoiceAPI } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import Alert from '../components/ui/Alert';

const PIPELINE_STEPS = [
  { label: 'Upload', description: 'Document storage', icon: UploadIcon },
  { label: 'OCR', description: 'Text extraction', icon: ScanText },
  { label: 'Extraction', description: 'Field identification', icon: Brain },
  { label: 'Validation', description: 'Data integrity', icon: ShieldCheck },
  { label: 'Routing', description: 'Confidence-based', icon: GitBranch },
];

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
      <PageHeader
        title="Upload Document"
        description="Upload invoices, receipts, or other documents for AI-powered extraction."
      />

      <div className="max-w-3xl space-y-6">
        {/* Upload Area */}
        <div
          className={`relative rounded-xl border-2 border-dashed bg-white p-10 sm:p-12 text-center transition-colors ${
            dragActive
              ? 'border-primary-500 bg-primary-50/60'
              : 'border-slate-300 hover:border-primary-400 hover:bg-slate-50/60'
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
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary-50 ring-8 ring-primary-50/50">
                <UploadCloud className="h-7 w-7 text-primary-600" />
              </div>
              <h3 className="text-base font-semibold text-slate-900">
                Drop your document here
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                or <span className="font-medium text-primary-600">browse files</span>
              </p>
              <p className="mt-4 text-xs text-slate-400">
                Supported formats: PDF, PNG, JPG, JPEG (max 10MB)
              </p>
            </>
          ) : (
            <div className="inline-flex items-center gap-4 rounded-lg border border-slate-200 bg-white px-5 py-4 text-left shadow-card">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
                <FileText className="h-5 w-5 text-primary-600" />
              </div>
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-900">{file.name}</p>
                <p className="text-sm text-slate-500">{formatFileSize(file.size)}</p>
              </div>
            </div>
          )}
        </div>

        {error && <Alert type="error">{error}</Alert>}

        {result && (
          <Alert type="success" title="Upload successful!">
            <p>Document ID: <span className="font-mono">{result.document_id}</span></p>
            <p>Status: {result.status}</p>
            <p className="mt-1 text-slate-500">Redirecting to invoice details...</p>
          </Alert>
        )}

        {file && (
          <div className="flex flex-col-reverse gap-3 sm:flex-row">
            <button
              onClick={() => setFile(null)}
              disabled={uploading}
              className="btn-secondary py-2.5"
            >
              <X className="h-4 w-4" />
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="btn-primary flex-1 py-2.5"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <UploadIcon className="h-4 w-4" />
                  Upload & Process
                </>
              )}
            </button>
          </div>
        )}

        {/* Processing Steps */}
        <div className="card p-6">
          <h3 className="card-title mb-6">Processing Pipeline</h3>
          <ol className="grid grid-cols-1 gap-6 md:grid-cols-5 md:gap-2">
            {PIPELINE_STEPS.map((step, index) => {
              const Icon = step.icon;
              return (
                <li key={step.label} className="relative flex items-center gap-4 md:flex-col md:gap-0 md:text-center">
                  {index < PIPELINE_STEPS.length - 1 && (
                    <span className="absolute left-5 top-10 h-6 w-px bg-slate-200 md:left-1/2 md:top-5 md:h-px md:w-full" />
                  )}
                  <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-50 ring-4 ring-white">
                    <Icon className="h-5 w-5 text-primary-600" />
                  </div>
                  <div className="md:mt-3">
                    <p className="text-sm font-medium text-slate-900">{step.label}</p>
                    <p className="text-xs text-slate-500">{step.description}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </div>
  );
}

export default Upload;
