"""Serve pyramid files over HTTP."""
import argparse
import os
import sys

from http.server import BaseHTTPRequestHandler, HTTPServer

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dir', action='store', required=True, help='Tiles directory.')
args = parser.parse_args()

tiles_dir = args.dir
if not os.path.isdir(tiles_dir):
    print('{0:s} is not a directory'.format(tiles_dir))
    sys.exit(1)
map_id = os.path.basename(os.path.normpath(tiles_dir))

MAIN_HTML = """
<!DOCTYPE html>
<html><head>
    <link crossorigin="" href="https://unpkg.com/leaflet@1.5.1/dist/leaflet.css" integrity="sha512-xwE/Az9zrjBIphAcBb3F6JVqxf46+CDLwfLMHloNu6KEQCAWi6HcDUbeOfBIptF7tcCzusKFjFw2yuvEpDL9wQ==" rel="stylesheet" />
    <script crossorigin="" integrity="sha512-GffPMF3RvMeYyc1LWMHtK8EbPv0iNZ8/oTtHPx9/cc2ILxQ+u905qIwdpULaqDkyBKgOaB57QTMg7ztg8Jm2Og==" src="https://unpkg.com/leaflet@1.5.1/dist/leaflet.js"></script>
</head><body>
    <div id="mapid" style="height:400px; width: 600px"></div>
    <script>
        var map = L.map('mapid', {
            maxZoom: 9,
            zoomControl: false,
            crs: L.CRS.Simple,
            attributionControl: false,
        }).setView([0, 0], 0);
        var layer = L.tileLayer('/%s/{z}/{y}/{x}.jpg',{
            noWrap: true,
        }).addTo(map);
    </script>
</body></html>
"""%(map_id)

class RequestHandler(BaseHTTPRequestHandler):
    """Class to handle http requests."""

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle GET requests"""
        content = self.HandleHTTP()
        self.wfile.write(content)

    def HandleHTTP(self):
        """Actually handle the request for tiles & such..."""
        res = b'ERROR'
        if self.path in ['/', '/index.html']:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            res = MAIN_HTML.encode()
        elif self.path.startswith('/{0:s}/'.format(map_id)):
            _, _, z, y, x = self.path.split('/')
            tile = os.path.join(args.dir, z, y, x)
            if os.path.isfile(tile):
                self.send_response(200)
                ext = os.path.splitext(tile)
                if ext == '.png':
                    self.send_header('Content-type', 'image/png')
                elif ext == '.jpg':
                    self.send_header('Content-type', 'image/jpeg')
                self.end_headers()
                with open(tile, 'rb') as f:
                    res = f.read()
            else:
                self.send_error(404, 'File Not Found: %s' % self.path)
        else:
            self.send_error(404, 'File Not Found: %s' % self.path)
        return res

httpd = HTTPServer(('', 8000), RequestHandler)
httpd.serve_forever()
