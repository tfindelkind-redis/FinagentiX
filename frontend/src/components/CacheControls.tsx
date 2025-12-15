import { useState } from 'react'
import { Sparkles, Trash2 } from 'lucide-react'
import { clearSemanticCache, clearToolCache } from '@/lib/api'
import type { CacheOperationResult } from '@/types/api'
import './CacheControls.css'

type OperationState = 'idle' | 'loading' | 'success' | 'error'

interface OperationStatus {
  state: OperationState
  message: string | null
}

const initialStatus: OperationStatus = { state: 'idle', message: null }

function formatClearedMessage(result: CacheOperationResult, label?: string) {
  const count = result.cleared_entries
  const suffix = count === 1 ? 'entry' : 'entries'
  return `${label ? `${label}: ` : ''}Cleared ${count} ${suffix}`
}

export default function CacheControls() {
  const [semanticStatus, setSemanticStatus] = useState<OperationStatus>(initialStatus)
  const [toolStatus, setToolStatus] = useState<OperationStatus>(initialStatus)
  const [toolName, setToolName] = useState('')

  const handleSemanticClear = async () => {
    setSemanticStatus({ state: 'loading', message: null })
    try {
      const result = await clearSemanticCache()
      setSemanticStatus({
        state: 'success',
        message: formatClearedMessage(result, 'Semantic cache'),
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to clear semantic cache'
      setSemanticStatus({ state: 'error', message })
    }
  }

  const handleToolClear = async () => {
    setToolStatus({ state: 'loading', message: null })
    const trimmed = toolName.trim()
    try {
      const result = await clearToolCache(trimmed || undefined)
      setToolStatus({
        state: 'success',
        message: formatClearedMessage(result, trimmed ? `Tool cache (${trimmed})` : 'Tool cache'),
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to clear tool cache'
      setToolStatus({ state: 'error', message })
    }
  }

  return (
    <div className="cache-controls">
      <div className="cache-action">
        <button
          type="button"
          className={`cache-button ${semanticStatus.state}`}
          onClick={handleSemanticClear}
          disabled={semanticStatus.state === 'loading'}
        >
          <Sparkles size={16} />
          <span>Clear Semantic Cache</span>
        </button>
        {semanticStatus.message && (
          <span className={`cache-status ${semanticStatus.state}`}>{semanticStatus.message}</span>
        )}
      </div>

      <div className="cache-action">
        <div className="tool-input-group">
          <input
            type="text"
            value={toolName}
            onChange={(event) => setToolName(event.target.value)}
            placeholder="Tool name (optional)"
            className="cache-input"
          />
          <button
            type="button"
            className={`cache-button ${toolStatus.state}`}
            onClick={handleToolClear}
            disabled={toolStatus.state === 'loading'}
          >
            <Trash2 size={16} />
            <span>Clear Tool Cache</span>
          </button>
        </div>
        {toolStatus.message && (
          <span className={`cache-status ${toolStatus.state}`}>{toolStatus.message}</span>
        )}
      </div>
    </div>
  )
}
