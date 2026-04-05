import { useEffect } from 'react'

interface SeoConfig {
  title: string
  description: string
  ogTitle?: string
  ogDescription?: string
  ogImage?: string
  ogUrl?: string
  ogType?: string
  keywords?: string
}

export function useSeoTags(config: SeoConfig) {
  useEffect(() => {
    // Set page title
    document.title = config.title

    // Set meta description
    let descMeta = document.querySelector('meta[name="description"]')
    if (!descMeta) {
      descMeta = document.createElement('meta')
      descMeta.setAttribute('name', 'description')
      document.head.appendChild(descMeta)
    }
    descMeta.setAttribute('content', config.description)

    // Set keywords if provided
    if (config.keywords) {
      let keywordsMeta = document.querySelector('meta[name="keywords"]')
      if (!keywordsMeta) {
        keywordsMeta = document.createElement('meta')
        keywordsMeta.setAttribute('name', 'keywords')
        document.head.appendChild(keywordsMeta)
      }
      keywordsMeta.setAttribute('content', config.keywords)
    }

    // Set OG tags for social sharing
    const ogTags = [
      { property: 'og:title', content: config.ogTitle || config.title },
      { property: 'og:description', content: config.ogDescription || config.description },
      { property: 'og:type', content: config.ogType || 'website' },
    ]

    if (config.ogImage) {
      ogTags.push({ property: 'og:image', content: config.ogImage })
    }

    if (config.ogUrl) {
      ogTags.push({ property: 'og:url', content: config.ogUrl })
    }

    // Add Twitter card tags
    const twitterTags = [
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: config.ogTitle || config.title },
      { name: 'twitter:description', content: config.ogDescription || config.description },
    ]

    if (config.ogImage) {
      twitterTags.push({ name: 'twitter:image', content: config.ogImage })
    }

    // Apply OG tags
    ogTags.forEach(({ property, content }) => {
      let tag = document.querySelector(`meta[property="${property}"]`)
      if (!tag) {
        tag = document.createElement('meta')
        tag.setAttribute('property', property)
        document.head.appendChild(tag)
      }
      tag.setAttribute('content', content)
    })

    // Apply Twitter tags
    twitterTags.forEach(({ name, content }) => {
      let tag = document.querySelector(`meta[name="${name}"]`)
      if (!tag) {
        tag = document.createElement('meta')
        tag.setAttribute('name', name)
        document.head.appendChild(tag)
      }
      tag.setAttribute('content', content)
    })

    return () => {
      // Cleanup is optional - can leave tags in place or remove them
    }
  }, [config])
}
