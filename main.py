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
app.config['SQLALCHEMY_ECHO'] = True

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
    res_add = db.Column(db.Text, nullable=False)
    res_phone = db.Column(db.Integer, nullable=False)
    off_add = db.Column(db.Text, nullable=True)
    off_phone = db.Column(db.Integer, nullable=True)
    mem_num = db.Column(db.Integer, nullable=False)
    date = db.Column(DateTime)
    
    
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    father = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(50), nullable=False)
    relation = db.Column(db.String(50), nullable=False)
    peear = db.Column(db.String(50), nullable=True)
    marriage = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(50), nullable=True)
    edu = db.Column(db.String(50), nullable=False)
    occu = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=True)
    blood = db.Column(db.String(50), nullable=False)
    family = db.relationship('Family', backref=db.backref('members', lazy=True))


@app.route('/', methods=['GET', 'POST'])
def form1():
    if request.method == 'POST':
            try:
                print("Processing form submission...")
                name = request.form.get('last_name') + " " + request.form.get('first_name') + " " + request.form.get('middle_name') 
                email = request.form.get('email')
                ghatak = request.form.get('ghatak')
                pradeshik = request.form.get('pradeshik')
                kuldevi_name = request.form.getlist('kuldevi[]')
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
                    k_name=", ".join(kuldevi_name), k_village=kuldevi_village, village=native_village, gotra=gotra,
                    res_add=address1, res_phone=phone1, off_add=address2, off_phone=phone2, mem_num=num_of_memb
                )
                db.session.add(entry)
                db.session.commit()
                print(f"Saved Family with ID: {entry.id}")
                print("Data saved successfully.")
                mem = str(num_of_memb)
                if mem:
                    return redirect(f'/form2/{mem}?family_id={entry.id}')
            except Exception as e:
                print("Error during form processing:", e)
                flash("Error submitting form.")
                return render_template('form1.html')
    return render_template('form1.html')
  

@app.route('/form2/<int:mem>', methods=['GET', 'POST'])
def form2(mem):
    family_id = request.args.get('family_id', type=int)
    if request.method == 'POST':
        try:
            ln_list = request.form.getlist('ln[]')
            fn_list = request.form.getlist('fn[]')
            mn_list = request.form.getlist('mn[]')
            fln_list = request.form.getlist('fln[]')
            ffn_list = request.form.getlist('ffn[]')
            fmn_list = request.form.getlist('fmn[]')
            gender_list = request.form.getlist('gender[]')
            relation_list = request.form.getlist('relation[]')
            peear_list = request.form.getlist('peear[]')
            marriage_list = request.form.getlist('marriage[]')
            dob_list = request.form.getlist('dob[]')
            photo_list = request.form.getlist('photo[]') 
            edu_list = request.form.getlist('edu[]')
            occu_list = request.form.getlist('occu[]')
            phone_list = request.form.getlist('phone[]')
            email_list = request.form.getlist('email[]')
            blood_list = request.form.getlist('blood[]')

            
            for i in range(mem):
                entry = Member(
                    family_id=family_id,
                    name=f"{ln_list[i]} {fn_list[i]} {mn_list[i]}",
                    father=f"{fln_list[i]} {ffn_list[i]} {fmn_list[i]}",
                    gender=safe_get(gender_list, i),
                    relation=relation_list[i],
                    peear=safe_get(peear_list, i),
                    marriage=safe_get(marriage_list, i),
                    dob=safe_get(dob_list, i),
                    photo=safe_get(photo_list, i),
                    edu=safe_get(edu_list, i),
                    occu=safe_get(occu_list, i),
                    phone=int(phone_list[i]),
                    email=safe_get(email_list, i),
                    blood=safe_get(blood_list, i)
                )
                print("Expected number of members (mem):", mem)
                print("ln_list:", len(ln_list))
                print("fn_list:", len(fn_list))
                print("mn_list:", len(mn_list))
                print("fln_list:", len(fln_list))
                print("ffn_list:", len(ffn_list))
                print("fmn_list:", len(fmn_list))
                print("gender_list:", len(gender_list))
                print("relation_list:", len(relation_list))
                print("marriage_list:", len(marriage_list))
                print("dob_list:", len(dob_list))
                print("edu_list:", len(edu_list))
                print("occu_list:", len(occu_list))
                print("phone_list:", len(phone_list))
                print("blood_list:", len(blood_list))

                db.session.add(entry)
            db.session.commit()
            flash("All members saved successfully.")
            return redirect(f'/summary/{family_id}')
        except Exception as e:
            print("Error:", e)
            flash("Error submitting form.")
            return render_template('form2.html', mem=mem)
    return render_template('form2.html', mem=mem, family_id=family_id)


def safe_get(lst, i, default="N/A"):
    return lst[i] if i < len(lst) and lst[i] else default
  

@app.template_filter('format_date_for_input')
def format_date_for_input(date_str):
    if not date_str:
        return ''
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ''  # fallback if no format matches



@app.route('/summary/<int:family_id>', methods=['GET', 'POST'])
def summary(family_id):
    family = Family.query.get_or_404(family_id)
    return render_template('final.html', family=family)
  

