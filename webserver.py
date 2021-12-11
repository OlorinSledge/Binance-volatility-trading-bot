"""
This module allows you to see the four main files of this bot through a web page. Once the bot and this module have started, 
we can access the page http: // localhost: 8000 / from our favorite browser and see choose the live mode or the simulation 
mode and the history, bot_stats, trades and coins_bought files will be displayed. Clarification, if any of these files do not 
exist or have not yet been created, it may show you an error in its presentation socket.
"""

import http.server
import socketserver

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        if self.path == '/':
            self.path = 'index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
		
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        print("Data: " + str(self.rfile.read(length), "utf-8"))

        response = bytes("This is the response.", "utf-8") #create response

        self.send_response(200) #create header
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response) #send response
		
def do_work():
    try:
        # Create an object of the above class
        handler_object = MyHttpRequestHandler

        PORT = 8000
        my_server = socketserver.TCPServer(("", PORT), handler_object)
	
        print("WebServer Started on PORT: " + str(PORT))
        # Star the server
        my_server.serve_forever()
    except Exception as e:
        print(f'{"WebServer"}: Exception do_work() 1: {e}')
        pass
    except KeyboardInterrupt as ki:
        pass