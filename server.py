from flask import flask

app = flask(__name__)

@app.route('/')
def welcome():
    return render_template('index.html')