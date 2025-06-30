from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from datetime import datetime
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


class Family(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    ghatak = db.Column(db.String(50), nullable=False)
    pradeshik = db.Column(db.String(50), nullable=False)
    k_name = db.Column(db.String(50), nullable=False)
    k_village = db.Column(db.String(50), nullable=False)
    village = db.Column(db.String(50), nullable=False)
    gotra = db.Column(db.String(50), nullable=True)
    res_add = db.Column(db.Text(50), nullable=False)
    res_phone = db.Column(db.Integer, nullable=False)
    off_add = db.Column(db.Text(50), nullable=True)
    off_phone = db.Column(db.Integer, nullable=True)
    mem_num = db.Column(db.Integer, nullable=False)
    date = db.Column(DateTime)
    
    
class Kuldevi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    
    
class village(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    
    
class member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    ghatak = db.Column(db.String(50), nullable=False)
    pradeshik = db.Column(db.String(50), nullable=False)
    k_name = db.Column(db.String(50), nullable=False)
    k_village = db.Column(db.String(50), nullable=False)
    village = db.Column(db.String(50), nullable=False)
    gotra = db.Column(db.String(50), nullable=True)
    res_add = db.Column(db.Text(50), nullable=False)
    res_phone = db.Column(db.Integer, nullable=False)
    off_add = db.Column(db.Text(50), nullable=True)
    off_phone = db.Column(db.Integer, nullable=True)
    mem_num = db.Column(db.Integer, nullable=False)
    date = db.Column(DateTime)



@app.route('/', methods=['POST', 'GET'])
def welcome():
    if 'user' in session and session['user'] == admin_user:
        if request.method == 'POST':
            try:
                print("Processing form submission...")
                # gather form data
                name = request.form.get('last_name') + request.form.get('first_name') + " Bhai" + request.form.get('middle_name') + " Bhai"
                email = request.form.get('email')
                ghatak = request.form.get('ghatak')
                pradeshik = request.form.get('pradeshik')
                kuldevi_name = request.form.get('kuldevi[]')
                kuldevi_village = request.form.get('kuldevi_village')
                native_village = request.form.get('native_village')
                gotra = request.form.get('gotra')
                address1 = request.form.get('building') + " | " + request.form.get('area') + " | " + request.form.get('street') + " | " + request.form.get('landmark') + " | " + request.form.get('pincode')
                address2 = request.form.get('office_building') + " | " + request.form.get('office_area') + " | " + request.form.get('office_street') + " | " + request.form.get('office_landmark') + " | " + request.form.get('office_pincode')
                phone1 = int(request.form.get('res_phone'))
                phone2_raw = request.form.get('office_phone')
                phone2 = int(phone2_raw) if phone2_raw and phone2_raw.isdigit() else None
                num_of_memb = int(request.form.get('family_members'))
                date = datetime.now()

                entry = Family(
                    name=name, email=email, ghatak=ghatak, pradeshik=pradeshik, date=date,
                    k_name=kuldevi_name, k_village=kuldevi_village, village=native_village, gotra=gotra,
                    res_add=address1, res_phone=phone1, off_add=address2, off_phone=phone2, mem_num=num_of_memb
                )
                db.session.add(entry)
                db.session.commit()
                print("Data saved successfully.")
            except Exception as e:
                print("Error during form processing:", e)
                flash("Error submitting form.")
        return render_template('form1.html')
    elif request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('pass')
        if username == admin_user and password == admin_password:
          session['user'] = username
          return render_template('form1.html')
    return render_template('index.html')
                         
                         
@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel_main():
    if 'user' in session and session['user'] == admin_user:
        try:
            data = Family.query.all()
            print(f"Retrieved {len(data)} entries.")
            return render_template('admin_panel.html', data=data)
        except Exception as e:
            print("Database query failed:", e)
            flash("Failed to retrieve data.")
    return redirect('/')


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=3000, debug=True)