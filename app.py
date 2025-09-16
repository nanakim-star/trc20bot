import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, JWTManager, jwt_required
from datetime import timedelta
from notification_helper import send_telegram_alert, send_server_alert

app = Flask(__name__)
db = SQLAlchemy()

# --- ⭐️ 데이터베이스 연결 부분 수정 ⭐️ ---
# Render가 자동으로 생성해준 DATABASE_URL 환경 변수를 직접 사용합니다.
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
# -----------------------------------------

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)
db.init_app(app)

# --- (이하 모든 코드는 이전과 동일합니다) ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Wallet(db.Model):
    __tablename__ = 'wallets'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), unique=True, nullable=False)
    bot_token = db.Column(db.String(200), nullable=False)
    chat_id = db.Column(db.String(100), nullable=False)
    notification_url = db.Column(db.String(255), nullable=True)
    notification_api_key = db.Column(db.String(255), nullable=True)
    tatum_subscription_id = db.Column(db.String(100), nullable=True)

with app.app_context():
    db.create_all()

@app.route('/admin')
def admin_dashboard(): return render_template('index.html')

@app.route('/admin/login')
def admin_login_page(): return render_template('login.html')

@app.route('/')
def index(): return "Bot server is alive."

@app.route('/setup-admin')
def setup_admin():
    key_from_url = request.args.get('key')
    key_from_env = os.environ.get('SETUP_KEY')
    if key_from_url != key_from_env: return "Unauthorized", 401
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')
    if not username or not password: return "ADMIN_USERNAME and ADMIN_PASSWORD must be set in environment variables.", 500
    user = db.session.query(User).filter_by(username=username).first()
    if user:
        user.set_password(password)
        db.session.commit()
        return f"Admin user '{username}' password has been updated successfully.", 200
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return f"Admin user '{username}' created successfully.", 200

@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    user = db.session.query(User).filter_by(username=username).first()
    if not user or not user.check_password(password): return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

@app.route('/api/wallets', methods=['GET'])
@jwt_required()
def get_wallets():
    wallets = db.session.query(Wallet).all()
    wallet_list = []
    for wallet in wallets:
        wallet_list.append({'id': wallet.id, 'name': wallet.name, 'address': wallet.address, 'bot_token': wallet.bot_token, 'chat_id': wallet.chat_id, 'notification_url': wallet.notification_url, 'notification_api_key': wallet.notification_api_key})
    return jsonify(wallet_list)

@app.route('/api/wallets', methods=['POST'])
@jwt_required()
def add_wallet():
    data = request.get_json()
    if not all(k in data for k in ('name', 'address', 'bot_token', 'chat_id')): return jsonify({'msg': 'Missing required fields'}), 400
    if db.session.query(Wallet).filter_by(address=data['address']).first(): return jsonify({'msg': 'Wallet address already exists'}), 400
    new_wallet = Wallet(name=data['name'], address=data['address'], bot_token=data['bot_token'], chat_id=data['chat_id'], notification_url=data.get('notification_url'), notification_api_key=data.get('notification_api_key'))
    db.session.add(new_wallet)
    db.session.commit()
    return jsonify({'msg': 'Wallet added successfully', 'id': new_wallet.id}), 201

@app.route('/api/wallets/<int:wallet_id>', methods=['DELETE'])
@jwt_required()
def delete_wallet(wallet_id):
    wallet = db.session.query(Wallet).get(wallet_id)
    if not wallet: return jsonify({'msg': 'Wallet not found'}), 404
    db.session.delete(wallet)
    db.session.commit()
    return jsonify({'msg': 'Wallet deleted successfully'})

@app.route('/api/wallets/<int:wallet_id>', methods=['PUT'])
@jwt_required()
def update_wallet(wallet_id):
    wallet = db.session.query(Wallet).get(wallet_id)
    if not wallet: return jsonify({'msg': 'Wallet not found'}), 404
    data = request.get_json()
    if 'address' in data and data['address'] != wallet.address:
        if db.session.query(Wallet).filter(Wallet.id != wallet_id, Wallet.address == data['address']).first():
            return jsonify({'msg': 'New wallet address already exists'}), 400
    wallet.name = data.get('name', wallet.name)
    wallet.address = data.get('address', wallet.address)
    wallet.bot_token = data.get('bot_token', wallet.bot_token)
    wallet.chat_id = data.get('chat_id', wallet.chat_id)
    wallet.notification_url = data.get('notification_url', wallet.notification_url)
    wallet.notification_api_key = data.get('notification_api_key', wallet.notification_api_key)
    db.session.commit()
    return jsonify({'msg': 'Wallet updated successfully'})

@app.route('/tatum-webhook', methods=['POST'])
def tatum_webhook():
    data = request.get_json()
    print(f"Received webhook from Tatum: {data}")
    USDT_CONTRACT_ADDRESS = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    target_address = data.get('address')
    amount = data.get('amount')
    tx_id = data.get('txId')
    contract_address = data.get('contractAddress')
    if not all([target_address, amount, tx_id, contract_address]): return "Missing required data", 400
    if contract_address != USDT_CONTRACT_ADDRESS: return "Transaction is not for USDT", 200
    wallet = db.session.query(Wallet).filter_by(address=target_address).first()
    if wallet:
        print(f"✅ Wallet found in DB: {wallet.name}. Preparing to send notifications.")
        message = (f"✅ *입금 알림*\n\n💰 *금액:* `{amount}` USDT\n🏠 *입금 주소:* `{target_address}`\n🔗 *거래 ID:* `{tx_id}`")
        send_telegram_alert(wallet.bot_token, wallet.chat_id, message)
        server_data = {'amount': amount, 'address': target_address, 'txId': tx_id, 'wallet_name': wallet.name}
        send_server_alert(wallet.notification_url, wallet.notification_api_key, server_data)
    else:
        print(f"❌ Wallet NOT found in DB for address: {target_address}")
    return "Webhook received and processed", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
