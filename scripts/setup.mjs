// One-time setup, the same on Linux, macOS and Windows:
//   1. create the Python virtual environment in server/.venv
//   2. install the Python packages
//   3. create server/.env from the example file
//   4. install the Node packages (for the start commands and for the client)
import { execFileSync, execSync } from 'node:child_process'
import { copyFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { clientDir, rootDir, serverDir, venvPython } from './paths.mjs'

const MIN_PYTHON = [3, 12]

function step(message) {
  console.log(`\n> ${message}`)
}

function fail(message) {
  console.error(`\nSetup stopped: ${message}`)
  process.exit(1)
}

/** Runs one setup action; if it fails, stops with a readable message instead of a stack trace. */
function run(action, failureMessage) {
  try {
    action()
  } catch {
    fail(failureMessage)
  }
}

/** Finds a Python that is new enough. Windows usually has "py" or "python", Linux "python3". */
function findPython() {
  const candidates =
    process.platform === 'win32'
      ? [['py', ['-3']], ['python', []], ['python3', []]]
      : [['python3', []], ['python', []]]

  let tooOld = null
  for (const [command, args] of candidates) {
    try {
      const version = execFileSync(
        command,
        [...args, '-c', 'import sys; print(sys.version_info.major, sys.version_info.minor)'],
        { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] },
      )
      const [major, minor] = version.trim().split(' ').map(Number)
      if (major > MIN_PYTHON[0] || (major === MIN_PYTHON[0] && minor >= MIN_PYTHON[1])) {
        return { command, args, version: `${major}.${minor}` }
      }
      tooOld = `${major}.${minor}`
    } catch {
      // This name is not installed; try the next one.
    }
  }

  const need = MIN_PYTHON.join('.')
  fail(
    tooOld
      ? `Python ${tooOld} is installed, but Python ${need} or newer is needed. Get it from https://www.python.org/downloads/`
      : `Python was not found. Install Python ${need} or newer from https://www.python.org/downloads/ ` +
          '(on Windows, tick "Add python.exe to PATH" in the installer).',
  )
}

if (existsSync(venvPython)) {
  step('Python environment already exists (server/.venv)')
} else {
  const python = findPython()
  step(`Creating the Python environment with Python ${python.version} (server/.venv)`)
  run(
    () => execFileSync(python.command, [...python.args, '-m', 'venv', '.venv'], { cwd: serverDir, stdio: 'inherit' }),
    'the Python environment could not be created. On Ubuntu or Debian, run "sudo apt install python3-venv" and try again.',
  )
}

step('Installing Python packages')
run(() => {
  const pip = (...args) => execFileSync(venvPython, ['-m', 'pip', ...args], { cwd: serverDir, stdio: 'inherit' })
  pip('install', '--quiet', '--upgrade', 'pip')
  pip('install', '--quiet', '-r', 'requirements-dev.txt')
}, 'installing the Python packages failed. Check your internet connection and run "npm run setup" again.')

const envFile = path.join(serverDir, '.env')
if (existsSync(envFile)) {
  step('server/.env already exists (left as it is)')
} else {
  step('Creating server/.env from server/.env.example')
  copyFileSync(path.join(serverDir, '.env.example'), envFile)
}

step('Installing Node packages')
run(() => {
  execSync('npm install --no-fund --no-audit', { cwd: rootDir, stdio: 'inherit' })
  execSync('npm install --no-fund --no-audit', { cwd: clientDir, stdio: 'inherit' })
}, 'installing the Node packages failed. The error from npm is shown above.')

console.log(`
Setup finished.

  1. Open server/.env and paste your Claude API key after ANTHROPIC_API_KEY=
  2. Run "npm run dev" and open http://localhost:5173
`)
