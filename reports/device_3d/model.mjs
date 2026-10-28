import * as T from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { partSpecs, specification } from './spec.mjs';

export function createDevice({ screenTexture = null } = {}) {
  const root = new T.Group();
  root.name = 'PBL6_tabletop_concept_mm';
  root.userData = { ...specification.choices, unit: 'millimeter', version: specification.version };
  const parts = new Map();
  const mat = (color, roughness = .55, metalness = 0) => new T.MeshStandardMaterial({ color, roughness, metalness });
  const m = { shell: mat('#e9e3d6'), trim: mat('#303c43'), dark: mat('#18252d'), board: mat('#237667'), chip: mat('#263139'), metal: mat('#a9b2b5', .35, .65), gold: mat('#c6a866', .4, .55), rubber: mat('#293332', .9), wire: mat('#3e4b50'), orange: mat('#ca8d49'), blue: mat('#497c9c'), glass: mat('#193940', .25, .15) };
  for (const p of partSpecs) {
    const g = new T.Group(); g.name = p.id; g.userData = { ...p }; g.visible = !p.optional;
    root.add(g); parts.set(p.id, g);
  }
  function mesh(g, geo, material, pos, name) {
    const o = new T.Mesh(geo, material); o.position.set(...pos); o.name = name; o.castShadow = true; o.receiveShadow = true; g.add(o); return o;
  }
  function box(g, size, pos, material = m.dark, radius = 0, name = 'body') {
    return mesh(g, radius ? new RoundedBoxGeometry(...size, 2, radius) : new T.BoxGeometry(...size), material, pos, name);
  }
  function cyl(g, radius, height, pos, material = m.metal, axis = 'y', name = 'cylinder') {
    const o = mesh(g, new T.CylinderGeometry(radius, radius, height, 32), material, pos, name);
    if (axis === 'z') o.rotation.x = Math.PI / 2;
    if (axis === 'x') o.rotation.z = Math.PI / 2;
    return o;
  }
  function screw(g, x, y, z, axis = 'y') {
    cyl(g, 1.7, 1.1, [x, y, z], m.metal, axis, 'fastener_concept');
  }
  function wire(g, points, radius, material = m.wire) {
    return mesh(g, new T.TubeGeometry(new T.CatmullRomCurve3(points.map(p => new T.Vector3(...p))), 40, radius, 6, false), material, [0, 0, 0], 'route_concept');
  }
  const base = parts.get('base');
  box(base, [220, 9, 145], [0, 10, 0], m.trim, 4, 'base_plate');
  for (const x of [-90, 90]) for (const z of [-52, 52]) cyl(base, 9, 5.5, [x, 3, z], m.rubber, 'y', 'rubber_foot');
  for (const x of [-91, 91]) for (const z of [-48, 39]) { cyl(base, 3.5, 14, [x, 21, z], m.metal); screw(base, x, 28.5, z); }
  const shell = parts.get('shell');
  const outline = [[70, 14], [-70, 14], [-70, 165], [35, 165]];
  for (const x of [-110, 107]) {
    const shape = new T.Shape(outline.map(([z, y]) => new T.Vector2(-z, y)));
    for (let i = 0; i < 8; i++) {
      const z = -44 + i * 6, y = 65;
      const h = new T.Path(); h.moveTo(-z, y); h.lineTo(-z - 2, y); h.lineTo(-z - 2, y + 39); h.lineTo(-z, y + 39); h.closePath(); shape.holes.push(h);
    }
    const geo = new T.ExtrudeGeometry(shape, { depth: 3, bevelEnabled: false }); geo.rotateY(Math.PI / 2);
    mesh(shell, geo, m.shell, [x, 0, 0], 'vented_side_panel');
  }
  box(shell, [214, 3, 101], [0, 166, -17], m.shell, 1.2, 'top_panel');
  for (const x of [-96, 96]) for (const z of [-52, 22]) screw(shell, x, 168, z);
  const front = parts.get('front');
  const face = new T.Group(); face.position.set(0, 95, 49); face.rotation.x = -12 * Math.PI / 180; front.add(face);
  box(face, [208, 13, 7], [0, 58.5, 0], m.shell, 2, 'upper_bezel');
  box(face, [208, 13, 7], [0, -58.5, 0], m.shell, 2, 'lower_bezel');
  box(face, [208, 6, 5], [0, 68, -.5], m.shell, 1, 'upper_transition');
  const chin = box(front, [208, 17, 4], [0, 22, 66], m.shell, 1, 'lower_transition');
  chin.rotation.x = -12 * Math.PI / 180;
  for (const x of [-95.5, 95.5]) box(face, [17, 104, 7], [x, 0, 0], m.shell, 2, 'side_bezel');
  for (const x of [-96, 96]) for (const y of [-58, 58]) screw(face, x, y, 4.2, 'z');
  const display = parts.get('display');
  const d = new T.Group(); d.position.copy(face.position); d.rotation.copy(face.rotation); display.add(d);
  box(d, [170, 100, 8], [0, 0, -1], m.dark, 1.3, 'LCD_module_170x100_approx');
  box(d, [168, 98, .8], [0, 0, 3.4], m.trim, .3, 'touch_glass');
  const sm = screenTexture ? new T.MeshBasicMaterial({ map: screenTexture, toneMapped: false }) : m.glass;
  mesh(d, new T.PlaneGeometry(153.5, 90), sm, [0, 0, 3.86], 'display_area_estimated');
  box(d, [68, 38, 2], [0, 0, -6], m.board, .5, 'display_controller_estimate');
  const camera = parts.get('camera');
  box(camera, [28, 6, 24], [0, 171, 22], m.trim, 2, 'webcam_mount_concept');
  cyl(camera, 8, 15, [0, 178, 24], m.trim, 'x', 'webcam_pivot');
  box(camera, [72, 30, 28], [0, 191, 27], m.dark, 8, 'Aioneus_form_placeholder');
  cyl(camera, 11, 4, [0, 191, 42], m.trim, 'z', 'lens_bezel');
  cyl(camera, 8.5, 1, [0, 191, 44.3], m.glass, 'z', 'lens_glass');
  cyl(camera, 3.5, .5, [0, 191, 45], m.dark, 'z', 'lens_aperture');
  cyl(camera, 1.1, 1, [25, 190, 41], m.blue, 'z', 'indicator_concept');
  const pi = parts.get('pi');
  box(pi, [85, 1.6, 56], [-48, 31, -9], m.board, 1.5, 'RaspberryPi4_PCB_85x56');
  box(pi, [15, 2.5, 15], [-53, 34, -7], m.chip, .5, 'SoC_simplified');
  box(pi, [10, 2, 10], [-70, 34, -12], m.chip, .3, 'RAM_simplified');
  box(pi, [22, 14, 16], [-12, 39, -24], m.metal, .8, 'Ethernet_simplified');
  for (const z of [-5, 12]) {
    box(pi, [17, 15, 14], [-12, 39.5, z], m.metal, .6, 'stacked_USB_pair');
    for (const y of [36, 42]) box(pi, [1, 4, 10], [-3, y, z], z < 0 ? m.blue : m.dark, .1, 'USB_socket');
  }
  for (let row = 0; row < 2; row++) for (let i = 0; i < 20; i++) box(pi, [.65, 6, .65], [-83 + i * 2.54, 35, -33 + row * 2.54], m.gold, 0, 'GPIO_pin');
  for (const x of [-80, -63]) box(pi, [8, 3, 5], [x, 33, 21], m.metal, .4, 'micro_HDMI_simplified');
  box(pi, [9, 3, 6], [-87, 33, 9], m.metal, .5, 'USB_C_simplified');
  for (const x of [-87, -29]) for (const z of [-33, 16]) cyl(pi, 2.2, 11, [x, 24.6, z], m.gold);
  const sd = parts.get('sd');
  box(sd, [15, 1, 11], [-91, 29.5, -8], m.dark, .6, 'microSD_32GB');
  for (let i = 0; i < 6; i++) box(sd, [3, .15, .7], [-85, 30.1, -11 + i * 1.2], m.gold);
  const rear = parts.get('rear');
  const rs = new T.Shape([new T.Vector2(-107, 14), new T.Vector2(107, 14), new T.Vector2(107, 164), new T.Vector2(-107, 164)]);
  const hole = new T.Path(); hole.absarc(35, 106, 27, 0, Math.PI * 2, true); rs.holes.push(hole);
  const micHole = new T.Path(); micHole.absarc(-32, 148, 5, 0, Math.PI * 2, true); rs.holes.push(micHole);
  mesh(rear, new T.ExtrudeGeometry(rs, { depth: 3, bevelEnabled: false }), m.shell, [0, 0, -70], 'rear_service_panel');
  for (let i = -4; i <= 4; i++) {
    const x = i * 5.5, h = 2 * Math.sqrt(Math.max(0, 26 ** 2 - x ** 2));
    box(rear, [1.8, h, 2], [35 + x, 106, -70.5], m.trim, .5, 'speaker_grille_rib');
  }
  for (const x of [-96, 96]) for (const y of [25, 152]) screw(rear, x, y, -70.8, 'z');
  box(rear, [30, 11, 1], [-62, 32, -70.8], m.dark, 2, 'DC_input_recess');
  cyl(rear, 3.5, 2, [-62, 32, -72], m.metal, 'z', 'DC_input_concept');
  const speaker = parts.get('speaker');
  cyl(speaker, 25, 12, [35, 106, -56], m.trim, 'z', 'speaker_50mm_placeholder');
  cyl(speaker, 20, 1, [35, 106, -63], m.dark, 'z', 'speaker_cone');
  cyl(speaker, 9, 5, [35, 106, -63], m.rubber, 'z', 'speaker_dustcap');
  box(speaker, [34, 1.6, 24], [53, 40, -38], m.board, .6, 'amplifier_placeholder');
  box(speaker, [10, 4, 10], [53, 43, -38], m.chip, .4);
  const microphone = parts.get('microphone');
  cyl(microphone, 4.5, 10, [-32, 148, -66], m.dark, 'z', 'microphone_placeholder');
  box(microphone, [24, 2, 15], [-32, 144, -52], m.board, .7, 'USB_audio_placeholder');
  const power = parts.get('power');
  box(power, [48, 2, 27], [57, 22, 12], m.board, 1, 'DC_distribution_zone_only');
  for (const x of [43, 58, 73]) { box(power, [9, 7, 9], [x, 26, 12], m.orange, .5, 'terminal_placeholder'); for (const z of [10, 14]) screw(power, x, 30, z); }
  const esp = parts.get('esp32');
  box(esp, [52, 1.6, 28], [48, 53, 0], m.dark, 1.5, 'ESP32_variant_unspecified');
  box(esp, [18, 3, 16], [46, 56, 0], m.metal, .6, 'ESP32_module');
  box(esp, [11, 1, 16], [67, 55, 0], m.board, .2, 'antenna_region');
  for (let i = 0; i < 15; i++) for (const z of [-12, 12]) box(esp, [.7, 7, .7], [25 + i * 2.54, 54, z], m.gold, 0, 'header_pin');
  const fan = parts.get('fan');
  for (const z of [-48, -12]) box(fan, [10, 40, 4], [-100, 100, z], m.dark, 1);
  for (const y of [82, 118]) box(fan, [10, 4, 36], [-100, y, -30], m.dark, 1);
  cyl(fan, 6, 11, [-100, 100, -30], m.trim, 'x', 'fan_hub');
  for (let i = 0; i < 7; i++) {
    const a = i / 7 * Math.PI * 2;
    const blade = box(fan, [2, 7, 14], [-100, 100 + Math.cos(a) * 11, -30 + Math.sin(a) * 11], m.trim, 1);
    blade.rotation.x = a - .4;
  }
  const w = parts.get('wiring');
  wire(w, [[-10, 40, 11], [8, 43, 14], [14, 105, 0], [15, 170, 14], [25, 182, 16]], 1.6);
  wire(w, [[-63, 33, 24], [-40, 44, 34], [-8, 73, 36], [0, 92, 40]], 2.1);
  wire(w, [[-10, 36, -5], [4, 45, -18], [12, 80, -42], [35, 94, -50]], 1.2);
  wire(w, [[-62, 32, -63], [-62, 23, -44], [0, 20, -35], [57, 26, 12]], 1.5, m.orange);
  wire(w, [[43, 26, 12], [18, 22, 30], [-40, 22, 35], [-87, 33, 12]], 1.3, m.orange);
  root.traverse(o => { if (o.isMesh) o.userData.geometryStatus = 'Concept geometry; see parent component metadata'; });
  return { root, parts };
}
