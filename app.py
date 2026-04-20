<<<<<<< HEAD

from flask import Flask, render_template, request, redirect, session, url_for
import pyotp, time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------------
# Twilio CONFIG (PUT YOUR VALUES)
# -------------------------
ACCOUNT_SID = "ACf2e365f78c1c9a20f8996996457db260"
AUTH_TOKEN = "e0c6400f567fa92c5f331cec341995b9"
TWILIO_NUMBER = "+18392505733"
USER_PHONE = "+919373753984"   # your phone

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# -------------------------
# USER
# -------------------------
USERNAME = "admin"
PASSWORD = "password123"

# -------------------------
# RSA Keys
# -------------------------
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# -------------------------
# OTP
# -------------------------
totp_secret = pyotp.random_base32()
totp = pyotp.TOTP(totp_secret)

# -------------------------
# Login Required Decorator
# -------------------------
def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/')
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# -------------------------
# ROUTES
# -------------------------
@app.route('/')
def login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def do_login():
    user = request.form['username']
    pwd = request.form['password']

    if user == USERNAME and pwd == PASSWORD:

        otp = totp.now()

        signature = private_key.sign(
            otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Send SMS via Twilio
        client.messages.create(
            body=f"Your OTP is: {otp}",
            from_=TWILIO_NUMBER,
            to=USER_PHONE
        )

        session['otp'] = otp
        session['signature'] = signature.hex()
        session['time'] = time.time()

        return redirect('/otp')

    return "Invalid Credentials"


@app.route('/otp')
def otp_page():
    return render_template("otp.html")


@app.route('/verify', methods=['POST'])
def verify():
    user_otp = request.form['otp']

    stored_otp = session.get('otp')
    signature = bytes.fromhex(session.get('signature'))
    timestamp = session.get('time')

    if time.time() - timestamp > 120:
        return "OTP Expired"

    try:
        public_key.verify(
            signature,
            user_otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        if user_otp == stored_otp:
            session['logged_in'] = True
            return redirect('/dashboard')

    except Exception:
        return "Invalid OTP"

    return "Verification Failed"


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route('/home')
@login_required
def home():
    return render_template("home.html")


@app.route('/about')
@login_required
def about():
    return render_template("about.html")


@app.route('/projects')
@login_required
def projects():
    return render_template("projects.html")


@app.route('/contact')
@login_required
def contact():
    return render_template("contact.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)


'''
from flask import Flask, render_template, request, redirect, session
import pyotp, time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twilio.rest import Client
from flask import flash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------------
# Twilio CONFIG
# -------------------------
ACCOUNT_SID = "ACf2e365f78c1c9a20f8996996457db260"
AUTH_TOKEN = "ae8baadd4cffcb487e8b8f5577ba366d"
TWILIO_NUMBER = "+18392505733"
USER_PHONE = "+919373753984"   # your phone

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# -------------------------
# USER
# -------------------------
USERNAME = "admin"
PASSWORD = "password123"

# -------------------------
# RSA KEYS
# -------------------------
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# -------------------------
# OTP
# -------------------------
totp_secret = pyotp.random_base32()
totp = pyotp.TOTP(totp_secret)

# -------------------------
# SECURITY SETTINGS
# -------------------------
MAX_ATTEMPTS = 3
LOCK_TIME = 120

# -------------------------
# LOCK CHECK
# -------------------------
def is_locked():
    lock_until = session.get('lock_until')
    if lock_until and time.time() < lock_until:
        return True, int(lock_until - time.time())
    return False, 0

# -------------------------
# ROUTES
# -------------------------
@app.route('/')
def login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def do_login():

    locked, remaining = is_locked()
    if locked:
        flash(f"Account locked. Try again in {remaining} seconds.")
        return redirect('/')

    user = request.form.get('username')
    pwd = request.form.get('password')

    if user == USERNAME and pwd == PASSWORD:
        session['login_attempts'] = 0

        otp = totp.now()

        signature = private_key.sign(
            otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # SEND OTP
        try:
            client.messages.create(
                body=f"Your OTP is: {otp}",
                from_=TWILIO_NUMBER,
                to=USER_PHONE
            )
        except Exception:
            print("Twilio error (check credentials)")

        session['otp'] = otp
        session['signature'] = signature.hex()
        session['time'] = time.time()
        session['otp_attempts'] = 0

        return redirect('/otp')

    # ❌ Wrong login
    session['login_attempts'] = session.get('login_attempts', 0) + 1

    if session['login_attempts'] >= MAX_ATTEMPTS:
        session['lock_until'] = time.time() + LOCK_TIME
        flash("Too many failed attempts. Locked for 2 minutes.")
    else:
        left = MAX_ATTEMPTS - session['login_attempts']
        flash(f"Invalid Credentials. Attempts left: {left}")

    return redirect('/')


@app.route('/otp')
def otp_page():
    locked, remaining = is_locked()
    if locked:
        flash(f"Account locked. Try again in {remaining} seconds.")
        return redirect('/')
    return render_template("otp.html")


@app.route('/verify', methods=['POST'])
def verify():

    locked, remaining = is_locked()
    if locked:
        flash(f"Account locked. Try again in {remaining} seconds.")
        return redirect('/otp')

    user_otp = request.form.get('otp')

    stored_otp = session.get('otp')
    signature_hex = session.get('signature')
    timestamp = session.get('time')

    if not stored_otp or not signature_hex:
        flash("Session expired. Login again.")
        return redirect('/')

    if time.time() - timestamp > 120:
        flash("OTP Expired")
        return redirect('/otp')

    signature = bytes.fromhex(signature_hex)

    try:
        public_key.verify(
            signature,
            user_otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        if user_otp == stored_otp:
            session['logged_in'] = True
            session['otp_attempts'] = 0
            return redirect('/dashboard')

    except Exception:
        pass

    # ❌ Wrong OTP
    session['otp_attempts'] = session.get('otp_attempts', 0) + 1

    if session['otp_attempts'] >= MAX_ATTEMPTS:
        session['lock_until'] = time.time() + LOCK_TIME
        flash("Too many wrong OTP attempts. Locked for 2 minutes.")
    else:
        left = MAX_ATTEMPTS - session['otp_attempts']
        flash(f"Invalid OTP. Attempts left: {left}")

    return redirect('/otp')


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template("dashboard.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)

    '''
=======
'''
from flask import Flask, render_template, request, redirect, session, url_for
import pyotp, time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------------
# Twilio CONFIG (PUT YOUR VALUES)
# -------------------------
ACCOUNT_SID = "ACf2e365f78c1c9a20f8996996457db260"
AUTH_TOKEN = "ae8baadd4cffcb487e8b8f5577ba366d"
TWILIO_NUMBER = "+18392505733"
USER_PHONE = "+919373753984"   # your phone

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# -------------------------
# USER
# -------------------------
USERNAME = "admin"
PASSWORD = "password123"

# -------------------------
# RSA Keys
# -------------------------
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# -------------------------
# OTP
# -------------------------
totp_secret = pyotp.random_base32()
totp = pyotp.TOTP(totp_secret)

# -------------------------
# Login Required Decorator
# -------------------------
def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/')
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# -------------------------
# ROUTES
# -------------------------
@app.route('/')
def login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def do_login():
    user = request.form['username']
    pwd = request.form['password']

    if user == USERNAME and pwd == PASSWORD:

        otp = totp.now()

        signature = private_key.sign(
            otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Send SMS via Twilio
        client.messages.create(
            body=f"Your OTP is: {otp}",
            from_=TWILIO_NUMBER,
            to=USER_PHONE
        )

        session['otp'] = otp
        session['signature'] = signature.hex()
        session['time'] = time.time()

        return redirect('/otp')

    return "Invalid Credentials"


@app.route('/otp')
def otp_page():
    return render_template("otp.html")


@app.route('/verify', methods=['POST'])
def verify():
    user_otp = request.form['otp']

    stored_otp = session.get('otp')
    signature = bytes.fromhex(session.get('signature'))
    timestamp = session.get('time')

    if time.time() - timestamp > 120:
        return "OTP Expired"

    try:
        public_key.verify(
            signature,
            user_otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        if user_otp == stored_otp:
            session['logged_in'] = True
            return redirect('/dashboard')

    except Exception:
        return "Invalid OTP"

    return "Verification Failed"


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route('/home')
@login_required
def home():
    return render_template("home.html")


@app.route('/about')
@login_required
def about():
    return render_template("about.html")


@app.route('/projects')
@login_required
def projects():
    return render_template("projects.html")


@app.route('/contact')
@login_required
def contact():
    return render_template("contact.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)

'''


from flask import Flask, render_template, request, redirect, session, flash
import pyotp, time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "supersecretkey"

# -------------------------
# TWILIO CONFIG
# -------------------------
ACCOUNT_SID = "ACf2e365f78c1c9a20f8996996457db260"
AUTH_TOKEN = "ae8baadd4cffcb487e8b8f5577ba366d"
TWILIO_NUMBER = "+18392505733"
USER_PHONE = "+919373753984"   # your phone    

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# -------------------------
# USER
# -------------------------
USERNAME = "admin"
PASSWORD = "password123"

# -------------------------
# RSA KEYS
# -------------------------
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# -------------------------
# OTP
# -------------------------
totp_secret = pyotp.random_base32()
totp = pyotp.TOTP(totp_secret)

# -------------------------
# SECURITY SETTINGS
# -------------------------
MAX_ATTEMPTS = 3
LOCK_TIME = 120

# -------------------------
# LOCK CHECK
# -------------------------
def is_locked():
    lock_until = session.get('lock_until')
    if lock_until and time.time() < lock_until:
        return True, int(lock_until - time.time())
    return False, 0

# -------------------------
# ROUTES
# -------------------------
@app.route('/')
def login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def do_login():

    locked, remaining = is_locked()
    if locked:
        flash(f"Account locked. Try again in {remaining} seconds.")
        return redirect('/')

    user = request.form.get('username')
    pwd = request.form.get('password')

    if user == USERNAME and pwd == PASSWORD:
        session['login_attempts'] = 0

        otp = totp.now()

        # RSA SIGNATURE
        signature = private_key.sign(
            otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # -------------------------
        # SEND OTP VIA TWILIO
        # -------------------------
        try:
            client.messages.create(
                body=f"Your OTP is: {otp}",
                from_=TWILIO_NUMBER,
                to=USER_PHONE
            )
            print("OTP sent via SMS")
        except Exception as e:
            print("Twilio Error:", e)
            print("Fallback OTP:", otp)

        # STORE IN SESSION
        session['otp'] = otp
        session['signature'] = signature.hex()
        session['time'] = time.time()
        session['otp_attempts'] = 0

        return redirect('/otp')

    # -------------------------
    # WRONG LOGIN
    # -------------------------
    session['login_attempts'] = session.get('login_attempts', 0) + 1

    if session['login_attempts'] >= MAX_ATTEMPTS:
        session['lock_until'] = time.time() + LOCK_TIME
        flash("Too many failed attempts. Locked for 2 minutes.")
    else:
        left = MAX_ATTEMPTS - session['login_attempts']
        flash(f"Invalid Credentials. Attempts left: {left}")

    return redirect('/')


@app.route('/otp')
def otp_page():

    locked, remaining = is_locked()
    if locked:
        flash(f"Account locked. Try again in {remaining} seconds.")
        return redirect('/')

    return render_template("otp.html")


@app.route('/verify', methods=['POST'])
def verify():

    locked, remaining = is_locked()
    if locked:
        flash(f"Account locked. Try again in {remaining} seconds.")
        return redirect('/otp')

    user_otp = request.form.get('otp')

    stored_otp = session.get('otp')
    signature_hex = session.get('signature')
    timestamp = session.get('time')

    if not stored_otp or not signature_hex:
        flash("Session expired. Login again.")
        return redirect('/')

    # OTP expiry
    if time.time() - timestamp > 120:
        flash("OTP Expired")
        return redirect('/otp')

    signature = bytes.fromhex(signature_hex)

    try:
        # VERIFY SIGNATURE
        public_key.verify(
            signature,
            user_otp.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        if user_otp == stored_otp:
            session['logged_in'] = True
            session['otp_attempts'] = 0
            return redirect('/dashboard')

    except Exception:
        pass

    # -------------------------
    # WRONG OTP
    # -------------------------
    session['otp_attempts'] = session.get('otp_attempts', 0) + 1

    if session['otp_attempts'] >= MAX_ATTEMPTS:
        session['lock_until'] = time.time() + LOCK_TIME
        flash("Too many wrong OTP attempts. Locked for 2 minutes.")
    else:
        left = MAX_ATTEMPTS - session['otp_attempts']
        flash(f"Invalid OTP. Attempts left: {left}")

    return redirect('/otp')


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template("dashboard.html")


@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template("home.html")


@app.route('/about')
def about():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template("about.html")


@app.route('/contact')
def contact():
    if not session.get('logged_in'):
        return redirect('/')
    return render_template("contact.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
>>>>>>> 486999dc758d33c8a2f50ce1ab1f6ebeb17ad1cf
