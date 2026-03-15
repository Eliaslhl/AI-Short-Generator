import http from 'http'
import handler from 'serve-handler'
import { chromium } from 'playwright'

const PORT = 4180

async function run() {
  const server = http.createServer((req, res) => handler(req, res, { public: 'dist' }))
  await new Promise((resolve) => server.listen(PORT, resolve))
  console.log('Static server running at http://localhost:' + PORT)

  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'networkidle' })

  // find elements that contain 'Privacy'
  const matches = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('*'))
    return els
      .filter(e => e.textContent && e.textContent.trim().includes('Privacy'))
      .map(e => ({ tag: e.tagName, outer: e.outerHTML.slice(0, 500) }))
  })
  console.log('Matches:', JSON.stringify(matches, null, 2))

  await browser.close()
  server.close()
  process.exit(0)
}

run().catch(e => { console.error(e); process.exit(1) })
