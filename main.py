from flask import Flask, render_template, request, session, redirect, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, extract, and_
import pandas as pd
import plotly
import plotly.graph_objects as go
import json
from rapidfuzz import fuzz
from datetime import datetime, timedelta
import os
import sqlite3
import re
import subprocess
import tempfile
from dotenv import load_dotenv
import io


load_dotenv()

local_server = True

app = Flask(__name__)

app.secret_key = os.getenv('key')
admin_user = os.getenv('admin_user')
admin_password = os.getenv('admin_password')

base_dir = os.path.abspath(os.path.dirname(__file__))
database_uri_prefix = os.getenv('local_uri', 'sqlite:///')
database_path = os.path.join(base_dir, 'data', 'database.db')
runtime_database_path = os.path.join(base_dir, 'data', 'database_runtime.db')


def resolve_local_database_uri():
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    if not os.path.exists(database_path):
        return database_uri_prefix + database_path

    try:
        with sqlite3.connect(database_path) as conn:
            conn.execute('PRAGMA schema_version;').fetchone()
        return database_uri_prefix + database_path
    except sqlite3.DatabaseError:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(os.path.dirname(database_path), f'database_invalid_{timestamp}.db')
        try:
            os.replace(database_path, backup_path)
            print(f"Invalid SQLite database detected. Backed up to {backup_path}")
            return database_uri_prefix + database_path
        except PermissionError:
            print(
                "Invalid SQLite database detected but the file is locked. "
                f"Using a fresh database at {runtime_database_path}"
            )
            return database_uri_prefix + runtime_database_path


if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = resolve_local_database_uri()
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('prod_uri')
# app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)

EDUCATION_OPTIONS = [
    ("uneducated", ["uneducated"]),
    ("schooling", [
        "nurecery/ KGI/ KGII",
        "class 1",
        "class 2",
        "class 3",
        "class 4",
        "class 5",
        "class 6",
        "class 7",
        "class 8",
        "class 9",
        "class 10",
    ]),
    ("senior secondary", [
        "class 11",
        "class 12",
    ]),
    ("diploma", ["diploma"]),
    ("Graduation 3 Years", [
        "bachlor of Laws - L.L.B",
        "bachlor of Commerce - B.Com",
        "bachlor of Computer Applications - B.C.A.",
        "bachlor of Business Administration - B.B.A",
        "bachlor of Library Science - B.Lib. / B.Lib.Sc.",
        "bachlor of Mass Communication - B.M.C./B.M.M.",
        "bachlor of Education - B.Ed.",
        "bachlor of Fine Arts - B.FA. / B.VA.",
        "bachlor of Fisherise Science - B.F.Sc.",
        "bachlor of Physical Education - B.P.Ed.",
        "bachlor of Science - B.Sc.",
        "bachlor of Social work - BSW / B.A. (SW)",
        "bachlor of Arts - B.A.",
        "graduation",
    ]),
    ("Graduation 4 Years", [
        "bachlor of Architechture - B.Arch.",
        "bachlor of Engineering/bachlor of Technology- B.E./B.Tech",
        "bachlor of Design - B.Des. / B.D.",
        "bachlor of Nursing",
        "bachlor of Pharmacy - B.Pharm. / B.Pharma.",
        "bachlor of Physiotherapy - B.P.T",
    ]),
    ("Graduation 5 Years", [
        "bachlor of Dential Surgery - B.D.S.",
        "bachlor of Medicine and bachlor of Surgery - M.B.B.S",
        "bachlor of Veterinary Science and Animal Husbandry- B.V.Sc. & A.H. / B.V.Sc.",
        "bachlor of Ayurvedic Medicine and Surgery- B.A.M.S.",
        "bachlor of Homoeopathic Medicine and Surgery- B.H.M.S.",
        "bachlor of Education - B.Ed.",
    ]),
    ("Post Graduation", [
        "Master of Architechture - M.Arch.",
        "Master of Arts - M.A.",
        "Master of Business Administration - M.B.A.",
        "Master of Chirurgiae - M.Ch.",
        "Master of Commerce - M.Com.",
        "Master of Computer Application - M.C.A.",
        "Master of Dential Surgery - M.D.S",
        "Master of Design- M.Des. / M.D",
        "Master of Education- M.Ed.",
        "Master of Engineering/Master of Technology - M.E. / M.Tech.",
        "Master of Fine Arts - M.FA / MVA",
        "Master of Laws - L.L.M.",
        "Master of Library Science - M.Lib. / M.Lib.Sc.",
        "Master of Mass Communication - M.M.C. / M.M.M.",
        "Master of Pharmacy - M.Pharm. / M.Pharma.",
        "Master of Philosophy - M.Phil.",
        "Master of Physiotherapy - M.P.T.",
        "Master of Science - M.Sc.",
        "Master of Social Work - M.S.W.",
        "Master of Surgery - M.S.",
        "Master of Veterinary Science - M.V.Sc.",
        "Masters",
    ]),
    ("Doctorate", [
        "Doctor of Medicine - M.D",
        "Doctor of Medicine in Homoeopathy - M.D",
        "Doctor of Philosophy - Pharma.D",
        "Doctor of Pharmacy - Ph.D",
        "Doctorate of Medicine - D.M",
    ]),
    ("Professinal", ["CA"]),
    ("Not in the List", ["NA"]),
]
EDUCATION_VALUES = [option for _, options in EDUCATION_OPTIONS for option in options]
OCCUPATION_OPTIONS = [
    "Agriculture",
    "business",
    "Consultancy",
    "Contractor",
    "Doctor",
    "House Maker",
    "House Wife",
    "House Work",
    "Industrlist",
    "Manufacturer",
    "NGO",
    "Not given",
    "Politics",
    "Professional",
    "Rental Income",
    "Retired",
    "Self Employeed",
    "Service",
    "Service - Abroad",
    "Service - Central Govt",
    "Service - Govt",
    "Service - MNC",
    "Service - PSU",
    "Service - Private",
    "Service - State Govt",
    "Service Provider",
    "Small Scale Industries",
    "Social Service",
    "Startup Owner",
    "Student",
    "Unemployeed",
]
MAIN_SHEET_COLUMNS = [
    "serial_no",
    "family_number",
    "salutation",
    "last_name",
    "first_name",
    "middle_name",
    "relation",
    "dob",
    "education",
    "occupation",
    "gender",
    "marital_status",
    "father_name",
    "father_native",
    "father_current_city",
    "email",
    "address",
    "building",
    "road",
    "locality",
    "pincode",
    "phone",
    "cellphone",
    "blood_group",
    "native",
    "gotra",
    "kuldevi",
]


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
    income = db.Column(db.String(50), nullable=True)
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
    edu = db.Column(db.String(150), nullable=False)
    occu = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=True)
    blood = db.Column(db.SmallInteger, db.ForeignKey('blood.id'), nullable=False)
    family = db.relationship('Family', backref=db.backref('members', lazy=True))
    blood_rel = db.relationship('Blood')
    relation_rel = db.relationship('Relation')
    marriage_rel = db.relationship('Marriage')


