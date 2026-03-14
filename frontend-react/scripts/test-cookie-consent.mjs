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

  const url = `http://localhost:${PORT}/`
  await page.goto(url, { waitUntil: 'networkidle' })

  // helper to detect analytics scripts
  const hasAnalytics = async () => {
    return await page.evaluate(() => {
      return Array.from(document.scripts).some(s => s.src && (s.src.includes('googletagmanager.com/gtm.js') || s.src.includes('googletagmanager.com/gtag/js')))
    })
  }

  const consentValue = await page.evaluate(() => localStorage.getItem('cookie_consent'))
  console.log('Initial localStorage.cookie_consent =', consentValue)

  const analyticsBefore = await hasAnalytics()
  console.log('Analytics scripts present before accept?', analyticsBefore)

  // Try to click the accept button in the cookie banner
  const acceptButton = await page.$('text=Accepter')
  if (!acceptButton) {
    console.error('Accept button not found on page')
    await browser.close()
    server.close()
    process.exit(2)
  }

  await acceptButton.click()
  // wait for potential scripts to be appended
  await page.waitForTimeout(1000)

  const analyticsAfter = await hasAnalytics()
  const consentAfter = await page.evaluate(() => localStorage.getItem('cookie_consent'))
  console.log('Analytics scripts present after accept?', analyticsAfter)
  console.log('localStorage.cookie_consent after accept =', consentAfter)

  await browser.close()
  server.close()

  if (analyticsBefore) {
    console.error('Analytics were present before consent — FAIL')
    process.exit(3)
  }
  if (consentAfter !== 'true' || !analyticsAfter) {
    console.error('Consent not recorded or analytics not loaded after accept — FAIL')
    process.exit(4)
  }

  console.log('Cookie consent flow: OK')
  process.exit(0)
}

run().catch(e => { console.error(e); process.exit(1) })
