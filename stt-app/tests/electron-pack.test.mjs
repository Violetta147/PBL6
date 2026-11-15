import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));

test('Packaged build verification', async (t) => {
  await t.test('STT Touchscreen App.exe exists and is non-empty', () => {
    const exePath = path.join(root, 'dist/win-unpacked/STT Touchscreen App.exe');
    assert.ok(fs.existsSync(exePath), 'Packaged executable should exist');
    const stat = fs.statSync(exePath);
    assert.ok(stat.size > 50 * 1024 * 1024, `Executable size (${stat.size} bytes) should be > 50MB`);
  });

  await t.test('splash.html exists in packed resources and has valid content and retry action', () => {
    const splashPath = path.join(root, 'electron/splash.html');
    assert.ok(fs.existsSync(splashPath), 'splash.html should exist');
    const content = fs.readFileSync(splashPath, 'utf8');
    assert.ok(content.includes('STT · Tiếng Việt'), 'splash.html must include title');
    assert.ok(content.includes('Đang khởi động hệ thống...'), 'splash.html must include status text');
    assert.ok(content.includes('spinner'), 'splash.html must include spinner');
    assert.ok(content.includes('retryStartup'), 'splash.html must include retryStartup handler');
  });

  await t.test('preload.cjs exists and exposes retryStartup via contextBridge', () => {
    const preloadPath = path.join(root, 'electron/preload.cjs');
    assert.ok(fs.existsSync(preloadPath), 'preload.cjs should exist');
    const content = fs.readFileSync(preloadPath, 'utf8');
    assert.ok(content.includes('contextBridge.exposeInMainWorld'), 'preload.cjs must use contextBridge');
    assert.ok(content.includes('retryStartup'), 'preload.cjs must expose retryStartup');
    assert.ok(content.includes('app:retry-startup'), 'preload.cjs must send app:retry-startup channel');
  });

  await t.test('main.cjs loads splash.html safely without unencoded hash truncation', () => {
    const mainPath = path.join(root, 'electron/main.cjs');
    assert.ok(fs.existsSync(mainPath), 'main.cjs should exist');
    const content = fs.readFileSync(mainPath, 'utf8');
    assert.ok(content.includes('loadFile(splashPath)'), 'main.cjs should call window.loadFile');
    assert.ok(content.includes('base64'), 'main.cjs should have base64 data-url fallback');
    assert.ok(!content.includes('data:text/html;charset=utf-8,<!DOCTYPE html><html><head><meta charset="utf-8"/><title>STT · Tiếng Việt</title><style>body{margin:0;padding:0;background:#F5F7F9'), 'main.cjs must NOT have raw unencoded data URL with # fragment');
    assert.ok(content.includes('app:retry-startup'), 'main.cjs should handle app:retry-startup IPC');
    assert.ok(content.includes('resolveAvailablePort'), 'main.cjs should have dynamic port fallback');
  });

  await t.test('Next.js production build exists in packed resources', () => {
    const nextDir = path.join(root, 'dist/win-unpacked/resources/app/.next');
    assert.ok(fs.existsSync(nextDir), '.next folder must exist in packed app');
  });
});
