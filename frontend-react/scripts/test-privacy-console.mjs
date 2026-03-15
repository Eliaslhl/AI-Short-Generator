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

  page.on('console', msg => {
    console.log('PAGE LOG:', msg.type(), msg.text())
  })

  page.on('pageerror', err => {
    console.log('PAGE ERROR:', err.message)
    console.log(err.stack)
  })

  await page.goto(`http://localhost:${PORT}/privacy`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)

  await browser.close()
  server.close()
}

run().catch(e => { console.error(e); process.exit(1) })
