"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import { FilePreviewData } from "@/lib/types";
import {
  Upload,
  X,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  FileSpreadsheet,
  ArrowRight,
  Loader2,
} from "lucide-react";

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId?: string;
  onDatasetImported: (datasetId: string, filename: string) => void;
  initialFile?: File | null;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  conversationId,
  onDatasetImported,
  initialFile,
}) => {
  const [file, setFile] = useState<File | null>(initialFile || null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [uploadedFileId, setUploadedFileId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<FilePreviewData | null>(null);
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (initialFile) {
      setFile(initialFile);
      uploadAndParse(initialFile);
    }
  }, [initialFile]);

  if (!isOpen) return null;

  const uploadAndParse = async (targetFile: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const res = await api.uploadFile(targetFile, conversationId);
      setUploadedFileId(res.file_id);
      setPreviewData(res.preview);

      const initMap: Record<string, string> = {};
      Object.entries(res.preview.field_mappings).forEach(([col, field]) => {
        if (field) initMap[col] = field;
      });
      setMappings(initMap);
    } catch (err: any) {
      setError(err.message || "Failed to upload and parse file.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      uploadAndParse(selected);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const dropped = e.dataTransfer.files[0];
      setFile(dropped);
      uploadAndParse(dropped);
    }
  };

  const handleConfirmImport = async () => {
    if (!uploadedFileId || !previewData) return;
    setIsImporting(true);
    setError(null);

    try {
      const res = (await api.importDataset(
        uploadedFileId,
        previewData.filename,
        mappings
      )) as any;
      onDatasetImported(res.dataset_id, previewData.filename);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to import dataset records.");
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold text-white text-sm">
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            <span>Upload Student File & Data Extraction</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content body */}
        <div className="p-5 flex-1 overflow-y-auto space-y-4">
          {error && (
            <div className="p-3 bg-rose-950/40 border border-rose-800 text-rose-300 rounded-lg text-xs flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
              {file && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    uploadAndParse(file);
                  }}
                  className="px-2.5 py-1 bg-rose-800/80 hover:bg-rose-700 text-white font-medium rounded text-[11px] transition flex-shrink-0"
                >
                  Retry Upload
                </button>
              )}
            </div>
          )}

          {!previewData ? (
            /* Upload step */
            <div className="space-y-4">
              <div
                onDragOver={handleDragOver}
                onDragEnter={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById("file-input")?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer ${
                  isDragging
                    ? "border-emerald-400 bg-emerald-950/30 scale-[1.01]"
                    : "border-gray-700 hover:border-emerald-500/60 bg-gray-950/40"
                }`}
              >
                {isUploading ? (
                  <div className="space-y-2">
                    <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mx-auto" />
                    <p className="text-sm font-medium text-emerald-300">
                      Uploading and parsing {file?.name}...
                    </p>
                    <p className="text-xs text-gray-500">
                      Detecting column headers and validating email addresses
                    </p>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                    <p className="text-sm font-medium text-gray-200">
                      {isDragging
                        ? "Drop file here to upload"
                        : file
                        ? file.name
                        : "Drag & drop your student file here, or click to browse"}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Supported: CSV, Excel (.xlsx, .xls), PDF, DOCX, TXT, JSON, XML (up to 50MB)
                    </p>
                  </>
                )}
                <input
                  id="file-input"
                  type="file"
                  accept=".csv,.xlsx,.xls,.pdf,.docx,.doc,.txt,.json,.xml"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>
            </div>
          ) : (
            /* Extraction preview and validation step */
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-[11px] text-gray-400 block">Total Rows</span>
                  <span className="text-lg font-bold text-white">
                    {previewData.stats.total_rows}
                  </span>
                </div>
                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-[11px] text-emerald-400 block">Valid Emails</span>
                  <span className="text-lg font-bold text-emerald-400">
                    {previewData.stats.valid_emails}
                  </span>
                </div>
                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-[11px] text-amber-400 block">Missing Emails</span>
                  <span className="text-lg font-bold text-amber-400">
                    {previewData.stats.missing_emails}
                  </span>
                </div>
                <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl text-center">
                  <span className="text-[11px] text-rose-400 block">Duplicates</span>
                  <span className="text-lg font-bold text-rose-400">
                    {previewData.stats.duplicate_emails}
                  </span>
                </div>
              </div>

              {/* Column Mapping Section */}
              <div className="p-3 bg-gray-950/60 border border-gray-800 rounded-xl space-y-2">
                <span className="text-xs font-semibold text-gray-300 block">
                  Detected Column Mappings
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {previewData.columns.map((col) => (
                    <div
                      key={col}
                      className="flex items-center justify-between p-2 bg-gray-900 border border-gray-800 rounded-lg"
                    >
                      <span className="font-medium text-gray-300 truncate max-w-[120px]" title={col}>
                        {col}
                      </span>
                      <select
                        value={mappings[col] || ""}
                        onChange={(e) =>
                          setMappings({ ...mappings, [col]: e.target.value })
                        }
                        className="bg-gray-800 border border-gray-700 text-gray-200 rounded px-2 py-1 text-xs focus:outline-none"
                      >
                        <option value="">(Ignore)</option>
                        <option value="name">Student Name</option>
                        <option value="email">Email Address</option>
                        <option value="task">Assigned Task / Project</option>
                        <option value="department">Department</option>
                        <option value="year">Academic Year</option>
                        <option value="semester">Semester</option>
                        <option value="section">Section</option>
                        <option value="register_number">Register Number</option>
                        <option value="phone">Phone Number</option>
                      </select>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sample Rows Preview */}
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-gray-300 block">
                  Sample Extracted Records
                </span>
                <div className="border border-gray-800 rounded-xl overflow-x-auto max-h-44">
                  <table className="w-full text-xs text-left text-gray-300">
                    <thead className="bg-gray-950 text-gray-400 uppercase text-[10px] sticky top-0">
                      <tr>
                        <th className="p-2">Row</th>
                        <th className="p-2">Status</th>
                        {previewData.columns.slice(0, 4).map((c) => (
                          <th key={c} className="p-2">{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800 bg-gray-900/40">
                      {previewData.sample_rows.map((row) => (
                        <tr key={row.row_index} className="hover:bg-gray-800/40">
                          <td className="p-2 font-mono text-[10px] text-gray-500">
                            {row.row_index}
                          </td>
                          <td className="p-2">
                            {row.is_valid ? (
                              <span className="text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-[10px]">
                                Valid
                              </span>
                            ) : (
                              <span
                                className="text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded text-[10px]"
                                title={row.error}
                              >
                                Review
                              </span>
                            )}
                          </td>
                          {previewData.columns.slice(0, 4).map((c) => (
                            <td key={c} className="p-2 truncate max-w-[120px]">
                              {String(row.data[c] || "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        {previewData && (
          <div className="p-4 border-t border-gray-800 bg-gray-950/60 flex items-center justify-between">
            <button
              onClick={() => {
                setPreviewData(null);
                setFile(null);
              }}
              className="text-xs text-gray-400 hover:text-white transition"
            >
              Choose another file
            </button>
            <button
              onClick={handleConfirmImport}
              disabled={isImporting}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50"
            >
              {isImporting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Importing...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Confirm & Save Dataset</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
