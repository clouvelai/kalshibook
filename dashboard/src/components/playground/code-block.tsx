"use client";

import { useState } from "react";
import { Highlight, themes } from "prism-react-renderer";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CodeBlockProps {
  code: string;
  language: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  }

  return (
    <div className="relative group">
      {/* Copy button */}
      <button
        type="button"
        onClick={handleCopy}
        className="absolute top-3 right-3 z-10 p-1.5 rounded-md text-gray-400 hover:text-white transition-colors"
        aria-label="Copy code"
      >
        {copied ? (
          <Check className="size-4" />
        ) : (
          <Copy className="size-4" />
        )}
      </button>

      {/* Syntax highlighted code */}
      <Highlight theme={themes.vsDark} code={code} language={language}>
        {({ style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className="bg-[#1e1e1e] rounded-lg overflow-x-auto text-sm p-4 pr-12"
            style={{ ...style, backgroundColor: "#1e1e1e" }}
          >
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })}>
                {line.map((token, key) => (
                  <span key={key} {...getTokenProps({ token })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </div>
  );
}
