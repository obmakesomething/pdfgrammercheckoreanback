import { promises as fs } from 'node:fs'
import path from 'node:path'

const cwd = process.cwd()

const src = path.join(cwd, 'pdfgrammercheckorean.ait')
const dest = path.join(cwd, 'pdgrammercheckorean.ait')

async function exists(p) {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

async function main() {
  if (!(await exists(src))) {
    // Nothing to rename.
    return
  }

  if (await exists(dest)) {
    await fs.unlink(dest)
  }

  await fs.rename(src, dest)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
