
#WebSocket + Tornado + Redis Pub/Sub usage.
from functools import partial
import threading
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import redis
import os


# This is ugly but I did not want to create multiple files for a so trivial
# example.
TEMPLATE = """
<!DOCTYPE>
<html>
<head>
    <title>Sample chat</title>
    <script type="text/javascript" src="static/jquery.js"></script>
</head>
<body>
    <form method='POST' action='./'>
        <textarea name='data' id="data"></textarea>
        <div><input type='submit'></div>
    </form>
    <div id="log"></div>
    <script type="text/javascript" charset="utf-8">
        $(document).ready(function(){

            $('form').submit(function(event){
                var value = $('#data').val();
                $.post("./", { data: value }, function(data){
                    $("#data").val('');
                });
                return false;
            });


            if ("WebSocket" in window) {
              var ws = new WebSocket("ws://localhost:8888/chat/");
              ws.onopen = function() {};
              ws.onmessage = function (evt) {
                  var received_msg = evt.data;
                  var html = $("#log").html();
                  html += "<p>"+received_msg+"</p>";
                  $("#log").html(html);
              };
              ws.onclose = function() {};
            } else {
              alert("WebSocket not supported");
            }
        });
    </script>
</body>
</html>
"""


LISTENERS = []


def redis_listener():
    r = redis.Redis()
    ps = r.pubsub()
    ps.subscribe('chat')
    io_loop = tornado.ioloop.IOLoop.instance()
    for message in ps.listen():
        for element in LISTENERS:
            io_loop.add_callback(partial(element.on_message, message))


class NewMsgHandler(tornado.web.RequestHandler):
#    @tornado.web.authenticated
    def get(self):
        self.write(TEMPLATE)

    def post(self):
        data = self.get_argument('data')
        r = redis.Redis()
        r.publish('chat', data)


class RealtimeHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        LISTENERS.append(self)

    def on_message(self, message):
        self.write_message(message['data'])

    def on_close(self):
        LISTENERS.remove(self)


settings = {
    'auto_reload': True,
#    "login_url": "/login",
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
}

application = tornado.web.Application([
    (r'/', NewMsgHandler),
    (r'/chat/', RealtimeHandler),
 #   (r'/login', LoginHandler),
], **settings)


if __name__ == "__main__":
    threading.Thread(target=redis_listener).start()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
