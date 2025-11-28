import React from 'react'
import { VoicePanel } from './components/VoicePanel'
import { FacialExpression } from './components/FacialExpression'
import { useRobotState } from './hooks/useRobotState'

function App() {
  const { state, isConnected, error, sendCommand, refresh } = useRobotState({
    useWebSocket: true,
    pollingInterval: 100,
  })

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🤖</span>
            <div>
              <h1 className="text-xl font-bold text-gray-800">
                UR10e 語音按摩控制系統
              </h1>
              <p className="text-sm text-gray-500">
                Voice-Controlled Massage Robot
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Connection status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isConnected ? 'bg-success' : 'bg-error'
                }`}
              />
              <span className="text-sm text-gray-600">
                {isConnected ? '已連接' : '未連接'}
              </span>
            </div>

            {/* Refresh button */}
            <button
              onClick={refresh}
              className="btn-secondary text-sm"
              title="Refresh"
            >
              🔄 刷新
            </button>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-error text-white px-4 py-2 text-center text-sm">
          {error}
        </div>
      )}

      {/* Main content - Two panels */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-180px)]">
          {/* Left Panel - Voice Control */}
          <VoicePanel
            robotStatus={state.safety_status}
            isRunning={state.is_running}
            isPaused={state.is_paused}
            patternName={state.pattern_name}
            onCommand={sendCommand}
          />

          {/* Right Panel - Facial Expression */}
          <FacialExpression
            emoji={state.comfort_emoji}
            comfortLevel={state.comfort_level}
            currentForce={state.current_force}
            targetForce={state.target_force}
            safetyZone={state.safety_zone}
          />
        </div>

        {/* Status bar */}
        <div className="mt-6 bg-white rounded-xl shadow-sm p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 text-sm">
            <StatusItem
              label="安全狀態"
              value={state.safety_status}
              highlight={state.safety_zone !== 'safe'}
            />
            <StatusItem
              label="當前模式"
              value={state.pattern_name === 'none' ? '無' : state.pattern_name}
            />
            <StatusItem
              label="目標力度"
              value={`${state.target_force.toFixed(1)} N`}
            />
            <StatusItem
              label="當前力度"
              value={`${state.current_force.toFixed(1)} N`}
              highlight={state.current_force > 25}
            />
            <StatusItem
              label="舒適度"
              value={`${state.comfort_level.toFixed(0)}%`}
            />
            <StatusItem
              label="更新時間"
              value={new Date(state.timestamp * 1000).toLocaleTimeString()}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-sm text-gray-400">
        UR10e Voice Massage Control v1.0 | 語音控制按摩機器人系統
      </footer>
    </div>
  )
}

interface StatusItemProps {
  label: string
  value: string
  highlight?: boolean
}

function StatusItem({ label, value, highlight = false }: StatusItemProps) {
  return (
    <div className="flex flex-col">
      <span className="text-gray-500 text-xs">{label}</span>
      <span
        className={`font-medium ${highlight ? 'text-error' : 'text-gray-800'}`}
      >
        {value}
      </span>
    </div>
  )
}

export default App