@app.route("/admin/dashboard")
def dashboard():
    if 'user' in session and session['user'] == admin_user:
        total_families = Family.query.count()
        total_members = Member.query.count()

        families = Family.query.all()
        last_names = [f.name.split()[0] for f in families if f.name]
        clusters = cluster_last_names(last_names, threshold=80)
        counter = {key: len(vals) for key, vals in clusters.items()}
        lst_names = list(counter.keys())
        lst_count = list(counter.values())

        today = datetime.today()
        end_date = today + timedelta(days=7)

        upcoming_birthdays = Member.query.filter(
            and_(
                and_(extract('month', Member.dob) == today.month,
                     extract('day', Member.dob) >= today.day),
                and_(extract('month', Member.dob) == end_date.month,
                     extract('day', Member.dob) <= end_date.day)
            )
        ).order_by(extract('month', Member.dob), extract('day', Member.dob)).all()
        for member in upcoming_birthdays:
            member.day = datetime.strptime(member.dob, '%Y-%m-%d').strftime('%d %b')
            member.age = today.year - datetime.strptime(member.dob, '%Y-%m-%d').year

        recent_fam = Family.query.order_by(Family.date.desc()).limit(3).all()

        return render_template('dashboard.html', fam_count=total_families, mem_count=total_members,
                               upcoming_birthdays=upcoming_birthdays, recent_fam=recent_fam, lst_names=lst_names,
                               lst_count=lst_count)
    else:
        return redirect("/admin")


@app.route("/admin/report")
def report():
    if 'user' in session and session['user'] == admin_user:
        families = Family.query.all()
        today = datetime.today()
        if families:
            for f in families:
                avg_fam_size = [f.mem_num]
            avg_membs_per_fam = sum(avg_fam_size) / len(avg_fam_size)
            largest_fam = max(families, key=lambda x: x.mem_num)
        members = Member.query.all()
        if members:
            age = [today.year - datetime.strptime(m.dob, '%Y-%m-%d').year for m in members if m.dob]
            median_age = sum(age) / len(age)

        families = Family.query.all()
        last_names = [f.name.split()[0] for f in families if f.name]
        clusters = cluster_last_names(last_names, threshold=80)
        counter = {key: len(vals) for key, vals in clusters.items()}
        common_count = max(counter.values())
        name = [key for key, value in counter.items() if value == common_count]
        common_name = str(name[0]).upper()
        total_add_fam = Family.query.filter(extract('year', Family.date) == today.year)
        total_add_fam = total_add_fam.count()

        data_village_count = db.session.query(
            Village.name, db.func.count(Family.id)
        ).join(Family, Family.village == Village.id).group_by(Village.name).all()
        village_name = [row[0] for row in data_village_count]
        village_count = [row[1] for row in data_village_count]

        data_kuldevi_count = db.session.query(
            Kuldevi.name, db.func.count(Family.id)
        ).join(family_kuldevi, Kuldevi.id == family_kuldevi.c.kuldevi_id) \
            .join(Family, Family.id == family_kuldevi.c.family_id) \
            .group_by(Kuldevi.name).all()
        kuldevi_name = [row[0] for row in data_kuldevi_count]
        kuldevi_count = [row[1] for row in data_kuldevi_count]

        data_blood_count = db.session.query(
            Blood.name, db.func.count(Member.id)
        ).join(Member, Member.blood == Blood.id).group_by(Blood.name).all()
        blood_name = [row[0] for row in data_blood_count]
        blood_count = [row[1] for row in data_blood_count]

        members = Member.query.with_entities(Member.dob, Member.gender).all()
        df = pd.DataFrame(members, columns=['dob', 'gender'])
        df['dob'] = pd.to_datetime(df['dob'])
        df['age'] = df['dob'].apply(lambda d: today.year - d.year - ((today.month, today.day) < (d.month, d.day)))
        bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 100]
        labels = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
        df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels, right=False)
        age_gender = df.groupby(['age_group', 'gender']).size().unstack(fill_value=0)
        age_groups = age_gender.index.tolist()
        male_counts = age_gender['M'].tolist()
        female_counts = (-age_gender['F']).tolist()

        male_bar = go.Bar(y=age_groups, x=male_counts, name='Male', orientation='h')
        female_bar = go.Bar(y=age_groups, x=female_counts, name='Female', orientation='h')

        layout = go.Layout(
            title="Population Pyramid",
            barmode='overlay',
            bargap=0.1,
            xaxis=dict(title="Population"),
            yaxis=dict(title="Age Group")
        )

        fig = go.Figure(data=[male_bar, female_bar], layout=layout)
        pyramid_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        members = Member.query.with_entities(Member.dob, Member.gender, Member.marriage).all()
        df = pd.DataFrame(members, columns=['dob', 'gender', 'marriage_rel'])
        df['dob'] = pd.to_datetime(df['dob'])
        df['age'] = df['dob'].apply(lambda d: today.year - d.year - ((today.month, today.day) < (d.month, d.day)))
        bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 100]
        labels = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
        df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels, right=False)
        marriage_map = {1: "Married", 2: "Unmarried", 3: "Widowed", 4: "Divorced"}
        df['marriage'] = df['marriage_rel'].map(marriage_map)
        grouped = df.groupby(['age_group', 'gender', 'marriage']).size().reset_index(name='count')

        traces = []
        for gender in grouped['gender'].unique():
            for status in grouped['marriage'].unique():
                subset = grouped[(grouped['gender'] == gender) & (grouped['marriage'] == status)]
                traces.append(go.Bar(
                    x=subset['age_group'],
                    y=subset['count'],
                    name=f"{gender} - {status}"
                ))

        layout = go.Layout(
            title="Marriage Distribution by Age & Gender",
            barmode='stack',
            xaxis=dict(title="Age Group"),
            yaxis=dict(title="Count")
        )

        fig = go.Figure(data=traces, layout=layout)
        marriage_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return render_template('report.html', avg_family_size=avg_membs_per_fam, largest_family=largest_fam,
                               median_age=median_age, common_name=common_name, common_count=common_count,
                               new_families_year=total_add_fam, village_name=village_name, village_count=village_count,
                               blood_count=blood_count, blood_name=blood_name, kuldevi_count=kuldevi_count,
                               kuldevi_name=kuldevi_name, pyramid_json=pyramid_json, marriage_json=marriage_json)
    else:
        return redirect("/admin")


