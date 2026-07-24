import { useRef, useState, type DragEvent } from "react";

const ACCEPT = ".pdf,.docx,.pptx,.txt,.md,.csv,.xlsx,.xls";

export function UploadDropzone({ onUpload }: { onUpload: (files: File[]) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    onUpload(Array.from(fileList));
    if (inputRef.current) inputRef.current.value = "";
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center text-sm transition ${
        dragOver ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:bg-gray-50"
      }`}
    >
      <p className="font-medium text-gray-700">Drop documents here or click to browse</p>
      <p className="mt-1 text-xs text-gray-400">PDF, DOCX, PPTX, TXT, MD, CSV, XLSX, XLS — max 25 MB each</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
