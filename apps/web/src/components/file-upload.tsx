"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

interface FileUploadProps {
  onUpload: (file: File) => void;
  isLoading: boolean;
}

export function FileUpload({ onUpload, isLoading }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);

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
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <Card
        className={`w-full max-w-md mx-auto border-2 border-dashed transition-colors ${dragActive ? "border-primary bg-primary/10" : "border-gray-200"}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
    >
      <CardContent className="flex flex-col items-center justify-center py-10 space-y-4">
        <div className="text-center">
            <h3 className="text-md font-semibold">Upload Bank Statement</h3>
            <p className="text-sm text-gray-500">Drag & drop CSV file or click to browse</p>
        </div>

        <input
            type="file"
            id="file-upload"
            className="hidden"
            accept=".csv, .txt"
            onChange={handleChange}
        />

        {!file ? (
            <Button variant="outline" onClick={() => document.getElementById('file-upload')?.click()}>
                Select File
            </Button>
        ) : (
            <div className="flex flex-col items-center space-y-4 w-full">
                <div className="flex items-center space-x-2 bg-gray-50 px-3 py-2 rounded text-sm w-full justify-between">
                    <span className="truncate max-w-[200px]">{file.name}</span>
                    <button onClick={() => setFile(null)} className="text-red-500 hover:text-red-700">×</button>
                </div>
                <Button className="w-full" onClick={() => onUpload(file)} disabled={isLoading}>
                    {isLoading ? "Uploading..." : "Start Analysis"}
                </Button>
            </div>
        )}
      </CardContent>
    </Card>
  )
}