@app.route("/admin/something")
def something():
    if 'user' in session and session['user'] == admin_user:
        return render_template('something.html')
    else:
        return redirect("/admin")


@app.route("/admin/user")
def users():
    if 'user' in session and session['user'] == admin_user:
        search = request.args.get('search', '')
        view = request.args.get("view", "quick")
        return render_template(
            'users.html',
            **build_users_context(view=view, search=search),
            import_result=None,
            default_ghatak='pune',
            default_pradeshik='mumbai',
        )
    else:
        return redirect("/admin")


@app.route("/admin/import", methods=['POST'])
def admin_import():
    if 'user' not in session or session['user'] != admin_user:
        return redirect("/admin")

    upload = request.files.get('excel_file')
    view = request.form.get('view', 'families')
    mode = request.form.get('mode', 'validate')
    default_ghatak = normalize_text(request.form.get('default_ghatak', 'pune')) or 'pune'
    default_pradeshik = normalize_text(request.form.get('default_pradeshik', 'mumbai')) or 'mumbai'

    if not upload or not upload.filename:
        flash('Select an Excel file before importing.')
        return render_template(
            'users.html',
            **build_users_context(view=view),
            import_result=None,
            default_ghatak=default_ghatak,
            default_pradeshik=default_pradeshik,
        )

    suffix = os.path.splitext(upload.filename)[1].lower()
    temp_fd, temp_path = tempfile.mkstemp(prefix='upload_', suffix=suffix, dir=os.path.join(base_dir, 'data'))
    os.close(temp_fd)
    upload.save(temp_path)

    try:
        import_result = import_excel_data(temp_path, mode, default_ghatak, default_pradeshik)
        if mode == 'import':
            flash(
                f"Import finished. Families imported: {import_result['families_created']}, "
                f"members imported: {import_result['members_created']}."
            )
        else:
            flash('Validation finished. Review the report below before importing.')
    except Exception as exc:
        db.session.rollback()
        flash(f'Import failed: {exc}')
        import_result = {
            'mode': mode,
            'rows_processed': 0,
            'families_detected': 0,
            'families_created': 0,
            'families_skipped': 0,
            'members_created': 0,
            'members_skipped': 0,
            'warning_count': 0,
            'error_count': 1,
            'issues': [{'level': 'error', 'family_key': '-', 'excel_row': '-', 'field': 'file', 'message': str(exc)}],
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return render_template(
        'users.html',
        **build_users_context(view=view),
        import_result=import_result,
        default_ghatak=default_ghatak,
        default_pradeshik=default_pradeshik,
    )


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
            # 1. Collect form data
            # Ensure these names match the 'name' attribute in your form1.html
            first = request.form.get('first_name', '')
            middle = request.form.get('middle_name', '')
            last = request.form.get('last_name', '')

            # This prevents the 'NoneType' has no attribute 'lower' error
            name = f"{last.lower()} {first.lower()} {middle.lower()}"

            email = request.form.get('email')
            ghatak = request.form.get('ghatak', '').lower()
            pradeshik = request.form.get('pradeshik', '').lower()

            # 2. Handle the Kuldevi Relationship
            k_id = request.form.get('kuldevi')
            # Fetch the actual Kuldevi object from the database
            kuldevi_obj = Kuldevi.query.get(int(k_id)) if k_id else None

            kuldevi_village = request.form.get('kuldevi_village')
            native_village = request.form.get('native_village')
            gotra = request.form.get('gotra')

            # 3. Process Addresses
            address1 = f"{request.form.get('building')} | {request.form.get('area')} | {request.form.get('street')} | {request.form.get('landmark')} | {request.form.get('pincode')}"
            address2 = f"{request.form.get('office_building')} | {request.form.get('office_area')} | {request.form.get('office_street')} | {request.form.get('office_landmark')} | {request.form.get('office_pincode')}"

            phone1 = int(request.form.get('res_phone'))
            phone2_raw = request.form.get('office_phone')
            phone2 = int(phone2_raw) if phone2_raw and phone2_raw.isdigit() else None
            income = request.form.get('income')
            num_of_memb = int(request.form.get('family_members'))
            date = datetime.now()

            # 4. Create Entry
            entry = Family(
                name=name,
                email=email,
                ghatak=ghatak,
                pradeshik=pradeshik,
                date=date,
                # Wrap the object in a list [ ] to satisfy the relationship
                kuldevi=[kuldevi_obj] if kuldevi_obj else [],
                k_village=kuldevi_village,
                village=native_village,
                gotra=gotra,
                res_add=address1,
                res_phone=phone1,
                off_add=address2,
                off_phone=phone2,
                income=income,
                mem_num=num_of_memb
            )

            db.session.add(entry)
            db.session.commit()

            return redirect(f'/form2/{num_of_memb}?family_id={entry.id}')

        except Exception as e:
            print("Error during form processing:", e)
            flash(f"Error: {str(e)}")
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
            return render_template('form2.html', mem=mem, family_id=family_id,
                                   education_options=EDUCATION_OPTIONS,
                                   occupation_options=OCCUPATION_OPTIONS)
    return render_template('form2.html', mem=mem, family_id=family_id,
                           education_options=EDUCATION_OPTIONS,
                           occupation_options=OCCUPATION_OPTIONS)


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


def normalize_text(value):
    if value is None:
        return ''
    value = str(value).strip().lower()
    value = re.sub(r'\s+', ' ', value)
    return value


def normalize_key(value):
    value = normalize_text(value)
    value = value.replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '', value)
    return value


