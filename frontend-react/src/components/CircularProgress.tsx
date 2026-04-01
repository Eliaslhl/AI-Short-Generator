import React from 'react'

interface CircularProgressProps {
  progress: number // 0-100
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'success' | 'warning' | 'error'
  label?: string
}

/**
 * Circular animated progress indicator
 * Great for showing current status at a glance
 */
export const CircularProgress: React.FC<CircularProgressProps> = ({
  progress,
  size = 'md',
  variant = 'default',
  label,
}) => {
  const normalizedProgress = Math.max(0, Math.min(100, progress))
  
  // Size configuration
  const sizes = {
    sm: { container: 'w-20 h-20', text: 'text-lg', label: 'text-xs' },
    md: { container: 'w-28 h-28', text: 'text-2xl', label: 'text-sm' },
    lg: { container: 'w-40 h-40', text: 'text-4xl', label: 'text-base' },
  }
  
  // Color configuration
  const colors = {
    default: {
      bg: 'from-purple-600 to-pink-600',
      text: 'text-purple-300',
      trail: 'stroke-purple-900/30',
    },
    success: {
      bg: 'from-green-600 to-emerald-600',
      text: 'text-green-300',
      trail: 'stroke-green-900/30',
    },
    warning: {
      bg: 'from-yellow-600 to-orange-600',
      text: 'text-yellow-300',
      trail: 'stroke-yellow-900/30',
    },
    error: {
      bg: 'from-red-600 to-pink-600',
      text: 'text-red-300',
      trail: 'stroke-red-900/30',
    },
  }

  const sizeConfig = sizes[size]
  const colorConfig = colors[variant]
  const circumference = 2 * Math.PI * 45 // radius = 45
  const strokeDashoffset = circumference - (normalizedProgress / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-3">
      <div className={`${sizeConfig.container} relative flex items-center justify-center`}>
        {/* SVG circular progress */}
        <svg className="absolute inset-0 transform -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            className={`${colorConfig.trail}`}
            strokeWidth="3"
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            className={`stroke-gradient transition-all duration-500`}
            stroke={`url(#gradient-${variant})`}
            strokeWidth="3"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
          {/* Gradient definition */}
          <defs>
            <linearGradient id={`gradient-${variant}`} x1="0%" y1="0%" x2="100%" y2="100%">
              {variant === 'default' && (
                <>
                  <stop offset="0%" stopColor="#a855f7" />
                  <stop offset="100%" stopColor="#ec4899" />
                </>
              )}
              {variant === 'success' && (
                <>
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#059669" />
                </>
              )}
              {variant === 'warning' && (
                <>
                  <stop offset="0%" stopColor="#f59e0b" />
                  <stop offset="100%" stopColor="#d97706" />
                </>
              )}
              {variant === 'error' && (
                <>
                  <stop offset="0%" stopColor="#ef4444" />
                  <stop offset="100%" stopColor="#ec4899" />
                </>
              )}
            </linearGradient>
          </defs>
        </svg>

        {/* Center text */}
        <div className="flex flex-col items-center gap-1">
          <span className={`${sizeConfig.text} font-bold ${colorConfig.text}`}>
            {Math.round(normalizedProgress)}%
          </span>
          {label && <span className={`${sizeConfig.label} text-gray-400 text-center`}>{label}</span>}
        </div>
      </div>
    </div>
  )
}

export default CircularProgress
