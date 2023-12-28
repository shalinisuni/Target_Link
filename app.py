from flask import Flask, render_template, redirect,session,request,url_for,jsonify,flash
import hashlib
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from random import *
import re


import mysql.connector


app = Flask(__name__)



app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'shalini18031999@gmail.com'
app.config['MAIL_PASSWORD'] = 'glba witq lcvy bkom'
app.config['MAIL_DEFAULT_SENDER'] = 'shalini18031999@gmail.com'
#app.config['PERMANENT_SESSION_LIFETIME'] = 60
app.config['SECRET_KEY'] = 'demoapp'
mail=Mail(app)


db_config = {
    'host': 'localhost',
    'user': 'target',
    'password': 'root',
    'database': 'mydb'
}
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

def connect_to_db():
    return mysql.connector.connect(**db_config)

@app.route('/logout')
def logout():
    session.pop('email',None)
    return render_template('index.html')

@app.route('/cancel')
def cancel():
     session.pop('email',None)
     return render_template('index.html')

@app.route('/')
def home():
    return render_template("index.html")

@app.before_request
def before_request():
    session.permanent = True
    #app.permanent_session_lifetime = timedelta(minutes=5)
    session.modified = True 

@app.route('/login', methods=['POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        password = hashlib.md5(password.encode()).hexdigest()
        user_id = get_user_id(email, password)
        print(user_id)
        if user_id is not None:
            session['user_id'] = user_id
            return redirect(url_for('target_page'))
        else:
            flash("Invalid email or password",'error')
            return render_template('index.html')
    return render_template('index.html', msg='Invalid email or password')

    
# Function to get user ID based on email and password
def get_user_id(email, password):
    connection = connect_to_db()
    cursor = connection.cursor(dictionary=True)
    sql="SELECT user_id FROM users WHERE email = %s AND password = %s"
    cursor.execute(sql , (email, password))
    user = cursor.fetchone()
    print(user)
    connection.close()
    return user['user_id'] if user else None

# Function to fetch target data based on user ID and target name
def get_target_data(user_id, target_name):
    connection = connect_to_db()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT total_target_count, cumulative_target FROM targets WHERE user_id = %s AND target_name = %s', (user_id, target_name))
    target_data = cursor.fetchone()
    #print(target_data)
    connection.close()
    return target_data

@app.route('/register',methods=['Get','Post'])
def register():
     if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirmpass']
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s OR mobile = %s", (email, phone))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Email or phone number already exists. Please choose a different one.")
            return render_template("register.html")
        else:
            if not name.isalpha():
                return "Name should contain only alphabets."
            if not phone.isdigit() and re.match(r'^\d{10}$', phone) :
                return "Phone number should contain only 10 digits."
            if not re.match(r'^[a-zA-Z0-9]+@[a-zA-Z]+\.[a-zA-Z]+$', email) :
                return "email Id is not valid please check"
            if password != confirm_password:
                return render_template('register.html', error='Passwords do not match')
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            connection = connect_to_db()
            cursor = connection.cursor()
            cursor.execute('INSERT INTO users (user_name, mobile, email, password) VALUES (%s, %s, %s, %s)',(name, phone, email, hashed_password))
            connection.commit()
            cursor.close()
            flash("registered Sucessfully")
            return render_template("index.html")

     return render_template('register.html')

@app.route('/target', methods=['GET'])
def target_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user_id = session['user_id']

    # Fetch target names for the dropdown
    connection = connect_to_db()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT  target_name FROM targets WHERE user_id = %s",(user_id,))
    target_names = [row['target_name'] for row in cursor.fetchall()]
    print(target_names)
    cursor.execute("select user_name from users where user_id=%s",(user_id,))
    uname=[r['user_name'] for r in cursor.fetchall()]
   
    uname=str(uname).strip("[]").replace("'", "")
    
    return render_template('target.html', target_names=target_names,uname=uname)

# Ajax route to fetch target details
@app.route('/get_target_details', methods=['POST'])
def get_target_details():
    user_id = session.get('user_id')
    if user_id is None:
        return jsonify({'error': 'User not authenticated'})

    target_name = request.json['target_name']
    print(target_name)
    target_data = get_target_data(user_id, target_name)
    return jsonify(target_data)

@app.route('/history',methods=['Get'])
def history():
    if 'user_id' not in session:
        return redirect(url_for('index'))
     
    connection = connect_to_db()
    cursor=connection.cursor()
    cursor.execute("SELECT target_name, count, DATE_FORMAT(date,'%d-%m-%Y %H:%i') from transactions")
    res=cursor.fetchall()
    cursor.close()
    print(res)
    new_data=res 
    return render_template("history.html",new_data=new_data)
   

@app.route('/submit',methods=['GET','Post'])
def submit():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user_id = session['user_id']
    targetDropdown=request.form['targetDropdown']
    todayCount=int(request.form['todayCount'])
    print(todayCount,targetDropdown)
    target_data = get_target_data(user_id, targetDropdown)
    total_target=target_data['total_target_count']
    cumulative=target_data['cumulative_target']
    print(type(total_target))
    if total_target > todayCount:
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute('INSERT INTO transactions (target_name,count) VALUES (%s, %s)',(targetDropdown,todayCount))
        connection.commit()
        target_data = get_target_data(user_id, targetDropdown)
        cumulative=target_data['cumulative_target']
        cursor.execute(f"update targets set cumulative_target={cumulative} + {todayCount} where user_id= %s and target_name= %s",(user_id,targetDropdown))
        print(f"{todayCount} and {cumulative}")
        connection.commit()
        cursor.close()
        return render_template("target.html", msg=f"today count {todayCount} {targetDropdown} is added into the database suceessfully ")
    else:
        return redirect(url_for('target_page' , msg="today count is greater than total target count please enter the correct value"))

def send_reset_email(email, reset_url):
    subject = 'Password Reset Request'
    body = render_template('reset_email.html', reset_url=reset_url)

    message = Message(subject, recipients=[email], html=body)
    mail.send(message)

@app.route('/change_password',methods=['Get','Post'])
def change_password():
    if request.method == 'POST':    
        email=request.form['email']
        print(email)
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        print(user)
        if user:
            # Generate a unique token
            token = serializer.dumps(email, salt='change-password')
             # Send email with the reset link
            reset_url = url_for('reset_token', token=token, _external=True)
            send_reset_email(email, reset_url)
            
            flash('Link has been send to your mail to reset your password', 'info')
            return redirect(url_for('change_password'))
        else:
            flash('Email not found in the database.', 'danger')
    return render_template("change_password.html")

@app.route("/reset_token/",methods=['Get','Post'])
def reset():
    email = session.get('reset_email')
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        print(new_password,confirm_password)
        if new_password == confirm_password:
            new_password= hashlib.md5(new_password.encode()).hexdigest()
            #Update the password in the database
            connection = connect_to_db()
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
            connection.commit()
            cursor.close()

            flash('Your password has been successfully updated.')
            return render_template("index.html")
           
        else:
            flash('New password and confirm password do not match.', 'danger')
    
        return render_template("new_password.html")

@app.route('/reset_token/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if 'email' not in session:
        flash("Please login using email and password")
        return render_template("index.html")
    try:
        email = serializer.loads(token, salt='change-password', max_age=10800)  # Token valid for 3 hours
        session['reset_email'] = email
        print(request.method)
    except:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))
    return render_template('new_password.html', email=email)

if __name__=="__main__":
    app.run(debug=True)