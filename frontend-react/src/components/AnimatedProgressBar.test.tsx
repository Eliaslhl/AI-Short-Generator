import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AnimatedProgressBar } from './AnimatedProgressBar'

describe('AnimatedProgressBar', () => {
  it('should render with default props', () => {
    render(<AnimatedProgressBar progress={50} />)
    expect(screen.getByText('Progression')).toBeDefined()
    expect(screen.getByText('50%')).toBeDefined()
  })

  it('should display correct progress percentage', () => {
    const { rerender } = render(<AnimatedProgressBar progress={25} showPercentage={true} />)
    expect(screen.getByText('25%')).toBeDefined()

    rerender(<AnimatedProgressBar progress={75} showPercentage={true} />)
    expect(screen.getByText('75%')).toBeDefined()
  })

  it('should clamp progress between 0 and 100', () => {
    const { rerender } = render(<AnimatedProgressBar progress={-10} showPercentage={true} />)
    expect(screen.getByText('0%')).toBeDefined()

    rerender(<AnimatedProgressBar progress={150} showPercentage={true} />)
    expect(screen.getByText('100%')).toBeDefined()
  })

  it('should not show percentage when showPercentage is false', () => {
    render(<AnimatedProgressBar progress={50} showPercentage={false} />)
    expect(screen.queryByText('50%')).toBeNull()
  })

  it('should show custom label', () => {
    render(<AnimatedProgressBar progress={50} label="Téléchargement" />)
    expect(screen.getByText('Téléchargement')).toBeDefined()
  })

  it('should render different size variants', () => {
    const { container: container1 } = render(<AnimatedProgressBar progress={50} size="sm" />)
    expect(container1.querySelector('.h-2')).toBeDefined()

    const { container: container2 } = render(<AnimatedProgressBar progress={50} size="md" />)
    expect(container2.querySelector('.h-3')).toBeDefined()

    const { container: container3 } = render(<AnimatedProgressBar progress={50} size="lg" />)
    expect(container3.querySelector('.h-4')).toBeDefined()
  })

  it('should apply correct variant colors', () => {
    const { container: containerDefault } = render(
      <AnimatedProgressBar progress={50} variant="default" />
    )
    expect(containerDefault.querySelector('.from-purple-500')).toBeDefined()

    const { container: containerSuccess } = render(
      <AnimatedProgressBar progress={50} variant="success" />
    )
    expect(containerSuccess.querySelector('.from-green-500')).toBeDefined()
  })
})
