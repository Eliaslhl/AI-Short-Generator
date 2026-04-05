/**
 * AnimatedProgressBar Component Examples
 * 
 * This file demonstrates all the different ways to use the AnimatedProgressBar component
 * with different sizes, variants, and configurations.
 */

import { useEffect } from 'react'
import { useSeoTags } from '../hooks/useSeoTags'
import { AnimatedProgressBar } from '../components/AnimatedProgressBar'
import { CircularProgress } from '../components/CircularProgress'

export const ProgressBarShowcase = () => {
  useSeoTags({
    title: 'Progress Bar Showcase - AI Shorts Generator',
    description: 'Progress bar component examples and demonstrations.',
  })

  // Add noindex meta tag
  useEffect(() => {
    let robotsMeta = document.querySelector('meta[name="robots"]')
    if (!robotsMeta) {
      robotsMeta = document.createElement('meta')
      robotsMeta.setAttribute('name', 'robots')
      document.head.appendChild(robotsMeta)
    }
    robotsMeta.setAttribute('content', 'noindex, nofollow')
  }, [])
  return (
    <div className="p-8 space-y-16 bg-black/20 rounded-lg">
      <h2 className="text-2xl font-bold text-white mb-8">Progress Bar Showcase</h2>

      {/* Size variations */}
      <section>
        <h3 className="text-lg font-semibold text-purple-300 mb-6">Size Variations</h3>
        <div className="space-y-8">
          <div>
            <p className="text-sm text-gray-400 mb-3">Small</p>
            <AnimatedProgressBar progress={45} size="sm" label="Small progress" />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-3">Medium (Default)</p>
            <AnimatedProgressBar progress={65} size="md" label="Medium progress" />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-3">Large</p>
            <AnimatedProgressBar progress={85} size="lg" label="Large progress" />
          </div>
        </div>
      </section>

      {/* Variant variations */}
      <section>
        <h3 className="text-lg font-semibold text-purple-300 mb-6">Color Variants</h3>
        <div className="space-y-8">
          <div>
            <p className="text-sm text-gray-400 mb-3">Default (Purple)</p>
            <AnimatedProgressBar progress={50} variant="default" label="Default variant" />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-3">Success (Green)</p>
            <AnimatedProgressBar progress={100} variant="success" label="Success variant" />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-3">Warning (Orange)</p>
            <AnimatedProgressBar progress={75} variant="warning" label="Warning variant" />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-3">Error (Red)</p>
            <AnimatedProgressBar progress={30} variant="error" label="Error variant" />
          </div>
        </div>
      </section>

      {/* Different progress levels */}
      <section>
        <h3 className="text-lg font-semibold text-purple-300 mb-6">Progress Levels</h3>
        <div className="space-y-6">
          <div>
            <p className="text-sm text-gray-400 mb-2">0% Complete</p>
            <AnimatedProgressBar progress={0} label="Just started" />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-2">25% Complete</p>
            <AnimatedProgressBar progress={25} />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-2">50% Complete</p>
            <AnimatedProgressBar progress={50} />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-2">75% Complete</p>
            <AnimatedProgressBar progress={75} />
          </div>
          <div>
            <p className="text-sm text-gray-400 mb-2">100% Complete</p>
            <AnimatedProgressBar progress={100} label="Finished!" />
          </div>
        </div>
      </section>

      {/* Circular progress examples */}
      <section>
        <h3 className="text-lg font-semibold text-purple-300 mb-6">Circular Progress</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <CircularProgress progress={25} size="sm" variant="default" label="Downloading..." />
          </div>
          <div>
            <CircularProgress progress={50} size="md" variant="success" label="Processing" />
          </div>
          <div>
            <CircularProgress progress={75} size="lg" variant="warning" label="Almost done" />
          </div>
          <div>
            <CircularProgress progress={100} size="md" variant="success" label="Complete!" />
          </div>
        </div>
      </section>

      {/* Without percentage display */}
      <section>
        <h3 className="text-lg font-semibold text-purple-300 mb-6">Options: Hide Percentage</h3>
        <div className="space-y-6">
          <AnimatedProgressBar progress={60} showPercentage={false} label="Processing video..." />
          <AnimatedProgressBar progress={40} showPercentage={false} label="Uploading clips..." />
        </div>
      </section>

      {/* Real-world example: Multi-step download */}
      <section>
        <h3 className="text-lg font-semibold text-purple-300 mb-6">Real-world Example: Download Flow</h3>
        <div className="space-y-12 bg-white/5 p-6 rounded-lg">
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-4">Step 1: Downloading Video</h4>
            <AnimatedProgressBar progress={30} label="Downloading from YouTube..." size="md" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-4">Step 2: Processing Clips</h4>
            <AnimatedProgressBar progress={60} label="Extracting and processing clips..." size="md" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-4">Step 3: Generating Subtitles</h4>
            <AnimatedProgressBar progress={90} label="Adding subtitles to video..." size="md" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-4">Completed!</h4>
            <AnimatedProgressBar
              progress={100}
              variant="success"
              label="Ready to download"
              size="md"
            />
          </div>
        </div>
      </section>
    </div>
  )
}

export default ProgressBarShowcase