def first_non_empty(*values):
    for value in values:
        text = str(value).strip() if value is not None else ''
        if text:
            return text
    return ''


def digits_only(value):
    return re.sub(r'\D+', '', str(value or ''))


def title_case_name(value):
    parts = [part for part in re.split(r'\s+', str(value or '').strip()) if part]
    return ' '.join(part.capitalize() for part in parts)


def build_person_name(last_name, first_name, middle_name):
    parts = [normalize_text(last_name), normalize_text(first_name), normalize_text(middle_name)]
    return ' '.join(part for part in parts if part)


def combine_address_parts(*parts):
    values = [str(part).strip() for part in parts if str(part or '').strip()]
    return ' | '.join(values) if values else 'Imported address not provided'


def parse_date_value(value):
    text = str(value or '').strip()
    if not text:
        return None

    text = re.sub(r'(?i)^age[-:\s/]*', '', text).strip()
    text = re.sub(r'(?i)^umar[-:\s/]*', '', text).strip()
    text = text.replace('.', '-').replace('/', '-')
    for fmt in ("%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d", "%d-%m-%Y %H:%M:%S", "%m-%d-%Y", "%m-%d-%y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def get_dataframe_from_excel(file_path, sheet_index=0):
    suffix = os.path.splitext(file_path)[1].lower()
    if suffix in {'.xlsx', '.xlsm'}:
        return pd.read_excel(file_path, sheet_name=sheet_index, header=None, dtype=str)

    if suffix == '.xls':
        try:
            return pd.read_excel(file_path, sheet_name=sheet_index, header=None, dtype=str, engine='xlrd')
        except ImportError:
            return read_xls_with_excel_com(file_path, sheet_index)

    raise ValueError("Unsupported file type. Please upload an .xls, .xlsx, or .xlsm file.")


def read_xls_with_excel_com(file_path, sheet_index=0):
    csv_fd, csv_path = tempfile.mkstemp(prefix='import_', suffix='.csv', dir=os.path.join(base_dir, 'data'))
    os.close(csv_fd)

    powershell_path = os.environ.get('SystemRoot', r'C:\Windows') + r'\System32\WindowsPowerShell\v1.0\powershell.exe'
    source = os.path.abspath(file_path).replace("'", "''")
    target = csv_path.replace("'", "''")
    sheet_number = int(sheet_index) + 1
    script = f"""
$source = '{source}'
$target = '{target}'
$excel = $null
$workbook = $null
$sheet = $null
try {{
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false
  $excel.DisplayAlerts = $false
  $workbook = $excel.Workbooks.Open($source)
  $sheet = $workbook.Worksheets.Item({sheet_number})
  $sheet.SaveAs($target, 62)
  $workbook.Close($false)
}} finally {{
  if ($excel) {{ $excel.Quit() }}
  if ($sheet) {{ [System.Runtime.Interopservices.Marshal]::ReleaseComObject($sheet) | Out-Null }}
  if ($workbook) {{ [System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null }}
  if ($excel) {{ [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null }}
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}}
"""
    try:
        subprocess.run(
            [powershell_path, '-NoProfile', '-Command', script],
            check=True,
            capture_output=True,
            text=True,
        )
        return pd.read_csv(csv_path, header=None, dtype=str, keep_default_na=False)
    except FileNotFoundError as exc:
        raise ValueError("PowerShell is not available for .xls import on this machine.") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("Unable to read the .xls file. Install xlrd or Microsoft Excel for .xls support.") from exc
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)


