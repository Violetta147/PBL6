import * as T from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { createDevice } from './model.mjs';
import { specification, partSpecs, partPosition } from './spec.mjs';

const $ = id => document.getElementById(id);
const stage = $('stage');
const state = { selected: 'display', explode: 0, target: 0, shell: true, wires: true, esp32: false, fan: false, isolated: false, hidden: new Set(), mode: 'assembled' };
function screenTexture() {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 600;
  const x = c.getContext('2d');
  x.fillStyle = '#eef4ee'; x.fillRect(0, 0, 1024, 600);
  x.fillStyle = '#204d49'; x.fillRect(0, 0, 1024, 64);
  x.font = '500 24px Segoe UI, Arial'; x.fillStyle = '#ffffff'; x.fillText('PBL6   /   HỖ TRỢ GIAO TIẾP', 36, 41);
  x.font = '20px Segoe UI, Arial'; x.fillStyle = '#cce3d9'; x.fillText('MINH HỌA GIAO DIỆN', 727, 40);
  x.fillStyle = '#687b75'; x.font = '24px Segoe UI, Arial'; x.fillText('NGƯỜI ĐỐI THOẠI', 38, 113);
  x.fillStyle = '#253b36'; x.font = '36px Segoe UI, Arial'; x.fillText('Bạn muốn dùng gì?', 38, 172);
  x.strokeStyle = '#c6d6cc'; x.beginPath(); x.moveTo(38, 220); x.lineTo(986, 220); x.stroke();
  x.fillStyle = '#687b75'; x.font = '24px Segoe UI, Arial'; x.fillText('VÙNG SOẠN CÂU TRẢ LỜI', 38, 266);
  x.fillStyle = '#153c32'; x.font = '44px Segoe UI, Arial'; x.fillText('Cho tôi một cốc nước.', 38, 335);
  const buttons = [[38, 'Làm lại', '#dbe5dd', '#304a40'], [363, 'Giữ từ', '#dbe5dd', '#304a40'], [688, 'Phát tiếng', '#27695a', '#ffffff']];
  for (const [left, text, bg, fg] of buttons) { x.fillStyle = bg; x.beginPath(); x.roundRect(left, 400, 296, 78, 10); x.fill(); x.fillStyle = fg; x.font = '32px Segoe UI, Arial'; x.fillText(text, left + 35, 451); }
  x.font = '22px Segoe UI, Arial'; x.fillStyle = '#72867a'; x.fillText('Kiểm tra văn bản rồi chọn Phát tiếng', 38, 555);
  const texture = new T.CanvasTexture(c); texture.colorSpace = T.SRGBColorSpace; return texture;
}
let renderer;
try { renderer = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }); }
catch (error) { $('loading').hidden = true; const msg = document.createElement('p'); msg.className = 'error'; msg.role = 'alert'; msg.textContent = 'Trình duyệt chưa khởi tạo được WebGL. Hãy mở file bằng Chrome/Edge có tăng tốc đồ họa. Thông tin bộ phận vẫn có trong README và specification.json.'; stage.append(msg); throw error; }
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
renderer.setClearColor(0x13222d, 0); renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
renderer.outputColorSpace = T.SRGBColorSpace; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.25;
renderer.domElement.setAttribute('aria-label', 'Mô hình 3D thiết bị để bàn. Kéo để xoay, cuộn để phóng to; chọn bộ phận bằng chuột hoặc danh sách bên cạnh.');
renderer.domElement.setAttribute('role', 'img'); stage.prepend(renderer.domElement);
const scene = new T.Scene();
const camera = new T.PerspectiveCamera(38, 1, 1, 2500); camera.position.set(325, 230, 350);
const controls = new OrbitControls(camera, renderer.domElement); controls.target.set(0, 96, 0); controls.enableDamping = true; controls.dampingFactor = .09;
let dirty = true;
controls.addEventListener('change', () => { dirty = true; });
controls.minDistance = 180; controls.maxDistance = 1000; controls.maxPolarAngle = Math.PI * .88; controls.enablePan = true;
scene.add(new T.HemisphereLight(0xf6eee1, 0x345260, 2.6));
const key = new T.DirectionalLight(0xfff4dd, 3.6); key.position.set(-210, 400, 330); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, { left: -280, right: 280, top: 300, bottom: -220, near: 1, far: 900 }); key.shadow.bias = -.00015; key.shadow.normalBias = .45; scene.add(key);
const rim = new T.DirectionalLight(0xa8cddd, 2.0); rim.position.set(240, 150, -230); scene.add(rim);
const floor = new T.Mesh(new T.CircleGeometry(380, 96), new T.ShadowMaterial({ opacity: .24 })); floor.rotation.x = -Math.PI / 2; floor.position.y = -.2; floor.receiveShadow = true; scene.add(floor);
const device = createDevice({ screenTexture: screenTexture() }); scene.add(device.root);
const selection = new T.Box3Helper(new T.Box3(), 0x9cd5c1); selection.visible = false; scene.add(selection);
const selectedSpec = () => partSpecs.find(p => p.id === state.selected);
for (const part of partSpecs) { const option = document.createElement('option'); option.value = part.id; option.textContent = part.name; $('partSelect').append(option); }
function showDetail(id) {
  state.selected = id; const p = selectedSpec(); $('partSelect').value = id;
  $('partName').textContent = p.name; $('partStatus').textContent = p.status; $('partDimensions').textContent = p.dimensions; $('partRole').textContent = p.role;
  $('hidePart').textContent = state.hidden.has(id) ? 'Hiện bộ phận' : 'Ẩn bộ phận'; $('partTag').textContent = p.name;
  updateVisibility();
}
function updateVisibility() {
  dirty = true;
  for (const p of partSpecs) {
    let visible = !state.hidden.has(p.id);
    if (p.shell && !state.shell) visible = false;
    if (p.optional && !state[p.id]) visible = false;
    if (p.id === 'wiring' && (!state.wires || state.target > .005 || state.explode > .005)) visible = false;
    if (state.isolated) visible = p.id === state.selected;
    device.parts.get(p.id).visible = visible;
  }
  $('isolate').setAttribute('aria-pressed', String(state.isolated));
  $('isolate').textContent = state.isolated ? 'Hiện toàn bộ' : 'Xem riêng';
  $('partTag').hidden = !device.parts.get(state.selected).visible;
}
function setMode(mode) {
  state.mode = mode; state.isolated = false; state.hidden.clear();
  state.shell = mode !== 'inside'; state.target = mode === 'exploded' ? 1 : 0;
  $('shellToggle').checked = state.shell; $('explode').value = state.target * 100; $('explodeValue').value = `${Math.round(state.target * 100)}%`;
  document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
  $('status').textContent = mode === 'exploded' ? 'Tách cụm để quan sát bố trí. Đường dây được ẩn; đây không phải mô phỏng tháo lắp cơ khí.' : mode === 'inside' ? 'Đã ẩn các tấm vỏ để thấy bên trong. Loa, mic và nguồn vẫn là cụm đại diện chưa chốt.' : 'Màn và camera hướng người ký hiệu; loa và mic dự kiến phía người đối thoại.';
  if (mode === 'exploded') { camera.position.set(420, 310, 620); controls.target.set(-40, 110, 0); }
  if (mode === 'inside') { camera.position.set(280, 270, -340); controls.target.set(0, 85, 0); }
  if (mode === 'assembled') { camera.position.set(325, 230, 350); controls.target.set(0, 96, 0); }
  controls.update();
  updateVisibility();
}
document.querySelectorAll('[data-mode]').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
$('explode').addEventListener('input', e => { state.target = Number(e.target.value) / 100; $('explodeValue').value = `${e.target.value}%`; state.isolated = false; document.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === (state.target ? 'exploded' : 'assembled')))); updateVisibility(); });
$('partSelect').addEventListener('change', e => showDetail(e.target.value));
for (const [id, keyName] of [['shellToggle', 'shell'], ['wiresToggle', 'wires'], ['espToggle', 'esp32'], ['fanToggle', 'fan']]) $(id).addEventListener('change', e => { state[keyName] = e.target.checked; state.isolated = false; updateVisibility(); });
$('isolate').addEventListener('click', () => { state.isolated = !state.isolated; updateVisibility(); });
$('hidePart').addEventListener('click', () => { if (state.hidden.has(state.selected)) state.hidden.delete(state.selected); else state.hidden.add(state.selected); state.isolated = false; showDetail(state.selected); });
function view(pos, name) { camera.position.set(...pos); controls.target.set(0, 100, 0); controls.update(); $('orientation').textContent = name; }
$('frontView').addEventListener('click', () => view([0, 165, state.target ? 620 : 440], 'PHÍA NGƯỜI KÝ HIỆU · MÀN & CAMERA'));
$('rearView').addEventListener('click', () => view([180, 195, state.target ? -620 : -420], 'PHÍA NGƯỜI ĐỐI THOẠI · LOA & THU ÂM'));
$('resetView').addEventListener('click', () => view([325, 230, 350], 'MÀN & CAMERA → NGƯỜI KÝ HIỆU'));
const raycaster = new T.Raycaster(), pointer = new T.Vector2(); let down = null;
renderer.domElement.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) return;
  const rect = renderer.domElement.getBoundingClientRect(); pointer.set((e.clientX - rect.left) / rect.width * 2 - 1, -(e.clientY - rect.top) / rect.height * 2 + 1); raycaster.setFromCamera(pointer, camera);
  const targets = [...device.parts.values()].filter(p => p.visible).flatMap(p => { const meshes = []; p.traverse(o => { if (o.isMesh) meshes.push(o); }); return meshes; });
  const hit = raycaster.intersectObjects(targets, false)[0];
  if (hit) { let p = hit.object; while (p && !p.userData.id) p = p.parent; if (p) showDetail(p.userData.id); }
});
function resize() { const r = stage.getBoundingClientRect(); renderer.setSize(r.width, r.height); camera.aspect = r.width / r.height; camera.updateProjectionMatrix(); dirty = true; }
new ResizeObserver(resize).observe(stage); resize();
const reduced = matchMedia('(prefers-reduced-motion: reduce)'); let last = performance.now();
function tick(now) {
  const dt = Math.min(.05, (now - last) / 1000); last = now;
  controls.update();
  if (!dirty && state.explode === state.target) { requestAnimationFrame(tick); return; }
  state.explode += (state.target - state.explode) * (reduced.matches ? 1 : 1 - Math.exp(-9 * dt)); if (Math.abs(state.explode - state.target) < .0001) state.explode = state.target;
  for (const p of partSpecs) device.parts.get(p.id).position.fromArray(partPosition(p, state.explode, [0, 0, 0]));
  updateVisibility(); controls.update(); device.root.updateMatrixWorld(true);
  const selected = device.parts.get(state.selected); selection.visible = selected.visible && state.isolated;
  if (selection.visible) selection.box.setFromObject(selected);
  if (selected.visible) {
    const bounds = new T.Box3().setFromObject(selected), center = bounds.getCenter(new T.Vector3()); center.y = bounds.max.y + 7; center.project(camera);
    const x = (center.x * .5 + .5) * stage.clientWidth, y = (-center.y * .5 + .5) * stage.clientHeight;
    const labelTop = stage.clientWidth < 500 ? 135 : 100;
    $('partTag').hidden = center.z > 1 || center.z < -1 || y < labelTop || y > stage.clientHeight - 35;
    if (state.shell && state.target < .1 && !state.isolated && !['display', 'camera', 'shell', 'front', 'rear', 'base'].includes(state.selected)) $('partTag').hidden = true;
    $('partTag').style.left = `${Math.max(100, Math.min(stage.clientWidth - 100, x))}px`; $('partTag').style.top = `${y}px`;
  }
  renderer.render(scene, camera); dirty = false; requestAnimationFrame(tick);
}
function download(blob, name) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); }
async function exportModel(mode = 'current', save = true) {
  const clone = device.root.clone(true);
  clone.scale.setScalar(.001); clone.name = 'PBL6_tabletop_device_concept'; clone.userData = { ...clone.userData, gltfUnit: 'meter', originalGeometryUnit: 'millimeter', exportPose: mode, notManufacturingCAD: true };
  for (const p of partSpecs) {
    const obj = clone.children.find(c => c.name === p.id);
    if (mode !== 'current') { obj.position.fromArray(partPosition(p, mode === 'exploded' ? 1 : 0, [0, 0, 0])); obj.visible = !p.optional && !(p.id === 'wiring' && mode === 'exploded'); }
  }
  clone.updateMatrixWorld(true);
  const data = await new GLTFExporter().parseAsync(clone, { binary: true, onlyVisible: true });
  if (save) { download(new Blob([data], { type: 'model/gltf-binary' }), `pbl6-device-${mode}.glb`); return { bytes: data.byteLength }; }
  const bytes = new Uint8Array(data); let binary = '';
  for (let i = 0; i < bytes.length; i += 32768) binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
  return btoa(binary);
}
$('exportGLB').addEventListener('click', async () => { $('status').textContent = 'Đang xuất GLB…'; try { await exportModel(); $('status').textContent = 'Đã xuất GLB theo trạng thái đang xem. Đơn vị GLB là mét; mỗi cụm giữ tên và thông tin nguồn.'; } catch (e) { $('status').textContent = `Xuất GLB chưa thành công: ${e.message}`; } });
$('saveImage').addEventListener('click', () => { renderer.render(scene, camera); renderer.domElement.toBlob(blob => { if (blob) download(blob, 'pbl6-device-view.png'); }); });
showDetail('display'); $('loading').hidden = true; requestAnimationFrame(tick);
window.deviceViewer = { state, device, scene, camera, controls, specification, partSpecs, setMode, select: showDetail, exportModel, ready: true, inspect() { return { selected: state.selected, exploded: state.explode, visible: [...device.parts].filter(([, g]) => g.visible).map(([id]) => id), meshCount: [...device.parts.values()].reduce((n, g) => { g.traverse(o => { if (o.isMesh) n++; }); return n; }, 0) }; } };
