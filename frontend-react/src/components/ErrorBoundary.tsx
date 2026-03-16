import React from 'react'

type Props = {
  children: React.ReactNode
}

type State = {
  hasError: boolean
  error?: Error | null
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: unknown) {
    // Log error to console (dev) — we could wire this to a telemetry service
    // eslint-disable-next-line no-console
    console.error('Unhandled error caught by ErrorBoundary', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white">
          <div className="max-w-xl text-center">
            <h1 className="text-2xl font-semibold mb-2">Something went wrong</h1>
            <p className="text-sm text-gray-300 mb-4">An unexpected error occurred. Check the developer console for details.</p>
            <pre className="text-xs text-left bg-gray-900 p-3 rounded">{String(this.state.error)}</pre>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
