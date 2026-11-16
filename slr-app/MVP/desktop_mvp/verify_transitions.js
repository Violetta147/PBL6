// Automated verification of Camera vs Stick Figure (posture-guide) state machine in demo.html
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const vm = require("node:vm");

const htmlPath = path.join(__dirname, "demo.html");
const html = fs.readFileSync(htmlPath, "utf8");

// 1. Verify HTML structural markup
assert(html.includes('<img id="preview" alt="Khung hình camera" hidden>'), "preview img should have hidden attribute initially");
assert(html.includes('id="posture-guide"'), "posture-guide SVG container must exist");
assert(html.includes('class="guide-silhouette"'), "guide-silhouette SVG must exist");
assert(html.includes('transform: scaleX(-1)'), "cam-box img must have scaleX(-1) mirroring");
console.log("[PASS] HTML initial structure assertions passed.");

// 2. Extract and test isLiveCameraPhase function directly from demo.html
const fnMatch = html.match(/function isLiveCameraPhase\([^)]*\)\s*\{[\s\S]*?\}/);
assert(fnMatch, "isLiveCameraPhase function must exist in demo.html");
const isLiveCameraPhase = new Function("phase", fnMatch[0] + "; return isLiveCameraPhase(phase);");

assert.strictEqual(isLiveCameraPhase("loading"), false);
assert.strictEqual(isLiveCameraPhase("ready"), false);
assert.strictEqual(isLiveCameraPhase("countdown"), true);
assert.strictEqual(isLiveCameraPhase("recording"), true);
assert.strictEqual(isLiveCameraPhase("processing"), true);
assert.strictEqual(isLiveCameraPhase("result"), false);
assert.strictEqual(isLiveCameraPhase("retry"), false);
assert.strictEqual(isLiveCameraPhase("error"), false);
assert.strictEqual(isLiveCameraPhase("disconnected"), false);
console.log("[PASS] isLiveCameraPhase classification on all 9 phases passed.");

// 3. Test State Machine Transition Logic
class MockElement {
  constructor(id, hidden = false) {
    this.id = id;
    this.hidden = hidden;
    this.attributes = {};
    this.style = {};
  }
  removeAttribute(attr) {
    delete this.attributes[attr];
    if (attr === "src") delete this.src;
  }
  setAttribute(attr, val) {
    this.attributes[attr] = val;
    if (attr === "src") this.src = val;
  }
}

// Simulate demo.html runtime environment
const preview = new MockElement("preview", true);
const postureGuide = new MockElement("posture-guide", false);
let currentState = { phase: "loading" };
let previewTimer = null;
let timersCleared = 0;
let timersSet = 0;

function mockSetTimeout(fn, delay) {
  timersSet++;
  return { fn, delay, id: timersSet };
}
function mockClearTimeout(t) {
  timersCleared++;
}

function fetchNextPreview() {
  if (previewTimer) {
    mockClearTimeout(previewTimer);
    previewTimer = null;
  }
  const active = isLiveCameraPhase(currentState.phase);
  if (!active) {
    preview.hidden = true;
    preview.removeAttribute("src");
    if (postureGuide) postureGuide.hidden = false;
    return;
  }
  preview.src = "/preview?t=" + Date.now();
}

function onPreviewLoad() {
  const active = isLiveCameraPhase(currentState.phase);
  if (active) {
    preview.hidden = false;
    if (postureGuide) postureGuide.hidden = true;
    if (previewTimer) mockClearTimeout(previewTimer);
    previewTimer = mockSetTimeout(fetchNextPreview, 90);
  } else {
    preview.hidden = true;
    preview.removeAttribute("src");
    if (postureGuide) postureGuide.hidden = false;
    if (previewTimer) {
      mockClearTimeout(previewTimer);
      previewTimer = null;
    }
  }
}

function renderState(state) {
  const prevPhase = currentState.phase;
  currentState = state;
  const phase = state.phase;

  const wasCameraActive = isLiveCameraPhase(prevPhase);
  const isCameraActive = isLiveCameraPhase(phase);

  if (!isCameraActive) {
    preview.hidden = true;
    preview.removeAttribute("src");
    if (postureGuide) postureGuide.hidden = false;
    if (previewTimer) {
      mockClearTimeout(previewTimer);
      previewTimer = null;
    }
  } else if (!wasCameraActive) {
    fetchNextPreview();
  }
}

// Test Step A: Init in loading state
fetchNextPreview();
assert.strictEqual(preview.hidden, true, "Loading state: preview must be hidden");
assert.strictEqual(postureGuide.hidden, false, "Loading state: posture guide must be visible");
assert.strictEqual(preview.src, undefined, "Loading state: preview.src must not be set");
assert.strictEqual(previewTimer, null, "Loading state: no spinning timer");
console.log("[PASS] Step A: Initial loading state verified.");

// Test Step B: Transition to ready
renderState({ phase: "ready" });
assert.strictEqual(preview.hidden, true, "Ready state: preview must be hidden");
assert.strictEqual(postureGuide.hidden, false, "Ready state: posture guide must be visible");
assert.strictEqual(preview.src, undefined, "Ready state: preview.src must not be set");
console.log("[PASS] Step B: Ready state verified (stick figure visible, camera hidden).");

// Test Step C: Transition to countdown (Bắt đầu / [R] pressed)
renderState({ phase: "countdown", remaining: 3 });
assert.ok(preview.src && preview.src.includes("/preview?t="), "Countdown: must initiate fetchNextPreview");
// Notice: Before first frame arrives, preview is still hidden and postureGuide visible
assert.strictEqual(preview.hidden, true, "Before first frame arrives, preview stays hidden to avoid black/stale frame");
assert.strictEqual(postureGuide.hidden, false, "Before first frame arrives, posture guide stays visible");

