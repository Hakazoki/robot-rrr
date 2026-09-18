import cv2
import http.server
import socketserver
import time

PORT = 8080

class CamStreamHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/?action=stream') or self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()

            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)

            try:
                while True:
                    success, frame = cap.read()
                    if not success:
                        time.sleep(0.01)
                        continue

                    ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if not ret:
                        continue

                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpeg)))
                    self.end_headers()
                    self.wfile.write(jpeg.tobytes())
                    self.wfile.write(b'\r\n')
            except (ConnectionResetError, BrokenPipeError):
                pass
            finally:
                cap.release()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    server = ThreadedHTTPServer(('0.0.0.0', PORT), CamStreamHandler)
    server.serve_forever()