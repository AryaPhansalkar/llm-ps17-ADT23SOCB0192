// Runs the server's virtual-environment Python inside server/, on any OS.
//   node scripts/python.mjs manage.py runserver 8000
//   node scripts/python.mjs -m ruff check .
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { serverDir, venvPython } from './paths.mjs'

if (!existsSync(venvPython)) {
  console.error('The Python environment has not been created yet. Run "npm run setup" first.')
  process.exit(1)
}

const child = spawn(venvPython, process.argv.slice(2), { cwd: serverDir, stdio: 'inherit' })

child.on('error', (error) => {
  console.error(`Could not start Python: ${error.message}`)
  process.exit(1)
})
child.on('exit', (code, signal) => process.exit(signal ? 1 : (code ?? 1)))

// Ctrl+C reaches Python directly from the terminal; this keeps Node alive until Python has shut down.
process.on('SIGINT', () => {})
process.on('SIGTERM', () => child.kill('SIGTERM'))
