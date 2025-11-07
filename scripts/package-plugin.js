#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '..');
const SRC_DIR = path.join(ROOT_DIR, 'src');

function readManifest(pluginDir) {
  const manifestPath = path.join(pluginDir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`manifest.json が見つかりません: ${manifestPath}`);
  }
  return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
}

function ensureDirectory(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function listPluginDirs() {
  return fs
    .readdirSync(SRC_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

function packagePlugin(pluginName) {
  const pluginDir = path.join(SRC_DIR, pluginName);
  if (!fs.existsSync(pluginDir) || !fs.statSync(pluginDir).isDirectory()) {
    throw new Error(`プラグインディレクトリが存在しません: ${pluginName}`);
  }

  const manifest = readManifest(pluginDir);
  const zipBaseName = `${manifest.name || pluginName}-${manifest.version || '0.0.0'}`;
  const distDir = path.join(ROOT_DIR, 'dist');
  ensureDirectory(distDir);
  const outputPath = path.join(distDir, `${zipBaseName}.zip`);

  if (fs.existsSync(outputPath)) {
    fs.rmSync(outputPath);
  }

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
        resolve({ pluginName, outputPath });
      } else {
        reject(new Error(`zip コマンドが異常終了しました (code=${code})`));
      }
    });
  });
}

async function main() {
  const args = process.argv.slice(2);
  const allFlagIndex = args.indexOf('--all');
  let targets;

  if (allFlagIndex !== -1) {
    args.splice(allFlagIndex, 1);
    targets = listPluginDirs();
    if (targets.length === 0) {
      console.error('パッケージ化対象のプラグインが見つかりません。');
      process.exit(1);
    }
  } else if (args.length > 0) {
    targets = args;
  } else {
    console.error('使用方法: node scripts/package-plugin.js <pluginName> [...pluginName] または --all');
    process.exit(1);
  }

  for (const pluginName of targets) {
    try {
      const result = await packagePlugin(pluginName);
      console.log(`✅ ${pluginName} をパッケージ化しました: ${path.relative(ROOT_DIR, result.outputPath)}`);
    } catch (error) {
      console.error(`❌ ${pluginName} のパッケージ化に失敗しました: ${error.message}`);
      process.exitCode = 1;
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
