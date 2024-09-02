import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

DATABASE = 'pharmacy.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    db = get_db()
    cur = db.execute('SELECT * FROM medicines LIMIT 4')
    medicines = cur.fetchall()
    cur = db.execute('SELECT * FROM testimonials')
    testimonials = cur.fetchall()
    return render_template('home.html', medicines=medicines, testimonials=testimonials)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/buy')
def buy():
    db = get_db()
    cur = db.execute('SELECT * FROM medicines')
    medicines = cur.fetchall()
    return render_template('buy.html', medicines=medicines)

@app.route('/add_to_cart/<int:medicine_id>')
def add_to_cart(medicine_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(medicine_id)
    session.modified = True
    return redirect(url_for('buy'))

@app.route('/cart')
def cart():
    if 'cart' not in session:
        session['cart'] = []
    
    db = get_db()
    cart_items = []
    total = 0
    for medicine_id in session['cart']:
        cur = db.execute('SELECT * FROM medicines WHERE id = ?', [medicine_id])
        medicine = cur.fetchone()
        if medicine:
            cart_items.append(medicine)
            total += medicine[3]  # Assuming price is at index 3
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        hashed_password = generate_password_hash('1234')
        
        username = request.form['username']
        password = request.form['password']
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', ['usernames', hashed_password])
        
        print("Password is : ", hashed_password)
        print(username)
        user = db.execute('SELECT * FROM users WHERE username = ?', [username]).fetchone()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect(url_for('admin'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    db = get_db()
    cur = db.execute('SELECT * FROM medicines')
    medicines = cur.fetchall()
    return render_template('admin.html', medicines=medicines)

@app.route('/admin/add_medicine', methods=['POST'])
@login_required
def add_medicine():
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    image_url = request.form['image_url']
    db = get_db()
    db.execute('INSERT INTO medicines (name, description, price, image_url) VALUES (?, ?, ?, ?)',
                [name, description, price, image_url])
    db.commit()
    flash('Medicine added successfully')
    return redirect(url_for('admin'))

@app.route('/admin/edit_medicine/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_medicine(id):
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image_url = request.form['image_url']
        db.execute('UPDATE medicines SET name = ?, description = ?, price = ?, image_url = ? WHERE id = ?',
                    [name, description, price, image_url, id])
        db.commit()
        flash('Medicine updated successfully')
        return redirect(url_for('admin'))
    cur = db.execute('SELECT * FROM medicines WHERE id = ?', [id])
    medicine = cur.fetchone()
    return render_template('edit_medicine.html', medicine=medicine)

@app.route('/admin/delete_medicine/<int:id>')
@login_required
def delete_medicine(id):
    db = get_db()
    db.execute('DELETE FROM medicines WHERE id = ?', [id])
    db.commit()
    flash('Medicine deleted successfully')
    return redirect(url_for('admin'))

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    name = request.form['name']
    email = request.form['email']
    date = request.form['date']
    time = request.form['time']
    db = get_db()
    db.execute('INSERT INTO appointments (name, email, date, time) VALUES (?, ?, ?, ?)',
                [name, email, date, time])
    db.commit()
    flash('Appointment booked successfully')
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)