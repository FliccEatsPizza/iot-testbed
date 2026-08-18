import React from 'react';
import { useEffect } from 'react';
import Prism from 'prismjs';
import 'prismjs/themes/prism.css';

/**
 * PropsTable
 * Renders a table of prop definitions for documenting API fields or component props.
 *
 * @param {{ props: { name: string; type: string; description: string }[] }} props
 */
export function PropsTable({ props: rows }) {
  return (
    <table className="w-full border-collapse mb-4">
      <thead>
        <tr>
          <th className="border px-4 py-2 text-left">Name</th>
          <th className="border px-4 py-2 text-left">Type</th>
          <th className="border px-4 py-2 text-left">Description</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.name} className="even:bg-gray-50">
            <td className="border px-4 py-2 font-mono">{row.name}</td>
            <td className="border px-4 py-2 font-mono italic">{row.type}</td>
            <td className="border px-4 py-2">{row.description}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/**
 * CodeBlock
 * Renders syntax-highlighted code using Prism.
 *
 * @param {{ code: string; language?: string }} props
 */
export function CodeBlock({ code, language = 'bash' }) {
  useEffect(() => {
    Prism.highlightAll();
  }, [code]);

  return (
    <pre className="rounded-lg shadow p-4 overflow-x-auto">
      <code className={`language-${language}`}>{code.trim()}</code>
    </pre>
  );
}

