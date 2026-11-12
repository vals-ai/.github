const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const [script, scenario] = process.argv.slice(2);
const posts = [];
const filePages = [];
const files = Array.from({length: 316}, (_, index) => ({filename: `file-${index}.py`, patch: '@@ -0,0 +1 @@\n+source'}));
const revision = {head: {sha: 'a'.repeat(40)}, base: {sha: 'b'.repeat(40)}};
let exitCode = 0;

function request(_command, arguments_) {
  const endpoint = arguments_[1];
  const method = arguments_[3];
  let result = [];
  if (endpoint.includes('/files?')) {
    const page = Number(new URLSearchParams(endpoint.split('?')[1]).get('page') || 1);
    filePages.push(page);
    result = scenario === 'truncated' && page > 1 ? [] : files.slice((page - 1) * 100, page * 100);
  } else if (endpoint.endsWith('/pulls/266')) {
    result = {...revision, changed_files: 316};
    if (scenario === 'changed-revision') result.head = {sha: 'c'.repeat(40)};
  } else if (method === 'POST' && endpoint.endsWith('/reviews')) {
    posts.push(JSON.parse(arguments_.input));
  }
  return {status: 0, stdout: JSON.stringify(result)};
}

const sandbox = {
  require(name) {
    if (name === 'fs') return {
      readFileSync(name) {
        if (name === 'event.json') return JSON.stringify({pull_request: {number: 266, ...revision}});
        if (name === 'findings.json') return JSON.stringify([{file: 'file-315.py', line: 1, description: 'Example finding'}]);
        throw new Error(`Unexpected file: ${name}`);
      }
    };
    if (name === 'child_process') return {
      spawnSync(command, arguments_, options) {
        arguments_.input = options.input;
        return request(command, arguments_);
      }
    };
    throw new Error(`Unexpected module: ${name}`);
  },
  process: {
    env: {GITHUB_REPOSITORY: 'vals-ai/valsmith', GITHUB_EVENT_PATH: 'event.json'},
    exit(code) {exitCode = code;}
  },
  console: {log() {}, error() {}}
};
vm.runInNewContext(fs.readFileSync(script, 'utf8'), sandbox, {filename: script});
if (scenario === 'last-file') {
  assert.equal(exitCode, 0);
  assert.deepEqual(filePages, [1, 2, 3, 4]);
  assert.equal(posts.length, 1);
  assert.equal(posts[0].comments[0].path, 'file-315.py');
} else {
  assert.equal(exitCode, 1);
  assert.equal(posts.length, 0);
}
