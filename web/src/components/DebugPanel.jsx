/**
 * DebugPanel - Displays request payload, response, and errors clearly.
 * Reusable across all pages for debugging API calls.
 */
export default function DebugPanel({ request, response, error }) {
  return (
    <div className="mt-6 space-y-3">
      {request && (
        <div>
          <h4 className="text-sm font-semibold text-gray-600 mb-1">Request Payload</h4>
          <pre className="bg-gray-900 text-green-400 text-xs rounded p-3 overflow-auto max-h-48">
            {JSON.stringify(request, null, 2)}
          </pre>
        </div>
      )}
      {response !== null && response !== undefined && (
        <div>
          <h4 className="text-sm font-semibold text-gray-600 mb-1">Response</h4>
          <pre className="bg-gray-900 text-blue-300 text-xs rounded p-3 overflow-auto max-h-64">
            {typeof response === 'string' ? response : JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
      {error && (
        <div>
          <h4 className="text-sm font-semibold text-red-600 mb-1">Error</h4>
          <pre className="bg-red-50 text-red-700 text-xs rounded p-3 overflow-auto max-h-48 border border-red-200">
            {error}
          </pre>
        </div>
      )}
    </div>
  )
}