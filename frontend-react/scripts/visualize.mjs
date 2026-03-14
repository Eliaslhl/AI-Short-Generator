import { build } from 'vite'
import { visualizer } from 'rollup-plugin-visualizer'

async function run() {
  await build({
    build: {
      sourcemap: true,
      rollupOptions: {
        plugins: [visualizer({ filename: 'dist/stats.html', open: false, gzipSize: true })]
      }
    }
  })
  console.log('Visualizer has written dist/stats.html')
}

run().catch((e) => { console.error(e); process.exit(1) })
