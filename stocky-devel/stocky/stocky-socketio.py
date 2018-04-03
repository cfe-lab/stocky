
# The stocky main Flask program
import flask
from flask_socketio import SocketIO

from random import random
from time import sleep
from threading import Thread, Event


app = flask.Flask(__name__.split('.')[0])
socky = SocketIO(app)

# https://github.com/shanealynn/async_flask/blob/master/application.py
# random number Generator Thread
thread = Thread()
thread_stop_event = Event()


class RandomThread(Thread):
    def __init__(self):
        self.delay = 1
        super(RandomThread, self).__init__()

    def randomNumberGenerator(self):
        """
        Generate a random number every 1 second and emit to a socketio instance (broadcast)
        Ideally to be run in a separate thread?
        """
        # infinite loop of magical random numbers
        print("Making random numbers")
        while not thread_stop_event.isSet():
            number = round(random()*10, 3)
            print(number)
            socky.emit('newnumber', {'number': number}, namespace='/test')
            sleep(self.delay)

    def run(self):
        self.randomNumberGenerator()


# this is required to server the javascript code
@app.route('/webclient/__javascript__/<path:path>')
def send_js(path):
    return flask.send_from_directory('webclient/__javascript__', path)


@app.route('/')
def main_page():
    return flask.render_template('mainpage.html', sconame='Danny Boy')


# @socky.on('connect', namespace='/test')
@socky.on('connect')
def test_connect():
    # need visibility of the global thread object
    global thread
    print('Client connected')
    # Start the random number generator thread only if the thread has not been started before.
    if not thread.isAlive():
        print("Starting Thread")
        thread = RandomThread()
        thread.start()


# @socky.on('disconnect', namespace='/test')
@socky.on('disconnect')
def test_disconnect():
    print('Client disconnected')


if __name__ == "__main__":
    socky.run(app)
