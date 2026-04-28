"use client";
import { useState } from "react";

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <button
      onClick={handleCopy}
      className="text-xs px-2.5 py-1 rounded border border-gray-300 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}
