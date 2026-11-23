// Locations shared by the scripts in this folder.
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
export const serverDir = path.join(rootDir, 'server')
export const clientDir = path.join(rootDir, 'client')

// A virtual environment keeps its Python in a different place on Windows.
export const venvPython =
  process.platform === 'win32'
    ? path.join(serverDir, '.venv', 'Scripts', 'python.exe')
    : path.join(serverDir, '.venv', 'bin', 'python')
