import React from 'react'

interface FacialExpressionProps {
  emoji: string
  comfortLevel: number
  currentForce: number
  targetForce: number
  safetyZone: string
}

export function FacialExpression({
  emoji,
  comfortLevel,
  currentForce,
  targetForce,
  safetyZone,
}: FacialExpressionProps) {
  // Determine comfort bar color based on level
  const getComfortColor = (level: number) => {
    if (level >= 70) return 'bg-success'
    if (level >= 40) return 'bg-warning'
    return 'bg-error'
  }

  // Determine safety badge style
  const getSafetyBadgeClass = (zone: string) => {
    switch (zone) {
      case 'safe':
        return 'status-badge-success'
      case 'warning':
        return 'status-badge-warning'
      case 'critical':
        return 'status-badge-error'
      default:
        return 'status-badge-info'
    }
  }

  return (
    <div className="panel h-full flex flex-col">
      <h2 className="panel-header flex items-center gap-2">
        <span>😊</span>
        <span>舒適度面板 / Comfort Panel</span>
      </h2>

      <div className="flex-1 flex flex-col items-center justify-center space-y-6">
        {/* Main emoji display */}
        <div className="relative">
          <div
            className="emoji-display text-9xl transition-all duration-300 animate-bounce-gentle"
            role="img"
            aria-label={`Comfort level: ${comfortLevel.toFixed(0)}%`}
          >
            {emoji}
          </div>

          {/* Safety zone indicator */}
          <div className="absolute -top-2 -right-2">
            <span className={getSafetyBadgeClass(safetyZone)}>
              {safetyZone === 'safe' ? '安全' : safetyZone === 'warning' ? '注意' : '危險'}
            </span>
          </div>
        </div>

        {/* Comfort level bar */}
        <div className="w-full max-w-xs">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>舒適度 / Comfort</span>
            <span>{comfortLevel.toFixed(0)}%</span>
          </div>
          <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${getComfortColor(comfortLevel)} transition-all duration-300`}
              style={{ width: `${Math.max(0, Math.min(100, comfortLevel))}%` }}
            />
          </div>
        </div>

        {/* Force display */}
        <div className="grid grid-cols-2 gap-4 w-full max-w-xs">
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <div className="text-sm text-gray-500 mb-1">當前力度 / Current</div>
            <div className="text-2xl font-bold text-primary-600">
              {currentForce.toFixed(1)}
              <span className="text-sm font-normal text-gray-400 ml-1">N</span>
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <div className="text-sm text-gray-500 mb-1">目標力度 / Target</div>
            <div className="text-2xl font-bold text-secondary-600">
              {targetForce.toFixed(1)}
              <span className="text-sm font-normal text-gray-400 ml-1">N</span>
            </div>
          </div>
        </div>

        {/* Comfort legend */}
        <div className="flex gap-4 text-sm text-gray-500">
          <div className="flex items-center gap-1">
            <span className="emoji-display">😀</span>
            <span>舒適</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="emoji-display">😐</span>
            <span>適中</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="emoji-display">😖</span>
            <span>不適</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FacialExpression