def dataframe_to_records(df):
    trimmed = df.iloc[:, :len(MAIN_SHEET_COLUMNS)].copy()
    trimmed.columns = MAIN_SHEET_COLUMNS[:trimmed.shape[1]]
    trimmed = trimmed.fillna('')
    records = []
    for row_index, row in trimmed.iloc[1:].iterrows():
        record = {column: str(row.get(column, '') or '').strip() for column in MAIN_SHEET_COLUMNS[:trimmed.shape[1]]}
        if not any(record.values()):
            continue
        record['excel_row'] = int(row_index) + 1
        records.append(record)
    return records


def load_surname_defaults(file_path):
    try:
        df = get_dataframe_from_excel(file_path, sheet_index=1).fillna('')
    except Exception:
        return {}

    defaults = {}
    for _, row in df.iloc[1:].iterrows():
        surname = str(row.iloc[0]).strip() if len(row) > 0 else ''
        if not surname:
            continue
        defaults[normalize_key(surname)] = {
            'gender': str(row.iloc[1]).strip() if len(row) > 1 else '',
            'blood_group': str(row.iloc[2]).strip() if len(row) > 2 else '',
            'native': str(row.iloc[3]).strip() if len(row) > 3 else '',
            'gotra': str(row.iloc[4]).strip() if len(row) > 4 else '',
            'kuldevi': str(row.iloc[5]).strip() if len(row) > 5 else '',
        }
    return defaults


def build_lookup_map(items, extra_aliases=None):
    lookup = {}
    for item in items:
        lookup[normalize_key(item.name)] = item
    for alias, item in (extra_aliases or {}).items():
        lookup[normalize_key(alias)] = item
    return lookup


def build_reference_maps():
    village_aliases = {}
    villages = Village.query.all()
    village_lookup = build_lookup_map(villages)
    for alias, target in {
        'sinugra': 'Sinogara',
        'sinogra': 'Sinogara',
        'galpadhar': 'Galpadar',
        'khambhara': 'Khambhra',
        'chandiya': 'Chandia',
        'kumbhariya': 'Kumbharia',
    }.items():
        match = next((item for item in villages if item.name == target), None)
        if match:
            village_aliases[alias] = match
    village_lookup.update(build_lookup_map([], village_aliases))

    gotras = Gotra.query.all()
    gotra_lookup = build_lookup_map(gotras)
    for alias, target in {
        'sha.bha.vishwamitra': 'VISHVAMITRA',
        'shabha vishwamitra': 'VISHVAMITRA',
        'vasistha': 'VASHISHTHA',
        'sonak': 'SHAUNAK',
    }.items():
        match = next((item for item in gotras if item.name == target), None)
        if match:
            gotra_lookup[normalize_key(alias)] = match

    kuldevis = Kuldevi.query.all()
    kuldevi_lookup = build_lookup_map(kuldevis)
    for alias, target in {
        'bahuchara mata': 'Bahuchari-Bramhani Maa',
        'bahuchara maa': 'Bahuchari-Bramhani Maa',
        'boot bhavani maa': 'But-Bhavani Maa',
        'boot bhavani mata': 'But-Bhavani Maa',
        'boot/sikotra': 'Sikotar Maa',
        'chaval dev': 'Chawal Maa',
        'bramhani': 'Bramhani Maa',
        'bramhani maa': 'Bramhani Maa',
        'bramhnai': 'Bramhani Maa',
    }.items():
        match = next((item for item in kuldevis if item.name == target), None)
        if match:
            kuldevi_lookup[normalize_key(alias)] = match

    blood_lookup = build_lookup_map(Blood.query.all())
    for alias, target in {'unknown': 'Unknown', 'na': 'Unknown', 'n/a': 'Unknown'}.items():
        match = Blood.query.filter_by(name=target).first()
        if match:
            blood_lookup[normalize_key(alias)] = match

    return {
        'village': village_lookup,
        'gotra': gotra_lookup,
        'kuldevi': kuldevi_lookup,
        'blood': blood_lookup,
        'unknown_blood': ensure_unknown_blood(),
    }


def ensure_unknown_blood():
    unknown = Blood.query.filter_by(name='Unknown').first()
    if unknown:
        return unknown
    next_id = max(9, (db.session.query(db.func.max(Blood.id)).scalar() or 0) + 1)
    unknown = Blood(id=next_id, name='Unknown')
    db.session.add(unknown)
    db.session.flush()
    return unknown


def map_relation_value(raw_value):
    normalized = normalize_key(raw_value)
    relation_aliases = {
        'self': 1,
        'father': 2,
        'mother': 3,
        'wife': 4,
        'husband': 5,
        'son': 6,
        'daughter': 7,
        'brother': 8,
        'sister': 9,
        'grandfather': 10,
        'grandmother': 11,
        'grandson': 12,
        'granddaughter': 13,
        'fatherinlaw': 14,
        'motherinlaw': 15,
        'daughterinlaw': 16,
        'soninlaw': 17,
        'sonswife': 16,
        'daughtershusband': 17,
        'grand daughter': 13,
        'grand son': 12,
    }
    return relation_aliases.get(normalized, 18 if normalized else None)


def map_marriage_value(raw_value):
    normalized = normalize_key(raw_value)
    aliases = {
        'married': 1,
        'unmarried': 2,
        'widowed': 4,
        'divorced': 3,
    }
    return aliases.get(normalized)


