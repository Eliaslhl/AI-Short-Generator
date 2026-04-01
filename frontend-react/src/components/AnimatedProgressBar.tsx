import React from 'react'
import '../styles/animations.css'

interface AnimatedProgressBarProps {
  progress: number // 0-100
  label?: string
  showPercentage?: boolean
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'success' | 'warning' | 'error'
  animated?: boolean
}

/**
 * Animated progress bar component with shimmer effect
 * Perfect for downloads, uploads, and processing status
 */
export const AnimatedProgressBar: React.FC<AnimatedProgressBarProps> = ({
  progress,
  label = 'Progression',
  showPercentage = true,
  size = 'md',
  variant = 'default',
  animated = true,
}) => {
  // Ensure progress is between 0 and 100
  const normalizedProgress = Math.max(0, Math.min(100, progress))

  // Size classes
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  }

  // Variant gradient classes
  const variantClasses = {
    default: 'from-purple-500 via-pink-500 to-purple-500',
    success: 'from-green-500 via-emerald-400 to-green-500',
    warning: 'from-yellow-500 via-orange-500 to-yellow-500',
    error: 'from-red-500 via-pink-500 to-red-500',
  }

  return (
    <div className="w-full">
      {/* Progress bar container */}
      <div className={`${sizeClasses[size]} bg-white/10 rounded-full overflow-hidden relative`}>
        {/* Background gradient bar */}
        <div
          className={`h-full bg-gradient-to-r ${variantClasses[variant]} rounded-full transition-all ${
            animated ? 'duration-500' : 'duration-200'
          }`}
          style={{ width: `${normalizedProgress}%` }}
        />

        {/* Shimmer effect overlay - only when animating and not complete */}
        {animated && normalizedProgress > 0 && normalizedProgress < 100 && (
          <div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-pulse"
            style={{ width: `${normalizedProgress}%` }}
          />
        )}

        {/* Glow effect for completion */}
        {normalizedProgress === 100 && (
          <div className="absolute inset-0 bg-white/20 animate-pulse" />
        )}
      </div>

      {/* Label and percentage */}
      {(label || showPercentage) && (
        <div className="flex justify-between items-center mt-2">
          {label && <span className="text-xs text-gray-400">{label}</span>}
          {showPercentage && (
            <span
              className={`text-xs font-semibold ${
                variant === 'default'
                  ? 'text-purple-300'
                  : variant === 'success'
                  ? 'text-green-300'
                  : variant === 'warning'
                  ? 'text-yellow-300'
                  : 'text-red-300'
              }`}
            >
              {Math.round(normalizedProgress)}%
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default AnimatedProgressBar
