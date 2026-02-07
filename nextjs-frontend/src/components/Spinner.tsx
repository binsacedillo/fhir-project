import React from "react";

export default function Spinner({ size = 32, color = "#2563eb" }: { size?: number; color?: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: `3px solid ${color}33`,
        borderTop: `3px solid ${color}`,
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }}
    />
  );
}

// Add global spinner keyframes (inject into <style> in _app or layout if needed)
if (typeof window !== "undefined") {
  const style = document.createElement("style");
  style.innerHTML = `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`;
  document.head.appendChild(style);
}
