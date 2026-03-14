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

  // accept first
  const accept = await page.$('text=Accepter')
  if (!accept) {
    console.error('Accept button not found')
    process.exit(2)
  }
  await accept.click()
  await page.waitForTimeout(1000)

  const hasAnalytics = async () => {
    return await page.evaluate(() => Array.from(document.scripts).some(s => s.src && (s.src.includes('googletagmanager.com/gtm.js') || s.src.includes('googletagmanager.com/gtag/js'))))
  }

  console.log('After accept — analytics present?', await hasAnalytics())

  // open cookie settings
  const settingsBtn = await page.$('text=Cookies')
  if (!settingsBtn) {
    console.error('Cookies settings button not found')
    process.exit(3)
  }
  await settingsBtn.click()
  await page.waitForTimeout(300)

  const revokeBtn = await page.$('text=Révoquer le consentement')
  if (!revokeBtn) {
    console.error('Revoke button not found')
    process.exit(4)
  }
  await revokeBtn.click()
  await page.waitForTimeout(500)

  const analyticsAfterRevoke = await hasAnalytics()
  const consent = await page.evaluate(() => localStorage.getItem('cookie_consent'))
  console.log('After revoke — analytics present?', analyticsAfterRevoke)
  console.log('localStorage.cookie_consent =', consent)

  await browser.close()
  server.close()

  if (consent !== 'false' || analyticsAfterRevoke) {
    console.error('Revoke failed')
    process.exit(5)
  }

  console.log('Revoke flow: OK')
  process.exit(0)
}

run().catch(e => { console.error(e); process.exit(1) })