def infer_gender(raw_gender, salutation, relation_id):
    normalized = normalize_key(raw_gender)
    if normalized in {'male', 'm', 'purush'}:
        return 'M'
    if normalized in {'female', 'f', 'stri'}:
        return 'F'

    salutation_key = normalize_key(salutation)
    if salutation_key in {'shri', 'kumar'}:
        return 'M'
    if salutation_key in {'shrimati', 'shirmati', 'kumari'}:
        return 'F'

    if relation_id in {2, 5, 6, 8, 10, 12, 17}:
        return 'M'
    if relation_id in {3, 4, 7, 9, 11, 13, 15, 16}:
        return 'F'
    return None


def normalize_education_value(raw_value):
    text = str(raw_value or '').strip()
    if not text:
        return 'NA', True
    return text, text not in EDUCATION_VALUES


def normalize_occupation_value(raw_value):
    text = str(raw_value or '').strip()
    aliases = {
        'retired': 'Retired',
        'service': 'Service',
        'job': 'Service',
        'business': 'business',
        'housewife': 'House Wife',
        'house work': 'House Work',
        'housemaker': 'House Maker',
        'studying': 'Student',
        'student': 'Student',
        'professional': 'Professional',
        'doctor': 'Doctor',
        'ngo': 'NGO',
    }
    normalized = normalize_key(text)
    if normalized in {normalize_key(option) for option in OCCUPATION_OPTIONS}:
        for option in OCCUPATION_OPTIONS:
            if normalize_key(option) == normalized:
                return option, False
    if normalized in aliases:
        return aliases[normalized], False
    if not text:
        return 'Not given', True
    return text, True


def add_issue(result, level, family_key, excel_row, field, message):
    issue = {
        'level': level,
        'family_key': family_key,
        'excel_row': excel_row,
        'field': field,
        'message': message,
    }
    result['issues'].append(issue)
    if level == 'error':
        result['error_count'] += 1
    else:
        result['warning_count'] += 1


def member_sort_key(member):
    return (
        0 if member.relation == 1 else 1,
        member.relation_rel.name if member.relation_rel else '',
        member.name or '',
    )


def build_family_cards(families, search=''):
    search_text = normalize_text(search)
    cards = []

    for family in families:
        sorted_members = sorted(list(family.members), key=member_sort_key)
        head_member = next((member for member in sorted_members if member.relation == 1), None)
        if not head_member and sorted_members:
            head_member = sorted_members[0]

        searchable_values = [
            family.name,
            family.email,
            family.ghatak,
            family.pradeshik,
            family.res_add,
            family.res_phone,
            family.off_add,
            family.off_phone,
            family.village_rel.name if family.village_rel else '',
            family.k_village_rel.name if family.k_village_rel else '',
            family.gotra_rel.name if family.gotra_rel else '',
            ' '.join(k.name for k in family.kuldevi),
            *(member.name for member in sorted_members),
            *(member.phone for member in sorted_members),
            *(member.edu for member in sorted_members),
            *(member.occu for member in sorted_members),
        ]
        haystack = normalize_text(' '.join(str(value or '') for value in searchable_values))
        if search_text and search_text not in haystack:
            continue

        cards.append({
            'family': family,
            'head_member': head_member,
            'members': sorted_members,
            'other_members': [member for member in sorted_members if not head_member or member.id != head_member.id],
        })

    return sorted(cards, key=lambda card: (card['family'].name or '', card['family'].id))


def build_users_context(view, search=''):
    families = Family.query.order_by(Family.name.asc()).all()
    family_cards = build_family_cards(families, search=search)

    members = []
    if view in {"joined", "members"}:
        members = [member for card in family_cards for member in card['members']]

    return {
        'view': view,
        'search': search,
        'families': [card['family'] for card in family_cards],
        'members': members,
        'family_cards': family_cards,
    }


def group_records_by_family(records):
    groups = {}
    for record in records:
        family_key = first_non_empty(record.get('serial_no'), record.get('family_number'))
        if not family_key:
            continue
        groups.setdefault(family_key, []).append(record)
    return groups


def resolve_lookup(lookup, raw_value):
    if not raw_value:
        return None
    return lookup.get(normalize_key(raw_value))


