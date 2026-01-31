"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { FileText, FileSpreadsheet, Upload, X, Loader2 } from "lucide-react"

interface FileUploadProps {
  onUpload: (file: File) => void;
  isLoading: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_SUBSCRIPTION_SERVICE_URL || "http://localhost:8001/v1";

export function FileUpload({ onUpload, isLoading }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [supportedFormats, setSupportedFormats] = useState<string[]>(["csv", "txt"]);
  const [pdfSupported, setPdfSupported] = useState(false);

  useEffect(() => {
    // Fetch capabilities from backend
    fetch(`${API_URL}/capabilities`)
      .then(res => res.json())
      .then(data => {
        if (data.supported_formats) {
          setSupportedFormats(data.supported_formats);
          setPdfSupported(data.pdf_support?.available || false);
        }
      })
      .catch(err => console.warn("Could not fetch capabilities:", err));
  }, []);

  const acceptedTypes = supportedFormats.map(f => `.${f}`).join(", ");

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (isValidFile(droppedFile)) {
        setFile(droppedFile);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (isValidFile(selectedFile)) {
        setFile(selectedFile);
      }
    }
  };

  const isValidFile = (f: File): boolean => {
    const ext = f.name.split('.').pop()?.toLowerCase();
    return ext ? supportedFormats.includes(ext) : false;
  };

  const getFileIcon = () => {
    if (!file) return null;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') {
      return <FileText className="h-5 w-5 text-red-500" />;
    }
    return <FileSpreadsheet className="h-5 w-5 text-green-600" />;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Card
        className={`w-full max-w-lg mx-auto border-2 border-dashed transition-all duration-300 ${
          dragActive 
            ? "border-primary bg-primary/10 scale-[1.02]" 
            : "border-muted-foreground/25 hover:border-muted-foreground/50 dark:border-muted-foreground/20"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
    >
      <CardContent className="flex flex-col items-center justify-center py-10 space-y-4">
        {/* Upload Icon */}
        <div className={`p-4 rounded-full transition-colors ${dragActive ? "bg-primary/20" : "bg-muted"}`}>
          <Upload className={`h-8 w-8 transition-colors ${dragActive ? "text-primary" : "text-muted-foreground"}`} />
        </div>

        {/* Title & Supported Formats */}
        <div className="text-center space-y-1">
            <h3 className="text-lg font-semibold">Upload Bank Statement</h3>
            <p className="text-sm text-muted-foreground">
              Drag & drop or click to browse
            </p>
            <div className="flex items-center justify-center gap-2 mt-2">
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                CSV
              </span>
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                TXT
              </span>
              {pdfSupported ? (
                <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                  PDF (OCR)
                </span>
              ) : (
                <span className="px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground rounded line-through">
                  PDF
                </span>
              )}
            </div>
        </div>

        <input
            type="file"
            id="file-upload"
            className="hidden"
            accept={acceptedTypes}
            onChange={handleChange}
        />

        {!file ? (
            <Button 
              variant="outline" 
              onClick={() => document.getElementById('file-upload')?.click()}
              className="mt-2"
            >
              Select File
            </Button>
        ) : (
            <div className="flex flex-col items-center space-y-4 w-full max-w-sm">
                {/* File Card */}
                <div className="flex items-center space-x-3 bg-muted/50 dark:bg-muted/30 px-4 py-3 rounded-lg w-full border">
                    {getFileIcon()}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                    </div>
                    <button 
                      onClick={() => setFile(null)} 
                      className="p-1 rounded-full hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Action Button */}
                <Button 
                  className="w-full bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 text-white" 
                  onClick={() => onUpload(file)} 
                  disabled={isLoading}
                >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      "Start Analysis"
                    )}
                </Button>
            </div>
        )}
      </CardContent>
    </Card>
  )
}
