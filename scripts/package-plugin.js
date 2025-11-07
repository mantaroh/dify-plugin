#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '..');
const SRC_DIR = path.join(ROOT_DIR, 'src');
const DIST_DIR = path.join(ROOT_DIR, 'dist');

function readManifest(pluginDir) {
  const manifestPath = path.join(pluginDir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`manifest.json が見つかりません: ${manifestPath}`);
  }
  const content = fs.readFileSync(manifestPath, 'utf8');
  return JSON.parse(content);
}

function ensureDirectory(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function listPluginDirs() {
  if (!fs.existsSync(SRC_DIR)) {
    return [];
  }
  return fs
    .readdirSync(SRC_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

function resolvePluginTarget(target) {
  if (!target) {
    throw new Error('パッケージ化対象の指定が空です。');
  }
  const normalized = target.replace(/\/$/, '');
  const directPath = path.resolve(ROOT_DIR, normalized);
  if (fs.existsSync(directPath) && fs.statSync(directPath).isDirectory()) {
    return directPath;
  }
  const fromSrc = path.join(SRC_DIR, normalized);
  if (fs.existsSync(fromSrc) && fs.statSync(fromSrc).isDirectory()) {
    return fromSrc;
  }
  throw new Error(`プラグインディレクトリが存在しません: ${target}`);
}

function buildZipBaseName(manifest, pluginDir) {
  const manifestName = manifest.name || path.basename(pluginDir);
  const version = manifest.version || '0.0.0';
  return `${manifestName}-${version}`;
}

function runZipCommand(pluginDir, outputPath) {
  return new Promise((resolve, reject) => {
    const zipArgs = ['-r', outputPath, '.'];
    const zipProcess = spawn('zip', zipArgs, {
      cwd: pluginDir,
      stdio: 'inherit',
    });

    zipProcess.on('error', (error) => {
      reject(new Error(`zip コマンドの実行に失敗しました: ${error.message}`));
    });

    zipProcess.on('exit', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`zip コマンドが異常終了しました (code=${code})`));
      }
    });
  });
}

async function packagePlugin(target) {
  const pluginDir = resolvePluginTarget(target);
  const manifest = readManifest(pluginDir);
  const zipBaseName = buildZipBaseName(manifest, pluginDir);

  ensureDirectory(DIST_DIR);
  const outputPath = path.join(DIST_DIR, `${zipBaseName}.zip`);

  if (fs.existsSync(outputPath)) {
    fs.rmSync(outputPath);
  }

  await runZipCommand(pluginDir, outputPath);

  return {
    target,
    pluginDir,
    manifest,
    outputPath,
    zipBaseName,
  };
}

async function packageMultiple(targets) {
  const results = [];
  for (const target of targets) {
    const result = await packagePlugin(target);
    results.push(result);
  }
  return results;
}

async function runCli(argv = process.argv.slice(2)) {
  const args = argv.filter((arg) => arg !== '--');
  const allFlagIndex = args.indexOf('--all');
  let targets;

  if (allFlagIndex !== -1) {
    args.splice(allFlagIndex, 1);
    if (args.length > 0) {
      throw new Error('--all オプションと個別指定は同時に利用できません。');
    }
    targets = listPluginDirs();
    if (targets.length === 0) {
      throw new Error('パッケージ化対象のプラグインが見つかりません。');
    }
  } else {
    targets = args;
    if (targets.length === 0) {
      throw new Error('パッケージ化するプラグインを指定してください。');
    }
  }

  const results = await packageMultiple(targets);
  for (const { pluginDir, outputPath, zipBaseName } of results) {
    const relativeDir = path.relative(ROOT_DIR, pluginDir) || '.';
    const relativeOutput = path.relative(ROOT_DIR, outputPath) || outputPath;
    console.log(`✅ ${zipBaseName} (${relativeDir}) -> ${relativeOutput}`);
  }
  return results;
}

module.exports = {
  ROOT_DIR,
  SRC_DIR,
  DIST_DIR,
  readManifest,
  ensureDirectory,
  listPluginDirs,
  resolvePluginTarget,
  packagePlugin,
  packageMultiple,
  runCli,
};

if (require.main === module) {
  runCli().catch((error) => {
    console.error(`❌ パッケージ化に失敗しました: ${error.message}`);
    process.exit(1);
  });
}
