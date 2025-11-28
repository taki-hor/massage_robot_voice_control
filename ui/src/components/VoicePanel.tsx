import React, { useState, useCallback } from 'react'

interface Intent {
  action: string
  pattern: string | null
  force_delta: number | null
  region: string | null
  confidence: number
  raw_text: string
}

interface VoicePanelProps {
  robotStatus: string
  isRunning: boolean
  isPaused: boolean
  patternName: string
  onCommand: (action: string, params?: Record<string, unknown>) => void
}

export function VoicePanel({
  robotStatus,
  isRunning,
  isPaused,
  patternName,
  onCommand,
}: VoicePanelProps) {
  const [transcript, setTranscript] = useState('')
  const [intent, setIntent] = useState<Intent | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [commandHistory, setCommandHistory] = useState<string[]>([])

  // Process voice command
  const processCommand = useCallback(async (text: string) => {
    if (!text.trim()) return

    setIsProcessing(true)
    try {
      const response = await fetch('/voice/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: text }),
      })

      if (response.ok) {
        const result = await response.json()
        setIntent(result.intent)
        setCommandHistory((prev) => [
          `${result.intent.action}: ${result.message}`,
          ...prev.slice(0, 4),
        ])
      }
    } catch (err) {
      console.error('Command processing error:', err)
    } finally {
      setIsProcessing(false)
    }
  }, [])

  // Handle text input submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (transcript.trim()) {
      processCommand(transcript)
      setTranscript('')
    }
  }

  // Quick command buttons
  const quickCommands = [
    { label: '開始', action: 'start', icon: '▶️' },
    { label: '暫停', action: 'pause', icon: '⏸️' },
    { label: '繼續', action: 'resume', icon: '▶️' },
    { label: '停止', action: 'stop', icon: '⏹️' },
    { label: '大力', action: 'harder', icon: '💪' },
    { label: '輕點', action: 'softer', icon: '🪶' },
  ]

  // Pattern buttons
  const patterns = [
    { name: 'linear', label: '直線推', icon: '➡️' },
    { name: 'circular', label: '打圈', icon: '🔄' },
    { name: 'trigger', label: '點按', icon: '👆' },
    { name: 'kneading', label: '揉捏', icon: '✊' },
  ]

  // Get status badge style
  const getStatusBadge = () => {
    if (isRunning) return 'status-badge-success'
    if (isPaused) return 'status-badge-warning'
    return 'status-badge-info'
  }

  const getStatusText = () => {
    if (isRunning) return '運行中'
    if (isPaused) return '已暫停'
    return '已停止'
  }

  return (
    <div className="panel h-full flex flex-col">
      <h2 className="panel-header flex items-center gap-2">
        <span>🎤</span>
        <span>語音控制面板 / Voice Control</span>
      </h2>

      <div className="flex-1 flex flex-col space-y-4 overflow-hidden">
        {/* Status display */}
        <div className="flex items-center justify-between bg-gray-50 rounded-xl p-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">狀態:</span>
            <span className={getStatusBadge()}>{getStatusText()}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">模式:</span>
            <span className="text-sm font-medium text-primary-600">
              {patternName === 'none' ? '無' : patternName}
            </span>
          </div>
        </div>

        {/* Voice input (text simulation) */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="輸入語音指令... / Type voice command..."
            className="flex-1 px-4 py-2 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none transition-all"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={isProcessing || !transcript.trim()}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? '處理中...' : '發送'}
          </button>
        </form>

        {/* Current intent display */}
        {intent && (
          <div className="bg-primary-50 rounded-xl p-3 animate-in">
            <div className="text-sm text-primary-600 font-medium mb-1">
              解析意圖 / Parsed Intent
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">動作: </span>
                <span className="font-medium">{intent.action}</span>
              </div>
              {intent.pattern && (
                <div>
                  <span className="text-gray-500">模式: </span>
                  <span className="font-medium">{intent.pattern}</span>
                </div>
              )}
              {intent.force_delta && (
                <div>
                  <span className="text-gray-500">力度: </span>
                  <span className="font-medium">
                    {intent.force_delta > 0 ? '+' : ''}
                    {intent.force_delta}N
                  </span>
                </div>
              )}
              <div>
                <span className="text-gray-500">信心: </span>
                <span className="font-medium">{(intent.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        )}

        {/* Quick commands */}
        <div>
          <div className="text-sm text-gray-500 mb-2">快捷指令 / Quick Commands</div>
          <div className="grid grid-cols-3 gap-2">
            {quickCommands.map((cmd) => (
              <button
                key={cmd.action}
                onClick={() => {
                  onCommand(cmd.action)
                  setCommandHistory((prev) => [`${cmd.action}: 已執行`, ...prev.slice(0, 4)])
                }}
                className="btn-secondary text-sm py-3"
              >
                <span className="mr-1">{cmd.icon}</span>
                {cmd.label}
              </button>
            ))}
          </div>
        </div>

        {/* Pattern selection */}
        <div>
          <div className="text-sm text-gray-500 mb-2">按摩模式 / Patterns</div>
          <div className="grid grid-cols-2 gap-2">
            {patterns.map((p) => (
              <button
                key={p.name}
                onClick={() => {
                  onCommand('start', { pattern: p.name })
                  setCommandHistory((prev) => [`pattern: ${p.name}`, ...prev.slice(0, 4)])
                }}
                className={`btn text-sm py-3 ${
                  patternName === p.name
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="mr-1">{p.icon}</span>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Command history */}
        <div className="flex-1 overflow-hidden">
          <div className="text-sm text-gray-500 mb-2">指令歷史 / History</div>
          <div className="bg-gray-50 rounded-xl p-3 h-full overflow-y-auto">
            {commandHistory.length === 0 ? (
              <div className="text-sm text-gray-400 text-center py-4">
                暫無指令 / No commands yet
              </div>
            ) : (
              <ul className="space-y-1">
                {commandHistory.map((cmd, i) => (
                  <li key={i} className="text-sm text-gray-600 animate-in">
                    <span className="text-gray-400 mr-2">›</span>
                    {cmd}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default VoicePanel
