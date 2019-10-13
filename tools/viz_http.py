"""Serve pyramid files over HTTP."""
import argparse
import os
import sys

from http.server import BaseHTTPRequestHandler, HTTPServer

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dir', action='store', required=True, help='Tiles directory.')
parser.add_argument(
    '-s', '--split', type=int, action='store', required=True,
    help='Number of splits (columns).', default=8)
parser.add_argument(
    '-t', '--total_size', type=int, action='store', required=True,
    help='Total file of the original dump file')
parser.add_argument(
    '-p', '--page_size', type=int, action='store', required=True,
    help='Length of a page (userdata + oob)')
args = parser.parse_args()

tiles_dir = args.dir
nb_splits = args.split
total_size = args.total_size
page_size = args.page_size
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
    <div id="mapid" style="height:400px; width: 600px; cursor:crosshair"></div>
    <div id="vals">
      Lng at right of first col: <input type="text" id="onecol"><br>
      Lat at bottom of first col: <input type="text" id="maxlat"><br>
    </div>
    <script>
    function getInputVal(input_id) {return parseFloat(document.getElementById(input_id).value) || -1};
    function latlng_to_page_num(latlng, nb_cols, total_size, page_size) {
        console.log(latlng.toString());
        var one_col_width = getInputVal('onecol');
        var maxlat = getInputVal('maxlat');
        if (one_col_width==-1 || maxlat ==-1) {
          console.log('Not enough info');
          return "";
        }
        var column = Math.ceil(latlng.lng / one_col_width);
        var total_pages = total_size / page_size;
        var pages_per_column = total_pages / nb_cols;

        var page_num = Math.floor(pages_per_column * (column - 1) + (pages_per_column/maxlat)*latlng.lat);
        var offset_in_page = Math.floor((latlng.lng%%one_col_width) * page_size / one_col_width);
        var offset = Math.floor((page_num)*(page_size) + offset_in_page);
        var res = "<ul>";
        res += "<li> Offset in page: " + offset_in_page + "</li>";
        res += "<li> Offset in dump: " + offset + " / 0x" + offset.toString(16).toUpperCase() + "</li>"
        res += "<li> Page Number: "+page_num+"</li>"
//        res += "<li> lat: "+latlng.lat+"</li>"
//        res += "<li> lng: "+latlng.lng+"</li>"
//        res += "<li> column: "+column+"</li>"
        res+="</ul>";
        return res;
    };

    var onMapClick = function(e) {
        if (e.latlng.lng < 0 || e.latlng.lng > 256) { return;};
        if (e.latlng.lat > 0 || e.latlng.lat < -256) { return;};
        var msg =  latlng_to_page_num(e.latlng, %d, %d, %d);
        if (msg == "") { return; }
        var marker = L.marker(
            [e.latlng.lat, e.latlng.lng]
        ).addTo(map).bindPopup(msg);
    };

        var map = L.map('mapid', {
            maxZoom: 9,
            zoomControl: false,
            crs: L.CRS.Simple,
            attributionControl: false,
        }).setView([0, 0], 0);
        var layer = L.tileLayer('/%s/{z}/{y}/{x}.jpg',{
            noWrap: true,
        }).addTo(map);
        map.on('click', onMapClick);
    </script>
</body></html>
"""%(nb_splits, total_size, page_size, map_id)

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

start_port = 8000
end_port = 9000
for port in range(start_port, end_port):
    try:
        httpd = HTTPServer(('', port), RequestHandler)
        print('Starting Webserver on http://localhost:{0:d}/'.format(port))
        print('Hit Ctrl-C to quit')
        httpd.serve_forever()
    except OSError:
        pass
