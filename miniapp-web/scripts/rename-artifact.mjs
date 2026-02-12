import { promises as fs } from 'node:fs'
import path from 'node:path'

const cwd = process.cwd()

const src = path.join(cwd, 'pdfgrammercheckorean.ait')
const dest = path.join(cwd, 'pdgrammercheckorean.ait')
const rootCopy = path.join(cwd, '..', 'pdgrammercheckorean.ait')
const manifestPath = path.join(cwd, '.granite', 'app.json')
const deepLinkFileName = 'pdgrammercheckorean.intoss-private.txt'
const deepLinkLocalPath = path.join(cwd, deepLinkFileName)
const deepLinkRootPath = path.join(cwd, '..', deepLinkFileName)

async function exists(p) {
  try {
    await fs.access(p)
    return true
  } catch {
    return false
  }
}

async function writeTextFile(filePath, content) {
  if (await exists(filePath)) {
    await fs.unlink(filePath)
  }
  await fs.writeFile(filePath, content, 'utf8')
}

async function readPrivateDeepLink() {
  if (!(await exists(manifestPath))) return null

  try {
    const raw = await fs.readFile(manifestPath, 'utf8')
    const parsed = JSON.parse(raw)
    const appName = typeof parsed?.appName === 'string' ? parsed.appName : ''
    const deploymentId =
      typeof parsed?._metadata?.deploymentId === 'string'
        ? parsed._metadata.deploymentId
        : ''

    if (!appName || !deploymentId) return null
    return `intoss-private://${appName}?_deploymentId=${deploymentId}`
  } catch {
    return null
  }
}

async function main() {
  if (await exists(src)) {
    if (await exists(dest)) {
      await fs.unlink(dest)
    }

    await fs.rename(src, dest)
  }

  if (!(await exists(dest))) {
    // Nothing to copy.
    return
  }

  if (await exists(rootCopy)) {
    await fs.unlink(rootCopy)
  }

  await fs.copyFile(dest, rootCopy)

  const privateDeepLink = await readPrivateDeepLink()
  if (!privateDeepLink) return

  const content = `${privateDeepLink}\n`
  await writeTextFile(deepLinkLocalPath, content)
  await writeTextFile(deepLinkRootPath, content)
  console.log(`Private deep link saved: ${privateDeepLink}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
