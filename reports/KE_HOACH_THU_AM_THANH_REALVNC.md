# Thử truyền âm thanh từ Pi 4 qua RealVNC Viewer

**Chờ thử.** Ngày 07/11/2026, nhóm dời bài thử này sang một lượt sau. Pi 4 đã phát được âm thanh qua tai nghe 3,5 mm. Bài thử này kiểm tra xem âm thanh phát trên Pi có nghe được qua loa laptop trong phiên RealVNC đang dùng hay không. [Kết quả thử trên Pi](../HUONG_DAN_NH2067_PI4.md)

## Các bước khi thử lại

1. Kết nối vào Pi bằng **RealVNC Viewer** trên laptop. Tìm biểu tượng **Audio** trên thanh công cụ của phiên và bật tiếng nếu điều khiển này khả dụng.
2. Trong cửa sổ VNC, mở `voice-test.wav` bằng trình phát trên **desktop Pi**. Nếu file cũ không còn, dùng một file âm thanh có sẵn trên Pi.
3. Nghe ở **loa laptop** và ghi lại kết quả. Nếu biểu tượng **Audio** không hiện, bị mờ hoặc đã bật mà laptop vẫn im lặng, kiểm tra phần mềm máy chủ trên Pi, quyền **Audio** và chế độ của phiên. Tính năng truyền âm thanh của RealVNC cần máy chủ cho phép âm thanh và phiên dùng **High-Speed Streaming (RFB 6)**. [Tài liệu âm thanh của RealVNC](https://help.realvnc.com/hc/en-us/articles/360002504358-Audio-in-RealVNC-Connect)

## Ghi kết quả

- **Ngày thử** — Chờ ghi.
- **Biểu tượng Audio** — Chờ ghi trạng thái.
- **Loa laptop** — Chờ ghi có nghe được tiếng phát từ Pi hay không.
