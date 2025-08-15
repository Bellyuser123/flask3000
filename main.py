from flask import Flask, render_template, request, session, redirect, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
import pandas as pd, openpyxl
from datetime import datetime
import os
import io


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
# app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)


class Kuldevi(db.Model):
    id = db.Column(db.SmallInteger, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class Village(db.Model):
    id = db.Column(db.SmallInteger, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class Gotra(db.Model):
    id = db.Column(db.SmallInteger, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class Blood(db.Model):
    id = db.Column(db.SmallInteger, primary_key=True)
    name = db.Column(db.String(50), nullable=False)


class Marriage(db.Model):
    id = db.Column(db.SmallInteger, primary_key=True)
    name = db.Column(db.String(50), nullable=False)


class Relation(db.Model):
    id = db.Column(db.SmallInteger, primary_key=True)
    name = db.Column(db.String(50), nullable=False)


family_kuldevi = db.Table(
    'family_kuldevi',
    db.Column('family_id', db.SmallInteger, db.ForeignKey('family.id'), primary_key=True),
    db.Column('kuldevi_id', db.SmallInteger, db.ForeignKey('kuldevi.id'), primary_key=True)
)


class Family(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    ghatak = db.Column(db.String(50), nullable=False)
    pradeshik = db.Column(db.String(50), nullable=False)
    kuldevi = db.relationship('Kuldevi', secondary=family_kuldevi, backref='families')
    k_village = db.Column(db.SmallInteger, db.ForeignKey('village.id'), nullable=False)
    village = db.Column(db.SmallInteger, db.ForeignKey('village.id'), nullable=False)
    gotra = db.Column(db.SmallInteger, db.ForeignKey('gotra.id'), nullable=False)
    res_add = db.Column(db.Text, nullable=False)
    res_phone = db.Column(db.Integer, nullable=False)
    off_add = db.Column(db.Text, nullable=True)
    off_phone = db.Column(db.Integer, nullable=True)
    mem_num = db.Column(db.SmallInteger, nullable=False)
    date = db.Column(DateTime)
    gotra_rel = db.relationship('Gotra')
    village_rel = db.relationship('Village', foreign_keys=[village])
    k_village_rel = db.relationship('Village', foreign_keys=[k_village])


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    father = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(50), nullable=False)
    relation = db.Column(db.SmallInteger, db.ForeignKey('relation.id'), nullable=False)
    peear = db.Column(db.String(50), nullable=True)
    marriage = db.Column(db.SmallInteger, db.ForeignKey('marriage.id'), nullable=False)
    dob = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(50), nullable=True)
    edu = db.Column(db.String(50), nullable=False)
    occu = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=True)
    blood = db.Column(db.SmallInteger, db.ForeignKey('blood.id'), nullable=False)
    family = db.relationship('Family', backref=db.backref('members', lazy=True))
    blood_rel = db.relationship('Blood')
    relation_rel = db.relationship('Relation')
    marriage_rel = db.relationship('Marriage')


@app.route('/export/all')
def export_all():
    if 'user' in session and session['user'] == admin_user:
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')

        # Families
        families = Family.query.all()
        df_families = pd.DataFrame([{
            'ID': f.id,
            'Name': f.name,
            'Email': f.email,
            'Gotra': f.gotra_rel.name if f.gotra_rel else '',
            'Village': f.village_rel.name if f.village_rel else '',
            'Kuldevi': ', '.join([k.name for k in f.kuldevi]),
            'Members': f.mem_num,
            'Date': f.date
        } for f in families])
        df_families.to_excel(writer, index=False, sheet_name='Families')

        # Members
        members = Member.query.all()
        df_members = pd.DataFrame([{
            'ID': m.id,
            'Family': m.family.name if m.family else '',
            'Name': m.name,
            'Father': m.father,
            'Gender': m.gender,
            'Relation': m.relation_rel.name if m.relation_rel else '',
            'Marriage': m.marriage_rel.name if m.marriage_rel else '',
            'DOB': m.dob,
            'Education': m.edu,
            'Occupation': m.occu,
            'Phone': m.phone,
            'Email': m.email,
            'Blood': m.blood_rel.name if m.blood_rel else ''
        } for m in members])
        df_members.to_excel(writer, index=False, sheet_name='Members')

        # Add other tables as needed...

        writer.close()
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name='all_data.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        return redirect("/admin")


@app.route("/submit/<int:id>", methods=['GET', 'POST'])
def submit(id):
    fam = Family.query.filter_by(id=id).first()
    mem = Member.query.filter_by(family_id=id).all()
    if fam.mem_num == len(mem):
        head = Member.query.filter_by(family_id=id, relation=1).first()
        if fam.name == head.name:
            return render_template('end.html')
        else:
            flash("Family Head name in Family details doesn't Match with Family head in Members details below", 'error')
    else:
        flash("Number of Family members doesn't match with provided Members", 'error')
    return redirect('/summary/' + str(id))


@app.route("/admin/user")
def users():
    if 'user' in session and session['user'] == admin_user:
        search = request.args.get('search', '')
        view = request.args.get("view", "quick")
        families = []
        members = []
        if view == "joined":
            members = db.session.query(Member).join(Family).all()
        elif view == "quick":
            families = Family.query.all()
        elif view == "families":
            families = Family.query.all()
        elif view == "members":
            members = Member.query.all()
        return render_template('users.html', view=view, search=search, families=families, members=members)
    else:
        return redirect("/admin")


@app.route('/admin/family/<int:family_id>/members')
def family_members_modal(family_id):
    family = Family.query.get_or_404(family_id)
    return render_template('partials/mem_lst.html', family=family)


@app.route('/admin/family/<int:family_id>/collapse-row')
def collapse_family_row(family_id):
    return render_template("partials/empty_row.html", family_id=family_id)


@app.route('/admin/member/<int:member_id>/partial')
def member_detail_partial(member_id):
    member = Member.query.get_or_404(member_id)
    return render_template('partials/mem_modal.html', member=member)


@app.route("/admin/report")
def report():
    if 'user' in session and session['user'] == admin_user:
        return render_template('report.html')
    else:
        return redirect("/admin")


@app.route("/admin/something")
def something():
    if 'user' in session and session['user'] == admin_user:
        return render_template('something.html')
    else:
        return redirect("/admin")


@app.route("/admin/dashboard")
def dashboard():
    if 'user' in session and session['user'] == admin_user:
        total_families = Family.query.count()
        total_members = Member.query.count()
        return render_template('dashboard.html', fam_count=total_families, mem_count=total_members)
    else:
        return redirect("/admin")


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('pass')

        if username == admin_user and password == admin_password:
            session['user'] = username
            return redirect('admin/dashboard')
        else:
            flash('Invalid login')
            return render_template('login.html')
    if 'user' in session and session['user'] == admin_user:
        return redirect('admin/dashboard')

    return render_template('login.html')


@app.route('/', methods=['GET', 'POST'])
def form1():
    if request.method == 'POST':
        try:
            name = request.form.get('last_name').lower() + " " + request.form.get('first_name').lower() + " " + request.form.get(
                'middle_name').lower()
            email = request.form.get('email')
            ghatak = request.form.get('ghatak').lower()
            pradeshik = request.form.get('pradeshik').lower()
            kuldevi_name = request.form.getlist('kuldevi[]')
            kuldevi_objs = Kuldevi.query.filter(Kuldevi.id.in_(kuldevi_name)).all()
            kuldevi_village = request.form.get('kuldevi_village')
            native_village = request.form.get('native_village')
            gotra = request.form.get('gotra')
            address1 = request.form.get('building') + " | " + request.form.get('area') + " | " + request.form.get(
                'street') + " | " + request.form.get('landmark') + " | " + request.form.get('pincode')
            address2 = request.form.get('office_building') + " | " + request.form.get(
                'office_area') + " | " + request.form.get('office_street') + " | " + request.form.get(
                'office_landmark') + " | " + request.form.get('office_pincode')
            phone1 = int(request.form.get('res_phone'))
            phone2_raw = request.form.get('office_phone')
            phone2 = int(phone2_raw) if phone2_raw and phone2_raw.isdigit() else None
            num_of_memb = int(request.form.get('family_members'))
            date = datetime.now()

            entry = Family(
                name=name, email=email, ghatak=ghatak, pradeshik=pradeshik, date=date,
                kuldevi=kuldevi_objs, k_village=kuldevi_village, village=native_village, gotra=gotra,
                res_add=address1, res_phone=phone1, off_add=address2, off_phone=phone2, mem_num=num_of_memb
            )
            db.session.add(entry)
            db.session.commit()
            mem = str(num_of_memb)
            if mem:
                return redirect(f'/form2/{mem}?family_id={entry.id}')
        except Exception as e:
            print("Error during form processing:", e)
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
                    name=f"{ln_list[i].lower()} {fn_list[i].lower()} {mn_list[i].lower()}",
                    father=f"{fln_list[i].lower()} {ffn_list[i].lower()} {fmn_list[i].lower()}",
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

                db.session.add(entry)
            db.session.commit()
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
    return render_template('summary.html', family=family)


@app.route("/edit/<string:type>/<string:id>", methods=['GET', 'POST'])
def editing_sec(id, type):
    if type == 'family':
        fam = Family.query.filter_by(id=id).first() if id != 'new' else None
        if request.method == 'POST':
            name = request.form.get('last_name').lower() + " " + request.form.get('first_name').lower() + " " + request.form.get(
                'middle_name').lower()
            email = request.form.get('email')
            ghatak = request.form.get('ghatak').lower()
            pradeshik = request.form.get('pradeshik').lower()
            kuldevi_name = request.form.getlist('kuldevi[]')
            kuldevi_village = request.form.get('kuldevi_village')
            native_village = request.form.get('native_village')
            gotra = request.form.get('gotra')
            address1 = request.form.get('building') + " | " + request.form.get('area') + " | " + request.form.get(
                'street') + " | " + request.form.get('landmark') + " | " + request.form.get('pincode')
            address2 = request.form.get('office_building') + " | " + request.form.get(
                'office_area') + " | " + request.form.get('office_street') + " | " + request.form.get(
                'office_landmark') + " | " + request.form.get('office_pincode')
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
                fam.kuldevi = Kuldevi.query.filter(Kuldevi.id.in_(kuldevi_name)).all()
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
            ln = request.form.get('ln').lower()
            fn = request.form.get('fn').lower()
            mn = request.form.get('mn').lower()
            fln = request.form.get('fln').lower()
            ffn = request.form.get('ffn').lower()
            fmn = request.form.get('fmn').lower()
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
            name = f"{ln} {fn} {mn}"
            father = f"{fln} {ffn} {fmn}"

            id_list = id.split("?")
            family_id = request.args.get('family_id', type=int)

            if not id_list[0] or id_list[0] == 'new':
                mem = Member(id=None, family_id=family_id, name=name, father=father, gender=gender, relation=relation,
                             dob=dob, photo=photo, peear=peear, marriage=marriage, edu=edu, occu=occu, email=email,
                             phone=phone, blood=blood)
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


@app.route("/admin/delete_mem/<string:id>/<int:family_id>")
def admin_delete_mem(id, family_id):
    if 'user' in session and session['user'] == admin_user:
        post = Member.query.filter_by(id=id).first() if id != 'new' else None
        fam = Family.query.filter_by(id=family_id).first()
        fam.mem_num -= 1
        db.session.delete(post)
        db.session.commit()
        return redirect(f'/admin/user')


@app.route("/admin/delete_fam/<int:family_id>")
def admin_delete_fam(family_id):
    if 'user' in session and session['user'] == admin_user:
        post = Family.query.filter_by(id=family_id).first() if id != 'new' else None
        members = Member.query.filter_by(family_id=family_id).all() if id != 'new' else None
        if members:
            for member in members:
                db.session.delete(member)
        db.session.delete(post)
        db.session.commit()
        return redirect(f'/admin/user?view=families')


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/')


def lookup_tables():
    if not Kuldevi.query.first():
        kuldevi_data = [
            (1, "Brahmani Maa"),
            (2, "Butbhavani Maa"),
            (3, "Chamunda Maa"),
            (4, "Chaval Maa"),
            (5, "Gatrad Maa"),
            (6, "Kalika Maa"),
            (7, "Khodiar Maa"),
            (8, "Momai Maa"),
            (9, "Pithad Maa"),
            (10, "Saval Maa"),
            (11, "Sikoter Maa"),
            (12, "Vishal Maa"),
            (13, "Truthiad Maa"),
        ]
        for kid, name in kuldevi_data:
            db.session.add(Kuldevi(id=kid, name=name))
        db.session.commit()
    if not Village.query.first():
        village_data = [
            (1, "Anjar"),
            (2, "Chandia"),
            (3, "Devaliya"),
            (4, "Galpadar"),
            (5, "Hajapar"),
            (6, "Jambudi"),
            (7, "Khambhra"),
            (8, "Khedol"),
            (9, "Kumbharia"),
            (10, "Kukma"),
            (11, "Lovaria"),
            (12, "Madhapar"),
            (13, "Meghpar"),
            (14, "Nagalpar"),
            (15, "Nagor"),
            (16, "Reha"),
            (17, "Sinogara"),
            (18, "Vidi"),
        ]
        for vid, name in village_data:
            db.session.add(Village(id=vid, name=name))
        db.session.commit()
    if not Gotra.query.first():
        gotra_data = [
            (1, "ATREE"),
            (2, "BHARDWAJ"),
            (3, "GARG"),
            (4, "GAUTAM"),
            (5, "KASHYAP"),
            (6, "KAUDINYA"),
            (7, "SANKADI"),
            (8, "SHANDIL"),
            (9, "SHAUNAK"),
            (10, "SONAL"),
            (11, "VALMIK"),
            (12, "VARSHA"),
            (13, "VASHISHTHA"),
            (14, "VATSA"),
            (15, "VISHVAMITRA"),
            (16, "OTHER"),
        ]
        for gid, name in gotra_data:
            db.session.add(Gotra(id=gid, name=name))
        db.session.commit()
    if not Blood.query.first():
        blood_data = [
            (1, "A+"),
            (2, "A-"),
            (3, "B+"),
            (4, "B-"),
            (7, "AB+"),
            (8, "AB-"),
            (5, "O+"),
            (6, "O-"),
        ]
        for bid, name in blood_data:
            db.session.add(Blood(id=bid, name=name))
        db.session.commit()
    if not Marriage.query.first():
        marriage_data = [
            (1, "Married"),
            (2, "Unmarried"),
            (3, "Divorced"),
            (4, "Widowed"),
        ]
        for mid, name in marriage_data:
            db.session.add(Marriage(id=mid, name=name))
        db.session.commit()
    if not Relation.query.first():
        relation_data = [
            (1, "Self"),
            (2, "Father"),
            (3, "Mother"),
            (4, "Wife"),
            (5, "Husband"),
            (6, "Son"),
            (7, "Daughter"),
            (8, "Brother"),
            (9, "Sister"),
            (10, "Grandfather"),
            (11, "Grandmother"),
            (12, "Grandson"),
            (13, "Granddaughter"),
            (14, "Father-in Law"),
            (15, "Mother-in Law"),
            (16, "Daughter-in Law"),
            (17, "Son-in Law"),
            (18, "Other"),
        ]
        for rid, name in relation_data:
            db.session.add(Relation(id=rid, name=name))
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        lookup_tables()
    app.run(host='0.0.0.0', port=3000, debug=True)
