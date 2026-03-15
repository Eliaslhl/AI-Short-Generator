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

  const privacy = await page.$('text=Privacy')
  if (!privacy) {
    console.error('Privacy link not found')
    await browser.close()
    server.close()
    process.exit(2)
  }
  await privacy.click()
  await page.waitForTimeout(500)
  console.log('After click, URL =', page.url())

  // Also try clicking link with href
  const anchor = await page.$('a[href="/privacy"]')
  if (anchor) {
    await anchor.click()
    await page.waitForTimeout(500)
    console.log('After anchor click, URL =', page.url())
  }

  await browser.close()
  server.close()
  process.exit(0)
}

run().catch(e => { console.error(e); process.exit(1) })
