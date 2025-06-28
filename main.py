from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
import os


local_server = True

app = Flask(__name__)

app.secret_key = os.getenv('key')
admin_user = os.getenv('admin_user')
admin_password = os.getenv('admin_password')


base_dir = os.path.abspath(os.path.dirname(__file__))
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('local_uri') + os.path.join(base_dir, 'data', 'database.db')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('prod_uri') + os.path.join(base_dir, 'data', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(DateTime)



@app.route('/', methods=['POST', 'GET'])
def welcome():
  if 'user' in session and session['user'] == admin_user:
    if request.method == 'POST':
      return render_template('main.html')
    return render_template('main.html')
  elif request.method == 'POST':
    username = request.form.get('name')
    password = request.form.get('pass')
    if username == admin_user and password == admin_password:
      session['user'] = username
      return render_template('main.html')
  return render_template('index.html
                         
                         
@app.route('/admin_panel', methods=['POST', 'GET'])
def admin_panel_main():
    if 'user' in session and session['user'] == admin_user:
        return render_template('')


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=3000, debug=True)