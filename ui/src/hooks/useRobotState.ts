import { useState, useEffect, useCallback, useRef } from 'react'

export interface RobotState {
  is_connected: boolean
  is_running: boolean
  is_paused: boolean
  safety_status: string
  safety_zone: string
  current_pattern: number
  pattern_name: string
  target_force: number
  current_force: number
  tcp_pose: number[]
  comfort_emoji: string
  comfort_level: number
  timestamp: number
}

interface UseRobotStateOptions {
  pollingInterval?: number
  useWebSocket?: boolean
}

const DEFAULT_STATE: RobotState = {
  is_connected: false,
  is_running: false,
  is_paused: false,
  safety_status: 'unknown',
  safety_zone: 'safe',
  current_pattern: 0,
  pattern_name: 'none',
  target_force: 10.0,
  current_force: 0.0,
  tcp_pose: [0, 0, 0, 0, 0, 0],
  comfort_emoji: '😀',
  comfort_level: 100.0,
  timestamp: 0,
}

export function useRobotState(options: UseRobotStateOptions = {}) {
  const { pollingInterval = 100, useWebSocket = true } = options

  const [state, setState] = useState<RobotState>(DEFAULT_STATE)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const pollingRef = useRef<number | null>(null)

  // Fetch state via REST API
  const fetchState = useCallback(async () => {
    try {
      const response = await fetch('/robot/state')
      if (response.ok) {
        const data = await response.json()
        setState(data)
        setIsConnected(data.is_connected)
        setError(null)
      } else {
        setError('Failed to fetch robot state')
      }
    } catch (err) {
      setError('Connection error')
      setIsConnected(false)
    }
  }, [])

  // Connect via WebSocket
  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/robot-state`

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'state' && message.state) {
            setState(message.state)
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket error')
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        // Attempt reconnect after delay
        setTimeout(connectWebSocket, 3000)
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      setError('Failed to connect')
    }
  }, [])

  // Send command via WebSocket
  const sendCommand = useCallback((action: string, params?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'command',
        action,
        ...params,
      }))
    } else {
      // Fallback to REST API
      fetch('/robot/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...params }),
      }).catch(console.error)
    }
  }, [])

  // Initialize connection
  useEffect(() => {
    if (useWebSocket) {
      connectWebSocket()
    } else {
      // Use polling
      fetchState()
      pollingRef.current = window.setInterval(fetchState, pollingInterval)
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [useWebSocket, pollingInterval, connectWebSocket, fetchState])

  return {
    state,
    isConnected,
    error,
    sendCommand,
    refresh: fetchState,
  }
}

export default useRobotState
