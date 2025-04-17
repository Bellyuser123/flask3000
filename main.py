from flask import Flask, render_template, request, session, redirect, flash

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def welcome():
  if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            return render_template('main.html')
        return render_template('main.html')
    elif request.method == 'POST':
        username = request.form.get('email')
        password = request.form.get('pass')
        if username == params['admin_user'] and password == params['admin_password']:
            session['user'] = username
            return render_template('main.html')
    return render_template('index.html')
  
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)