def import_excel_data(file_path, mode, default_ghatak, default_pradeshik):
    df = get_dataframe_from_excel(file_path, sheet_index=0)
    records = dataframe_to_records(df)
    surname_defaults = load_surname_defaults(file_path)
    reference_maps = build_reference_maps()
    grouped_records = group_records_by_family(records)
    existing_signatures = {(family.name, str(family.res_phone), family.village) for family in Family.query.all()}

    result = {
        'mode': mode,
        'rows_processed': len(records),
        'families_detected': len(grouped_records),
        'families_created': 0,
        'families_skipped': 0,
        'members_created': 0,
        'members_skipped': 0,
        'warning_count': 0,
        'error_count': 0,
        'issues': [],
    }

    for family_key, family_rows in grouped_records.items():
        head_row = next((row for row in family_rows if normalize_key(row.get('relation')) == 'self'), family_rows[0])
        surname_key = normalize_key(head_row.get('last_name'))
        defaults = surname_defaults.get(surname_key, {})

        family_name = build_person_name(head_row.get('last_name'), head_row.get('first_name'), head_row.get('middle_name'))
        if not family_name:
            add_issue(result, 'error', family_key, head_row['excel_row'], 'name', 'Family head name is missing.')
            result['families_skipped'] += 1
            result['members_skipped'] += len(family_rows)
            continue

        village_text = first_non_empty(head_row.get('native'), defaults.get('native'))
        village = resolve_lookup(reference_maps['village'], village_text)
        if not village:
            add_issue(result, 'error', family_key, head_row['excel_row'], 'native', f"Native village '{village_text or 'blank'}' could not be mapped.")
            result['families_skipped'] += 1
            result['members_skipped'] += len(family_rows)
            continue

        gotra_text = first_non_empty(head_row.get('gotra'), defaults.get('gotra'))
        gotra = resolve_lookup(reference_maps['gotra'], gotra_text) or Gotra.query.filter_by(name='OTHER').first()
        if not gotra_text:
            add_issue(result, 'warning', family_key, head_row['excel_row'], 'gotra', "Gotra missing. Imported as 'OTHER'.")
        elif not resolve_lookup(reference_maps['gotra'], gotra_text):
            add_issue(result, 'warning', family_key, head_row['excel_row'], 'gotra', f"Gotra '{gotra_text}' not found. Imported as 'OTHER'.")

        kuldevi_text = first_non_empty(head_row.get('kuldevi'), defaults.get('kuldevi'))
        kuldevi = resolve_lookup(reference_maps['kuldevi'], kuldevi_text)
        if kuldevi_text and not kuldevi:
            add_issue(result, 'warning', family_key, head_row['excel_row'], 'kuldevi', f"Kuldevi '{kuldevi_text}' could not be mapped and was left blank.")

        family_phone = ''
        for row in family_rows:
            family_phone = first_non_empty(digits_only(row.get('cellphone')), digits_only(row.get('phone')), family_phone)
            if family_phone:
                break
        if not family_phone:
            add_issue(result, 'error', family_key, head_row['excel_row'], 'phone', 'No usable phone number was found for this family.')
            result['families_skipped'] += 1
            result['members_skipped'] += len(family_rows)
            continue

        family_email = next((row.get('email') for row in family_rows if row.get('email')), '')
        family_address = combine_address_parts(
            head_row.get('address'),
            head_row.get('building'),
            head_row.get('road'),
            head_row.get('locality'),
            head_row.get('pincode'),
        )

        valid_members = []
        family_errors_before = result['error_count']
        for row in family_rows:
            member_name = build_person_name(row.get('last_name'), row.get('first_name'), row.get('middle_name'))
            if not member_name:
                continue

            relation_id = map_relation_value(row.get('relation'))
            if not relation_id:
                relation_id = 18
                add_issue(result, 'warning', family_key, row['excel_row'], 'relation', f"Relation '{row.get('relation')}' not recognized. Imported as 'Other'.")

            gender = infer_gender(row.get('gender'), row.get('salutation'), relation_id)
            if not gender:
                add_issue(result, 'error', family_key, row['excel_row'], 'gender', 'Gender is missing and could not be inferred.')
                result['members_skipped'] += 1
                continue

            dob = parse_date_value(row.get('dob'))
            if not dob:
                add_issue(result, 'error', family_key, row['excel_row'], 'dob', f"DOB '{row.get('dob') or 'blank'}' is missing or invalid.")
                result['members_skipped'] += 1
                continue

            marriage_id = map_marriage_value(row.get('marital_status'))
            if not marriage_id:
                marriage_id = 2
                add_issue(result, 'warning', family_key, row['excel_row'], 'marital_status', "Marital status missing or invalid. Imported as 'Unmarried'.")

            member_phone = first_non_empty(digits_only(row.get('cellphone')), digits_only(row.get('phone')), family_phone)
            if not member_phone:
                member_phone = family_phone
                add_issue(result, 'warning', family_key, row['excel_row'], 'phone', 'Member phone missing. Used family phone.')

            blood_text = first_non_empty(row.get('blood_group'), defaults.get('blood_group'))
            blood = resolve_lookup(reference_maps['blood'], blood_text) or reference_maps['unknown_blood']
            if not blood_text:
                add_issue(result, 'warning', family_key, row['excel_row'], 'blood_group', "Blood group missing. Imported as 'Unknown'.")
            elif blood == reference_maps['unknown_blood']:
                add_issue(result, 'warning', family_key, row['excel_row'], 'blood_group', f"Blood group '{blood_text}' not mapped. Imported as 'Unknown'.")

            education, education_warning = normalize_education_value(row.get('education'))
            if education_warning:
                add_issue(result, 'warning', family_key, row['excel_row'], 'education', f"Education '{row.get('education') or 'blank'}' is outside the current dropdown list.")

            occupation, occupation_warning = normalize_occupation_value(row.get('occupation'))
            if occupation_warning:
                add_issue(result, 'warning', family_key, row['excel_row'], 'occupation', f"Occupation '{row.get('occupation') or 'blank'}' was normalized to '{occupation}'.")

            father_name = title_case_name(row.get('father_name')) or 'Unknown'
            if father_name == 'Unknown':
                add_issue(result, 'warning', family_key, row['excel_row'], 'father_name', "Father name missing. Imported as 'Unknown'.")

            valid_members.append({
                'name': member_name,
                'father': father_name,
                'gender': gender,
                'relation': relation_id,
                'peear': row.get('father_native') or None,
                'marriage': marriage_id,
                'dob': dob,
                'photo': None,
                'edu': education,
                'occu': occupation,
                'phone': member_phone,
                'email': row.get('email') or None,
                'blood': blood.id,
            })

        if not valid_members or result['error_count'] > family_errors_before and not valid_members:
            add_issue(result, 'error', family_key, head_row['excel_row'], 'members', 'No valid members remained after validation.')
            result['families_skipped'] += 1
            continue

        signature = (family_name, str(family_phone), village.id)
        if signature in existing_signatures:
            add_issue(result, 'warning', family_key, head_row['excel_row'], 'duplicate', 'Matching family already exists. This family was skipped.')
            result['families_skipped'] += 1
            result['members_skipped'] += len(valid_members)
            continue

        if mode == 'import':
            family = Family(
                name=family_name,
                email=family_email or 'imported@example.com',
                ghatak=default_ghatak,
                pradeshik=default_pradeshik,
                date=datetime.now(),
                kuldevi=[kuldevi] if kuldevi else [],
                k_village=village.id,
                village=village.id,
                gotra=gotra.id,
                res_add=family_address,
                res_phone=int(family_phone[:10]) if family_phone else 0,
                off_add='',
                off_phone=None,
                income='',
                mem_num=len(valid_members),
            )
            db.session.add(family)
            db.session.flush()

            for member_data in valid_members:
                db.session.add(Member(family_id=family.id, **member_data))

            existing_signatures.add(signature)

        result['families_created'] += 1
        result['members_created'] += len(valid_members)

    if mode == 'import':
        db.session.commit()
    else:
        db.session.rollback()

    result['issues'] = result['issues'][:200]
    return result


