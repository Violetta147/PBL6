import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import { createDevice } from '../model.mjs';
import { partSpecs, specification, partPosition } from '../spec.mjs';

test('draft choices remain distinct from estimated geometry', () => {
  assert.ok(!Object.hasOwn(specification, 'sources'));
  assert.equal(specification.screen.diagonalInches, 7);
  assert.equal(specification.choices.displaySide, 'Người ký hiệu');
  assert.equal(specification.choices.speakerSide, 'Người đối thoại');
  assert.equal(new Set(partSpecs.map(p => p.id)).size, partSpecs.length);
  for (const p of partSpecs) {
    assert.ok(p.status && p.dimensions && p.role);
    assert.ok(!Object.hasOwn(p, 'sources'));
  }
  assert.match(partSpecs.find(p => p.id === 'camera').dimensions, /ước lượng/);
  assert.match(partSpecs.find(p => p.id === 'speaker').status, /Chưa chốt/);
  assert.ok(!partSpecs.some(p => /battery|sensor/.test(p.id)));
});

test('all assemblies have actual 3D meshes with finite geometry at every exploded state', () => {
  const { root, parts } = createDevice();
  assert.equal(parts.size, partSpecs.length);
  for (const amount of [0, .25, .5, .75, 1]) {
    for (const p of partSpecs) parts.get(p.id).position.fromArray(partPosition(p, amount, [0, 0, 0]));
    root.updateMatrixWorld(true);
    for (const [id, group] of parts) {
      const bounds = new T.Box3().setFromObject(group);
      assert.ok(!bounds.isEmpty(), `${id}: empty geometry`);
      assert.ok([...bounds.min, ...bounds.max].every(Number.isFinite), `${id}: invalid bounds`);
    }
  }
});

test('optional components are disabled by default and Pi PCB retains its sourced footprint', () => {
  const { root, parts } = createDevice();
  assert.equal(parts.get('esp32').visible, false);
  assert.equal(parts.get('fan').visible, false);
  const pcb = root.getObjectByName('RaspberryPi4_PCB_85x56');
  const size = new T.Box3().setFromObject(pcb).getSize(new T.Vector3());
  assert.ok(Math.abs(size.x - 85) < .01);
  assert.ok(Math.abs(size.z - 56) < .01);
  const bounds = new T.Box3().setFromObject(root), total = bounds.getSize(new T.Vector3());
  assert.ok(total.x <= 221 && total.z <= 146 && total.y <= 208, `envelope mismatch: ${total.toArray()}`);
});

test('screen and camera face signer; loudspeaker and microphone face the opposite side', () => {
  const { root } = createDevice(); root.updateMatrixWorld(true);
  const cameraLens = root.getObjectByName('lens_glass').getWorldPosition(new T.Vector3());
  const display = root.getObjectByName('display_area_estimated').getWorldPosition(new T.Vector3());
  const speaker = root.getObjectByName('speaker_cone').getWorldPosition(new T.Vector3());
  const mic = root.getObjectByName('microphone_placeholder').getWorldPosition(new T.Vector3());
  assert.ok(cameraLens.z > 0 && display.z > 0);
  assert.ok(speaker.z < 0 && mic.z < 0);
});
