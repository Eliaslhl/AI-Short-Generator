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

  const info = await page.evaluate(() => {
    const a = document.querySelector('a[href="/privacy"]')
    if (!a) return { error: 'not found' }
    const r = a.getBoundingClientRect()
    const cx = r.left + r.width/2
    const cy = r.top + r.height/2
    const topEl = document.elementFromPoint(cx, cy)
    return {
      tag: a.tagName,
      outer: a.outerHTML.slice(0, 500),
      rect: { x: r.x, y: r.y, width: r.width, height: r.height },
      topAtCenter: topEl ? topEl.outerHTML && topEl.tagName : null,
      pointerEvents: window.getComputedStyle(a).pointerEvents
    }
  })

  console.log('Inspect:', info)

  await browser.close()
  server.close()
  process.exit(0)
}

run().catch(e => { console.error(e); process.exit(1) })
