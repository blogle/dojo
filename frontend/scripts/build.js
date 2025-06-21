import { build } from 'vite'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const dryRun = process.argv.includes('--dry-run')

build({}).then(() => {
  if (dryRun) {
    console.log('dry run complete')
  }
}).catch((err) => {
  console.error(err)
  process.exit(1)
})
