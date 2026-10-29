import * as k from './vendor/kit/iso-kit.mjs';
import * as G from './vendor/kit/lathe.mjs';
import * as A from './vendor/kit/audit.mjs';
import {turning} from './vendor/kit/turn-build.mjs';
export const W=920,H=650;
export const assemblies=[
 ['base','Đế & gá khay','Cơ khí đề xuất','220 × 145 mm; ước lượng','Chân cao su và khung giữ thiết bị trên bàn. Vị trí gá chưa phải bản chế tạo.',[0,0,0]],
 ['left','Hông trái','Cơ khí đề xuất','Dày 3 mm; ước lượng','Tháo hông để tiếp cận khay Pi. Vít và khe gió là bố trí minh họa.',[-200,0,0]],
 ['right','Hông phải','Cơ khí đề xuất','Dày 3 mm; ước lượng','Khoang nguồn và thu/phát âm thanh. Điện áp và dòng tổng chưa chốt.',[200,0,0]],
 ['roof','Nắp trên','Cơ khí đề xuất','214 × 110 × 3 mm; ước lượng','Nắp tháo bảo trì, mang vị trí đỡ camera khi lắp.',[0,0,90]],
 ['front','Mặt người ký','Cơ khí đề xuất','Cửa màn 170 × 100 mm; dự kiến','Mặt trước có một màn cảm ứng, hướng người ký. Trong bản mới màn đứng; góc đặt vẫn cần thử với người dùng.',[0,80,0]],
 ['display','Màn cảm ứng 7″','Phương án dự kiến','NH2067: 1024 × 600; khoảng 170 × 100 mm','Trang sản phẩm ghi 17 × 10 cm. Chiều dày, vùng hiển thị và lỗ gá chưa có bản vẽ. Cần HDMI cho hình, USB data cho touch và nguồn phù hợp.',[0,150,0]],
 ['camera','Webcam Aioneus','Có trong trao đổi gốc','USB 1080p; vỏ 72 × 28 × 28 mm ước lượng','Hướng người ký để thu động tác. Chưa rõ mã sản phẩm, góc nhìn, kích thước và có micro hay không.',[0,0,150]],
 ['pi','Raspberry Pi 4B • 8 GB','Có kết quả thí nghiệm','PCB 85 × 56 mm; bố trí đầu nối giản lược','B04 đã chạy Zipformer INT8 trên WAV. SPOTER là hướng tích hợp; chưa có benchmark toàn camera–landmark–SPOTER trên Pi.',[-150,0,0]],
 ['rear','Mặt người đối thoại','Cơ khí đề xuất','Cửa loa 60 × 60 mm; ước lượng','Loa hướng người đối thoại. Khu vực thu âm ở cùng phía là đề xuất, chưa kiểm chứng âm học.',[0,-80,0]],
 ['speaker','Loa & lưới bảo vệ','Chưa chốt linh kiện','Củ loa Ø50 mm; đại diện','Phát câu đã được xác nhận. Không phải bản CAD của Loyfun 804; âm lượng, công suất và trở kháng chưa chốt.',[0,-150,0]],
 ['audio','Khay âm thanh & nguồn','Chưa chốt linh kiện','Khay 84 × 84 mm; ước lượng','Vùng bo ampli, đầu vào DC và kết nối. Adapter đặt ngoài. Không giả định Pi cấp điện đủ cho tất cả ngoại vi.',[150,0,0]],
 ['mic','Cụm thu âm','Chưa chốt linh kiện','USB/audio đại diện; chưa chốt AEC','Thu lời người đối thoại. Đây không phải xác nhận micro webcam hoặc nghe/phát đồng thời đã hoạt động.',[0,-110,65]]
].map(([id,name,status,size,description,move])=>({id,name,status,size,description,move}));
export function follow(v={}) {const e=Math.max(0,Math.min(1,v.explode??0));const shell=Math.min(1,e*2);const inner=Math.max(0,e*2-1);const o={device:v.device??0};for(const a of assemblies){if(a.id==='base')continue;const t=['left','right','roof','front','rear','camera','mic'].includes(a.id)?shell:inner;o[a.id]=Math.hypot(...a.move)*t;}return o;}
export const poses=()=>Array.from({length:25},(_,i)=>[0,.25,.5,.75,1].map(e=>follow({device:i*15,explode:e}))).flat();
export function makeModel(){
 const P=k.fitProjection([...k.boxCorners({x:-210,y:-200,w:420,d:400,r:0},0,350)],W,H,{pad:45,azimuth:55,elevation:26});
 const R=A.recorder(P),T=turning(P,{recorder:R});const device=T.group('device',{turn:{pivot:[0,0]}}), layer=T.layer('device');T.stack(['device']);
 const groups={base:device};for(const a of assemblies.slice(1))groups[a.id]=T.group(a.id,{parent:device,slide:{direction:a.move,travel:Math.hypot(...a.move)}});
 const box=(id,name,x,y,z,w,d,h,mat='steel',radius=0.5,extra={})=>T.prism({name:id+'.'+name,group:groups[id],layer,plan:{x,y,w,d,r:radius},z,h,steps:2,bevel:Math.min(.6,w/8,d/8,h/3),material:mat,tone:id==='base'?'lo':'mid',...extra});
 const round=(id,name,c,axis,s0,s1,r,mat='steel',extra={})=>T.round({name:id+'.'+name,group:groups[id],layer,F:G.frameAlong(c,axis),s0,s1,r,material:mat,tone:'mid',...extra});
 const plane=(part,o,u,v,svg,normal)=>T.plane({part,o,u,v,svg,normal});
 // Feet contact the tabletop at z=0. Every solid records its true geometry.
 for(const x of [-90,90])for(const y of [-54,54]){const p=round('base','foot.'+x+'.'+y,[x,y,0],[0,0,1],0,4,8,'rubber');p.shapes.forEach(s=>s.ground=true);round('base','pad.'+x+'.'+y,[x,y,0],[0,0,1],4,6,9,'gunmetal');}
 box('base','plate',-110,-72.5,6,220,145,8,'gunmetal',5,{details:{seams:[9],dots:[[-100,-62],[-100,62],[100,-62],[100,62]].map(([x,y])=>({at:[14,x,y],normal:[0,0,1],size:.5}))}});
 for(const x of [-96,-16,24,94])box('base','trayMount.'+x,x,-37,14,4,74,10,'steel',.2);
 // Three mm walls, an actual screen opening, and a rear service aperture.
 const l=box('left','wall',-110,-55,14,3,110,166,'steel',.2);
 const r=box('right','wall',107,-55,14,3,110,166,'steel',.2);
 for(const [p,x,n] of [[l,-110,[-1,0,0]],[r,110,[1,0,0]]]){plane(p,[x,0,0],[0,1,0],[0,0,1],Array.from({length:14},(_,i)=>'<rect x="'+(-33+i*5)+'" y="38" width="2" height="44" rx="1" fill="var(--anatomy-mid)" stroke="var(--anatomy-lo)" stroke-width=".35"/>').join(''),n);}
 box('roof','lid',-107,-55,180,214,110,3,'steel',.2,{details:{dots:[[-98,-45],[-98,45],[98,-45],[98,45]].map(([x,y])=>({at:[183,x,y],normal:[0,0,1],size:.55}))}});
 for(const [name,x,z,w,h] of [['bottom',-107,14,214,48],['top',-107,162,214,18],['left',-107,62,22,100],['right',85,62,22,100]])box('front',name,x,55,z,w,3,h,'steel',.1);
 const frontBottom=T.parts.find(p=>p.name==='front.bottom');
 plane(frontBottom,[-33,58,31],[1,0,0],[0,0,1],'<rect x="0" y="0" width="66" height="13" rx="1" fill="none" stroke="var(--anatomy-mid)" stroke-width=".3"/><circle cx="4" cy="6.5" r=".7" fill="var(--anatomy-mid)"/><circle cx="62" cy="6.5" r=".7" fill="var(--anatomy-mid)"/><g transform="translate(10 8.5) scale(1 -1)"><text font-family="monospace" font-size="3.8" fill="var(--anatomy-strong)">PBL6 / CONCEPT 02</text></g>',[0,1,0]);
 const display=box('display','lcd',-85,48,62,170,10,100,'gunmetal',.2);
 const glass=box('display','touchGlass',-79,58,67,158,.8,90,'rubber',.2,{lit:true});
 const screenSvg='<defs><clipPath id="screenclip"><rect x="0" y="0" width="150" height="82" rx="2"/></clipPath></defs><g clip-path="url(#screenclip)" class="screen-ui" style="font-family:Segoe UI,Arial;fill:var(--screen-ink)"><rect width="150" height="82" fill="var(--screen-paper)"/><text x="7" y="11" font-size="4.8">GIAO TIẾP · BẢN MINH HỌA</text><path d="M7 17H143" stroke="var(--anatomy-lo)" stroke-width=".3"/><text x="7" y="28" font-size="4">NGƯỜI ĐỐI THOẠI</text><text x="7" y="39" font-size="6">Bạn muốn dùng gì?</text><rect x="7" y="47" width="136" height="18" rx="2" fill="var(--screen-field)"/><text x="11" y="58" font-size="5.5">Cho tôi một cốc nước.</text><rect x="96" y="69" width="47" height="9" rx="2" fill="var(--screen-ink)"/><text x="104" y="75.5" font-size="4.3" fill="var(--screen-paper)">XÁC NHẬN / PHÁT</text></g>';
 plane(glass,[-75,58.8,153],[1,0,0],[0,0,-1],screenSvg,[0,1,0]);
 // Camera: flat-mounted lens rings, not overlapping cylinders.
 box('camera','mount',-14,8,183,28,24,5,'gunmetal',1);
 box('camera','body',-36,6,188,72,28,28,'gunmetal',3,{details:{seams:[192]}});
 round('camera','lensBezel',[0,34,202],[0,1,0],0,2,9,'chrome',{details:{seams:[.7,1.4]}});
 round('camera','lensGlass',[0,36,202],[0,1,0],0,.5,6.8,'rubber');
 for(const x of [-25,20])box('camera','faceInset.'+x,x,34,196,5,.4,12,'rubber',.2);
 // Raspberry Pi on a removable tray. The PCB has the documented footprint.
 box('pi','tray',-100,-42,24,110,84,3,'steel',1);
 for(const x of [-84,-7])for(const y of [-24,24])round('pi','standoff.'+x+'.'+y,[x,y,0],[0,0,1],27,33,2.4,'brass');
 const pcb=box('pi','pcb',-88,-28,33,85,56,1.6,'gunmetal',.5);
 box('pi','cpu',-61,-10,34.6,15,15,2,'chrome',.3);
 box('pi','ram',-74,9,34.6,12,10,1.4,'rubber',.2);
 box('pi','usbController',-31,-13,34.6,8,8,1.2,'rubber',.2);
 box('pi','gpioBase',-80,20,34.6,50,5,2,'rubber',.3);
 for(let i=0;i<20;i++)for(let j=0;j<2;j++)box('pi','gpio.'+i+'.'+j,-79+i*2.54,21+j*2.54,36.6,.65,.65,4,'brass',.05);
 for(const [name,x,y,w,d,h] of [['ethernet',-24,7,21,16,14],['usbA1',-21,-12,18,14,15],['usbA2',-21,-27,18,14,15],['usbC',-83,-28,9,6,3],['hdmi1',-69,-28,7,5,3],['hdmi2',-59,-28,7,5,3],['audioJack',-46,-28,8,9,5]]) {const port=box('pi',name,x,y,34.6,w,d,h,'chrome',.2); if(name.startsWith('usbA')||name==='ethernet')plane(port,[x+w,y,35.5],[0,1,0],[0,0,1],'<rect x="1" y="1" width="'+(d-2)+'" height="'+(h-3)+'" rx=".3" fill="var(--anatomy-shade-0)"/>',[1,0,0]);}
 box('pi','sdSlot',-88,-7,31.8,13,13,1.2,'steel',.2);
 box('pi','microSD32',-91,-6,30.8,15,11,1,'rubber',.2);
 for(let i=0;i<8;i++)box('pi','smd.'+i,-78+i*5.6,-17,34.6,2.7,1.4,.7,'steel',.1);
 for(const [name,x,z,w,h] of [['bottom',-107,14,214,66],['top',-107,140,214,40],['left',-107,80,102,60],['right',55,80,52,60]])box('rear',name,x,-58,z,w,3,h,'steel',.1);
 // Speaker module fills the rear aperture; its acoustic face looks to -y.
 box('speaker','frame',-5,-58,80,60,3,60,'gunmetal',.4);
 round('speaker','magnet',[25,-55,110],[0,1,0],0,18,15,'steel');
 round('speaker','surround',[25,-58,110],[0,-1,0],0,2,25,'rubber');
 round('speaker','cone',[25,-60,110],[0,-1,0],0,2,[23,12],'gunmetal');
 round('speaker','dustCap',[25,-62,110],[0,-1,0],0,.7,11,'rubber');
 const mesh=round('speaker','grille',[25,-62.7,110],[0,-1,0],0,.4,25,'steel');
 plane(mesh,[25,-63.1,110],[1,0,0],[0,0,1],Array.from({length:13},(_,i)=>{const y=(i-6)*3.4;const w=2*Math.sqrt(23*23-y*y);return '<rect x="'+(-w/2)+'" y="'+(y-.6)+'" width="'+w+'" height="1.2" rx=".6" fill="var(--anatomy-shade-0)"/>';}).join(''),[0,-1,0]);
 // Right tray: representative amplifier and DC distribution, no mains hardware.
 box('audio','tray',18,-42,24,84,84,3,'steel',1);
 box('audio','ampPcb',24,-31,27,34,24,1.6,'gunmetal',.3);
 box('audio','ampIC',34,-24,28.6,10,8,2,'rubber',.2);
 for(const x of [28,52])round('audio','capacitor.'+x,[x,-15,0],[0,0,1],28.6,37,2.5,'steel',{details:{seams:[35]}});
 box('audio','audioTerminal',25,-31,28.6,7,5,6,'rubber',.3);
 box('audio','dcBoard',25,8,27,48,27,1.6,'gunmetal',.4);
 box('audio','dcModule',29,13,28.6,16,16,6,'steel',.4);
 for(let i=0;i<3;i++)box('audio','dcTerminal.'+i,51+i*7,24,28.6,6,8,7,'rubber',.3);
 box('audio','dcSocket',79,16,27,13,14,10,'gunmetal',.4);
 box('audio','bridge',73,20,27,6,6,1.6,'steel',.1);
 // Mic on the rear face; housing and mesh remain a single assembly.
 box('mic','mount',66,-60,151,18,2,13,'steel',.3);
 box('mic','housing',68,-66,153,14,6,9,'gunmetal',1);
 const mic=box('mic','mesh',69,-66.4,154,12,.4,7,'steel',.3);
 plane(mic,[69,-66.4,154],[1,0,0],[0,0,1],Array.from({length:5},(_,i)=>'<rect x="'+(1+i*2)+'" y="1" width=".6" height="5" rx=".3" fill="var(--anatomy-shade-0)"/>').join(''),[0,-1,0]);
 const out=T.build({statics:R.items,poses,verify:true});
 return {P,R,T,out};
}