def cluster_last_names(names, threshold):
    clusters = {}
    for name in names:
        matched = False
        for key in clusters.keys():
            if fuzz.ratio(name, key) >= threshold:
                clusters[key].append(name)
                matched = True
                break
        if not matched:
            clusters[name] = [name]
    return clusters


@app.route('/summary/<int:family_id>', methods=['GET', 'POST'])
def summary(family_id):
    family = Family.query.get_or_404(family_id)
    return render_template('summary.html', family=family)


@app.route("/edit/<string:type>/<string:id>", methods=['GET', 'POST'])
def editing_sec(id, type):
    if type == 'family':
        fam = Family.query.filter_by(id=id).first() if id != 'new' else None
        if request.method == 'POST':
            name = request.form.get('last_name').lower() + " " + request.form.get(
                'first_name').lower() + " " + request.form.get(
                'middle_name').lower()
            email = request.form.get('email')
            ghatak = request.form.get('ghatak').lower()
            pradeshik = request.form.get('pradeshik').lower()
            k_id = request.form.get('kuldevi')
            kuldevi_obj = Kuldevi.query.get(k_id)
            kuldevi = [kuldevi_obj]
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
            income = request.form.get('income')
            num_of_memb = int(request.form.get('family_members'))

            fam = Family.query.filter_by(id=id).first()
            if fam:
                fam.name = name
                fam.email = email
                fam.ghatak = ghatak
                fam.pradeshik = pradeshik
                k_id = request.form.get('kuldevi')
                if k_id:
                    fam.kuldevi = [Kuldevi.query.get(int(k_id))]
                fam.k_village = kuldevi_village
                fam.village = native_village
                fam.gotra = gotra
                fam.res_add = address1
                fam.res_phone = phone1
                fam.off_add = address2
                fam.off_phone = phone2
                fam.income = income
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
                    mem.edu = edu
                    mem.occu = occu
                    mem.phone = phone
                    mem.email = email
                    mem.blood = blood
                    family_id = mem.family_id

                    db.session.commit()
                    return redirect('/summary/' + str(family_id))
        return render_template('edit_m.html', id=id, mem=mem, type=type,
                               education_options=EDUCATION_OPTIONS,
                               education_values=EDUCATION_VALUES,
                               occupation_options=OCCUPATION_OPTIONS)


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


@app.route('/export/xsl')
def export_all():
    if 'user' in session and session['user'] == admin_user:
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')

        families = Family.query.all()
        df_families = pd.DataFrame([{
            'ID': f.id,
            'Name': f.name,
            'Email': f.email,
            'Gotra': f.gotra_rel.name if f.gotra_rel else '',
            'Village': f.village_rel.name if f.village_rel else '',
            'Kuldevi': f.Kuldevi.name if f.Kuldevi else '',
            'Members': f.mem_num,
            'Date': f.date
        } for f in families])
        df_families.to_excel(writer, index=False, sheet_name='Families')

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


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/')


def lookup_tables():
    if not Kuldevi.query.first():
        kuldevi_data = [
            (1, "Bahuchari-Bramhani Maa"),
            (2, "Bramhani-Chamunda Maa"),
            (3, "Bramhani-Chawal Maa"),
            (4, "Bramhani-Sikotar Maa"),
            (5, "Bramhani Maa"),
            (6, "Bramhani-Sihwahini Maa"),
            (7, "But-Bhavani Maa"),
            (8, "Chamunda Maa"),
            (9, "Chamunda-Chawal Maa"),
            (10, "Chawal Maa"),
            (11, "Chawal-But Maa"),
            (12, "Chawal-Bramhani Maa"),
            (13, "Kalika Maa"),
            (14, "Khodiar Maa"),
            (15, "Momai-Chamunda Maa"),
            (16, "Momai Maa"),
            (17, "Peethal Maa"),
            (18, "Sikotar-Bramhani Maa"),
            (19, "Sikotar Maa"),
            (20, "Truthiani Maa"),
            (21, "Truthiyani Maa"),
            (22, "Truthiyan-Chamunda-Harsiddhi Maa"),
            (23, "Truthiyan-Chamunda Maa"),
            (24, "Truthiyan-Harsiddhi Maa"),
            (25, "Vachra Dada"),
            (26, "Vishal Maa"),
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


def initialize_database():
    with app.app_context():
        db.create_all()
        lookup_tables()


initialize_database()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
