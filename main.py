from flask import Flask, render_template, request, session, redirect, flash
import os

app = Flask(__name__)

admin_user = os.getenv('admin_user')
admin_password = os.getenv('admin_password')

@app.route('/', methods=['POST', 'GET'])
def welcome():
  if 'user' in session and session['user'] == admin_user:
    if request.method == 'POST':
      return render_template('main.html')
    return render_template('main.html')
  elif request.method == 'POST':
    username = request.form.get('email')
    password = request.form.get('pass')
    if username == admin_user and password == admin_password:
      session['user'] = username
      return render_template('main.html')
  return render_template('index.html')
  
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)