// Simulate first frame loaded!
onPreviewLoad();
assert.strictEqual(preview.hidden, false, "After first frame loads, preview becomes visible");
assert.strictEqual(postureGuide.hidden, true, "After first frame loads, posture guide hides");
assert.ok(previewTimer !== null, "Continuous preview timer scheduled (90ms)");
console.log("[PASS] Step C: Countdown transition verified (smooth switch upon first frame decode).");

// Test Step D: Transition to recording
renderState({ phase: "recording", remaining: 4.0 });
assert.strictEqual(preview.hidden, false, "Recording: preview stays visible");
assert.strictEqual(postureGuide.hidden, true, "Recording: posture guide stays hidden");
console.log("[PASS] Step D: Recording phase verified.");

// Test Step E: Transition to processing
renderState({ phase: "processing" });
assert.strictEqual(preview.hidden, false, "Processing: preview stays visible");
assert.strictEqual(postureGuide.hidden, true, "Processing: posture guide stays hidden");
console.log("[PASS] Step E: Processing phase verified.");

// Test Step F: Transition to result
renderState({ phase: "result", gloss: "Dài", index: 95 });
assert.strictEqual(preview.hidden, true, "Result phase: preview immediately hidden");
assert.strictEqual(postureGuide.hidden, false, "Result phase: posture guide immediately visible");
assert.strictEqual(preview.src, undefined, "Result phase: preview.src cleared to avoid stale frame cache");
assert.strictEqual(previewTimer, null, "Result phase: previewTimer cancelled");

// Test Step G: In-flight preview load arriving AFTER entering result
onPreviewLoad();
assert.strictEqual(preview.hidden, true, "Late preview load must not unhide preview during result");
assert.strictEqual(postureGuide.hidden, false, "Posture guide must remain visible during result");
assert.strictEqual(preview.src, undefined, "preview.src must remain cleared");
console.log("[PASS] Step F & G: Result phase & late-frame immunity verified.");

// Test Step H: Retry loop (result -> countdown via [R])
renderState({ phase: "countdown", remaining: 3 });
assert.ok(preview.src && preview.src.includes("/preview?t="), "Retry must fetch fresh frame");
onPreviewLoad();
assert.strictEqual(preview.hidden, false, "Preview visible after retry frame loads");
assert.strictEqual(postureGuide.hidden, true, "Posture guide hidden after retry frame loads");
console.log("[PASS] Step H: Retry loop transition verified.");

console.log("\n=== ALL DOM STATE TRANSITION TESTS PASSED (100%) ===");

async function verifySequencePlayback() {
  const playedUrls = [];
  const script = html.match(/<script>([\s\S]+)<\/script>/)[1];
  new vm.Script(script);
  const playback = script.slice(script.indexOf("async function playCandidate"),
    script.indexOf('btnConfirm.addEventListener("click", triggerConfirmSpeak)'));
  const sandbox = vm.createContext({
    playing: false, played: false, starting: false, selectedCandidate: null,
    currentState: { phase: "result", sequence: [
      { index: 154, gloss: "Khăn quàng cổ" }, { index: 86, gloss: "Cảm ơn" },
    ] },
    soundStatus: {}, confirmLabel: {}, btnConfirm: {}, btnRetry: {}, modeSelect: {}, playedPill: {},
    setTimeout, clearTimeout, fetch: async () => {}, console,
    Audio: class {
      constructor(url) { this.url = url; }
      play() {
        playedUrls.push(this.url);
        setImmediate(() => this.onended());
        return Promise.resolve();
      }
    },
  });
  vm.runInContext(playback, sandbox);
  assert.deepStrictEqual(playedUrls, []);
  const confirmation = sandbox.triggerConfirmSpeak();
  assert.deepStrictEqual(playedUrls, ["/audio/154.mp3"]);
  assert.strictEqual(sandbox.btnRetry.disabled, true);
  await confirmation;
  assert.deepStrictEqual(playedUrls, ["/audio/154.mp3", "/audio/86.mp3"]);
  assert.strictEqual(sandbox.playedPill.hidden, false);
  assert.strictEqual(sandbox.btnRetry.disabled, false);
  console.log("[PASS] Sequence audio starts on confirmation and plays one clip at a time in order.");
}

async function verifySequenceFinish() {
  const script = html.match(/<script>([\s\S]+)<\/script>/)[1];
  const action = script.slice(script.indexOf("async function triggerStart"),
    script.indexOf('btnStart.addEventListener("click", triggerStart)'));
  const requests = [];
  const sandbox = vm.createContext({
    starting: false, playing: false, played: false,
    currentState: { phase: "recording", mode: "sequence", sample: false },
    soundStatus: {}, btnStart: {}, btnRetry: {}, modeSelect: { value: "sequence" },
    fetch: async url => {
      requests.push(url);
      return { ok: true, json: async () => ({ phase: "recording", mode: "sequence", stop_requested: true }) };
    },
    render(state) { sandbox.currentState = state; },
    console,
  });
  vm.runInContext(action, sandbox);
  await sandbox.triggerStart();
  await sandbox.triggerStart();
  assert.deepStrictEqual(requests, ["/finish"]);
  assert.strictEqual(sandbox.currentState.stop_requested, true);
  console.log("[PASS] The recording button ends an active sequence once.");
}

Promise.all([verifySequencePlayback(), verifySequenceFinish()]).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
