import fs from 'node:fs'
import path from 'node:path'

const distDir = path.resolve('dist', 'assets')
const budgetBytes = 900 * 1024

if (!fs.existsSync(distDir)) {
  console.error('bundle budget check failed: dist/assets does not exist')
  process.exit(1)
}

const offenders = fs
  .readdirSync(distDir)
  .filter((file) => file.endsWith('.js'))
  .map((file) => {
    const fullPath = path.join(distDir, file)
    const size = fs.statSync(fullPath).size
    return { file, size }
  })
  .filter(({ size }) => size > budgetBytes)

if (offenders.length > 0) {
  console.error('bundle budget check failed:')
  for (const offender of offenders) {
    console.error(` - ${offender.file}: ${offender.size} bytes`)
  }
  process.exit(1)
}

console.log('bundle budget: OK')