@app.route("/edit/<string:type>/<string:id>", methods=['GET', 'POST'])
def editing_sec(id, type):
        if type == 'family':
            fam = Family.query.filter_by(id=id).first() if id != 'new' else None
            if request.method == 'POST':
                name = name = request.form.get('last_name') +" "+ request.form.get('first_name') + " " + request.form.get('middle_name') 
                email = request.form.get('email')
                ghatak = request.form.get('ghatak')
                pradeshik = request.form.get('pradeshik')
                kuldevi_name = request.form.getlist('kuldevi[]')
                kuldevi_village = request.form.get('kuldevi_village')
                native_village = request.form.get('native_village')
                gotra = request.form.get('gotra')
                address1 = request.form.get('building') + " | " + request.form.get('area') + " | " + request.form.get('street') + " | " + request.form.get('landmark') + " | " + request.form.get('pincode')
                address2 = request.form.get('office_building') + " | " + request.form.get('office_area') + " | " + request.form.get('office_street') + " | " + request.form.get('office_landmark') + " | " + request.form.get('office_pincode')
                phone1 = int(request.form.get('res_phone'))
                phone2_raw = request.form.get('office_phone')
                phone2 = int(phone2_raw) if phone2_raw and phone2_raw.isdigit() else None
                num_of_memb = int(request.form.get('family_members'))
              
                fam = Family.query.filter_by(id=id).first()
                if fam:
                    fam.name = name
                    fam.email = email
                    fam.ghatak = ghatak
                    fam.pradeshik = pradeshik
                    fam.k_name = ", ".join(kuldevi_name)
                    fam.k_village = kuldevi_village
                    fam.village = native_village
                    fam.gotra = gotra
                    fam.res_add = address1
                    fam.res_phone = phone1
                    fam.off_add = address2
                    fam.off_phone = phone2
                    fam.mem_num = num_of_memb
              
                db.session.add(fam)
                db.session.commit()
                return redirect('/summary/' + id)
            return render_template('edit_f.html', id=id, fam=fam, type=type)
        elif type == 'member':
            mem = Member.query.filter_by(id=id).first() if id != 'new' else None
            if request.method == 'POST':
                ln = request.form.get('ln')
                fn = request.form.get('fn')
                mn = request.form.get('mn')
                fln = request.form.get('fln')
                ffn = request.form.get('ffn')
                fmn = request.form.get('fmn')
                gender = request.form.get('gender')
                relation = request.form.get('relation')
                peear = request.form.get('peear')
                marriage = request.form.get('marriage')
                dob = request.form.get('dob')
                photo = request.form.get('photo') 
                edu = request.form.get('edu')
                occu = request.form.get('occu')
                phone = request.form.get('phone')
                email = request.form.get('email')
                blood = request.form.get('blood')
                name=f"{ln} {fn} {mn}"
                father=f"{fln} {ffn} {fmn}"
                
                id_list = id.split("?")
                family_id = request.args.get('family_id', type=int)
                print(family_id)
                
                if not id_list[0] or id_list[0] == 'new':
                    mem = Member(id=None, family_id=family_id, name=name, father=father, gender=gender, relation=relation, dob=dob, photo=photo, peear=peear, marriage=marriage, edu=edu, occu=occu, email=email, phone=phone, blood=blood)
                    fam = Family.query.filter_by(id=family_id).first()
                    fam.mem_num += 1
                    db.session.add(mem)
                    db.session.commit()
                    return redirect('/summary/' + str(family_id))
                else:
                    mem = Member.query.filter_by(id=id).first() if id != 'new' else None
                    if mem:
                        mem.name = name
                        mem.father = father
                        mem.gender = gender 
                        mem.relation = relation 
                        mem.peear = peear
                        mem.marriage = marriage 
                        mem.dob = dob 
                        mem.photo = photo 
                        mem.occu = occu  
                        mem.phone = phone 
                        mem.email = email 
                        mem.blood = blood 
                        family_id = mem.family_id
                        
                        db.session.commit()
                        return redirect('/summary/' + str(family_id))
            return render_template('edit_m.html', id=id, mem=mem, type=type)


@app.route("/delete/<string:id>/<int:family_id>")
def delete(id, family_id):
    post = Member.query.filter_by(id=id).first() if id != 'new' else None
    fam = Family.query.filter_by(id=family_id).first()
    fam.mem_num -= 1
    db.session.delete(post)
    db.session.commit()
    return redirect(f'/summary/{family_id}')
  
  
@app.route("/submit")
def submit():
    family_id = request.args.get('family_id', type=int)
    print(family_id)
    return render_template('end.html')
  
  


@app.route('/admin_panel', methods=['GET', 'POST'])
def admin_panel_main():
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('pass')

        if username == admin_user and password == admin_password:
            session['user'] = username
            data = Member.query.all()
            return render_template('admin_panel2.html', data=data)
        else:
            flash('Invalid login')
            return render_template('index.html')
    if 'user' in session and session['user'] == admin_user:
        data = Member.query.all()
        return render_template('admin_panel2.html', data=data)

    return render_template('index.html')

    
    
@app.route('/admin_panel1', methods=['GET', 'POST'])
def admin_panel1():
    if 'user' in session and session['user'] == admin_user:
        try:
            data = Family.query.all()
            print(f"Retrieved {len(data)} entries.")
            return render_template('admin_panel.html', data=data)
        except Exception as e:
            print("Database query failed:", e)
            flash("Failed to retrieve data.")
    return redirect('/')

  
@app.route('/admin_panel2', methods=['GET', 'POST'])
def admin_panel2():
    if 'user' in session and session['user'] == admin_user:
        try:
            data = Member.query.all()
            print(f"Retrieved {len(data)} entries.")
            return render_template('admin_panel2.html', data=data)
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