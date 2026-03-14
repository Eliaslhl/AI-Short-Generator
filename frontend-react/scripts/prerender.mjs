import { build } from 'vite'
import http from 'http'
import handler from 'serve-handler'
import { chromium } from 'playwright'
import fs from 'fs'
import path from 'path'

const ROUTES = [
  '/',
  '/seo/ai-shorts-generator',
  '/seo/youtube-shorts-generator',
  '/seo/convert-youtube-to-shorts',
]

async function run() {
  console.log('Building project...')
  await build()
  console.log('Build complete. Starting static server...')

  const server = http.createServer((req, res) => handler(req, res, { public: 'dist' }))
  await new Promise((resolve) => server.listen(4173, resolve))
  console.log('Server running at http://localhost:4173')

  const browser = await chromium.launch()
  const page = await browser.newPage()

  for (const route of ROUTES) {
    const url = `http://localhost:4173${route}`
    console.log('Rendering', url)
    try {
      await page.goto(url, { waitUntil: 'networkidle' })
      const html = await page.content()
      // Write to dist/<route>/index.html (for / -> dist/index.html already exists)
      if (route === '/') {
        await fs.promises.writeFile(path.resolve('dist/index.html'), html, 'utf-8')
      } else {
        const outDir = path.resolve('dist', route.replace(/^\//, ''))
        await fs.promises.mkdir(outDir, { recursive: true })
        await fs.promises.writeFile(path.join(outDir, 'index.html'), html, 'utf-8')
      }
      console.log('Wrote static HTML for', route)
    } catch (e) {
      console.error('Failed to prerender', route, e)
    }
  }

  await browser.close()
  server.close()
  console.log('Prerender complete. Files written to dist/')
}

run().catch((e) => { console.error(e); process.exit(1) })
