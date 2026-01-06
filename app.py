from flask import Flask, request, jsonify, session, send_from_directory, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import os

app = Flask(__name__, 
            static_folder='.',  # Serve all files from current directory
            static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///plaready.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='customer')  # customer, partner, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    business_name = db.Column(db.String(200))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    gst_number = db.Column(db.String(50))
    bank_account = db.Column(db.String(50))
    ifsc_code = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    commission_rate = db.Column(db.Float, default=20.0)
    rating = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # stringing, grip, restringing
    base_price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('partner.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    
    # Order details
    racquet_type = db.Column(db.String(50))
    string_type = db.Column(db.String(100))
    tension = db.Column(db.String(20))
    pickup_address = db.Column(db.Text)
    pickup_slot = db.Column(db.DateTime)
    
    # Pricing
    base_price = db.Column(db.Float)
    string_price = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_price = db.Column(db.Float)
    
    # Status tracking
    status = db.Column(db.String(30), default='pending')  
    # pending, assigned, pickup_scheduled, picked_up, in_repair, 
    # ready_for_delivery, out_for_delivery, delivered, cancelled
    
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20))
    
    # Logistics
    pickup_tracking_id = db.Column(db.String(100))
    delivery_tracking_id = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id])
    partner = db.relationship('Partner', foreign_keys=[partner_id])
    service = db.relationship('Service')

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20))  # percentage, fixed
    discount_value = db.Column(db.Float)
    min_order_value = db.Column(db.Float, default=0)
    max_discount = db.Column(db.Float)
    valid_from = db.Column(db.DateTime)
    valid_until = db.Column(db.DateTime)
    usage_limit = db.Column(db.Integer)
    usage_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

# ============================================================================
# STATIC FILE ROUTES
# ============================================================================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve all static files (HTML, CSS, JS, images)"""
    try:
        return send_from_directory('.', path)
    except:
        return jsonify({'error': 'File not found'}), 404

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    
    if User.query.filter_by(phone=data['phone']).first():
        return jsonify({'error': 'Phone number already registered'}), 400
    
    user = User(
        phone=data['phone'],
        name=data.get('name'),
        email=data.get('email'),
        role=data.get('role', 'customer')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    session['role'] = user.role
    
    return jsonify({
        'message': 'Registration successful',
        'user': {
            'id': user.id,
            'name': user.name,
            'phone': user.phone,
            'role': user.role
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(phone=data['phone']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user.id
    session['role'] = user.role
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'name': user.name,
            'phone': user.phone,
            'role': user.role
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    return jsonify({
        'id': user.id,
        'name': user.name,
        'phone': user.phone,
        'email': user.email,
        'role': user.role
    })

# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.route('/api/services', methods=['GET'])
def get_services():
    services = Service.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'category': s.category,
        'base_price': s.base_price,
        'description': s.description,
        'image_url': s.image_url
    } for s in services])

@app.route('/api/orders', methods=['POST'])
def create_order():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    service = Service.query.get(data['service_id'])
    
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    # Generate order number
    order_number = f"PLR{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(3).upper()}"
    
    # Calculate pricing
    base_price = service.base_price
    string_price = data.get('string_price', 0)
    discount = 0
    
    # Apply coupon if provided
    if data.get('coupon_code'):
        coupon = Coupon.query.filter_by(code=data['coupon_code'], is_active=True).first()
        if coupon and coupon.valid_until > datetime.utcnow():
            if coupon.discount_type == 'percentage':
                discount = (base_price + string_price) * (coupon.discount_value / 100)
                if coupon.max_discount:
                    discount = min(discount, coupon.max_discount)
            else:
                discount = coupon.discount_value
            coupon.usage_count += 1
    
    total_price = base_price + string_price - discount
    
    order = Order(
        order_number=order_number,
        customer_id=session['user_id'],
        service_id=data['service_id'],
        racquet_type=data.get('racquet_type'),
        string_type=data.get('string_type'),
        tension=data.get('tension'),
        pickup_address=data.get('pickup_address'),
        pickup_slot=datetime.fromisoformat(data['pickup_slot']),
        base_price=base_price,
        string_price=string_price,
        discount=discount,
        total_price=total_price,
        payment_method=data.get('payment_method', 'online')
    )
    
    db.session.add(order)
    db.session.commit()
    
    return jsonify({
        'message': 'Order created successfully',
        'order_number': order_number,
        'order_id': order.id,
        'total_price': total_price
    }), 201

@app.route('/api/orders/my', methods=['GET'])
def get_my_orders():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    orders = Order.query.filter_by(customer_id=session['user_id']).order_by(Order.created_at.desc()).all()
    
    return jsonify([{
        'id': o.id,
        'order_number': o.order_number,
        'service_name': o.service.name,
        'status': o.status,
        'total_price': o.total_price,
        'pickup_slot': o.pickup_slot.isoformat() if o.pickup_slot else None,
        'created_at': o.created_at.isoformat()
    } for o in orders])

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Check authorization
    if session['role'] == 'customer' and order.customer_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': order.id,
        'order_number': order.order_number,
        'service': {
            'name': order.service.name,
            'category': order.service.category
        },
        'racquet_type': order.racquet_type,
        'string_type': order.string_type,
        'tension': order.tension,
        'pickup_address': order.pickup_address,
        'pickup_slot': order.pickup_slot.isoformat() if order.pickup_slot else None,
        'base_price': order.base_price,
        'string_price': order.string_price,
        'discount': order.discount,
        'total_price': order.total_price,
        'status': order.status,
        'payment_status': order.payment_status,
        'created_at': order.created_at.isoformat(),
        'partner': {
            'business_name': order.partner.business_name
        } if order.partner else None
    })

@app.route('/api/coupons/validate', methods=['POST'])
def validate_coupon():
    data = request.json
    coupon = Coupon.query.filter_by(code=data['code'], is_active=True).first()
    
    if not coupon:
        return jsonify({'error': 'Invalid coupon code'}), 404
    
    if coupon.valid_until < datetime.utcnow():
        return jsonify({'error': 'Coupon has expired'}), 400
    
    if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
        return jsonify({'error': 'Coupon usage limit reached'}), 400
    
    order_value = data.get('order_value', 0)
    if order_value < coupon.min_order_value:
        return jsonify({'error': f'Minimum order value ₹{coupon.min_order_value} required'}), 400
    
    discount = 0
    if coupon.discount_type == 'percentage':
        discount = order_value * (coupon.discount_value / 100)
        if coupon.max_discount:
            discount = min(discount, coupon.max_discount)
    else:
        discount = coupon.discount_value
    
    return jsonify({
        'valid': True,
        'discount': discount,
        'discount_type': coupon.discount_type,
        'discount_value': coupon.discount_value
    })

# ============================================================================
# PARTNER ENDPOINTS
# ============================================================================

@app.route('/api/partner/register', methods=['POST'])
def register_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    partner = Partner(
        user_id=session['user_id'],
        business_name=data['business_name'],
        address=data['address'],
        city=data['city'],
        pincode=data['pincode'],
        gst_number=data.get('gst_number'),
        bank_account=data['bank_account'],
        ifsc_code=data['ifsc_code']
    )
    
    db.session.add(partner)
    
    # Update user role
    user = User.query.get(session['user_id'])
    user.role = 'partner'
    session['role'] = 'partner'
    
    db.session.commit()
    
    return jsonify({'message': 'Partner registration submitted for approval'}), 201

@app.route('/api/partner/orders', methods=['GET'])
def get_partner_orders():
    if 'user_id' not in session or session['role'] != 'partner':
        return jsonify({'error': 'Unauthorized'}), 403
    
    partner = Partner.query.filter_by(user_id=session['user_id']).first()
    
    if not partner:
        return jsonify({'error': 'Partner profile not found'}), 404
    
    status_filter = request.args.get('status')
    query = Order.query.filter_by(partner_id=partner.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return jsonify([{
        'id': o.id,
        'order_number': o.order_number,
        'customer_name': o.customer.name,
        'service_name': o.service.name,
        'status': o.status,
        'total_price': o.total_price,
        'pickup_slot': o.pickup_slot.isoformat() if o.pickup_slot else None,
        'created_at': o.created_at.isoformat()
    } for o in orders])

@app.route('/api/partner/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    if 'user_id' not in session or session['role'] != 'partner':
        return jsonify({'error': 'Unauthorized'}), 403
    
    partner = Partner.query.filter_by(user_id=session['user_id']).first()
    order = Order.query.get(order_id)
    
    if not order or order.partner_id != partner.id:
        return jsonify({'error': 'Order not found'}), 404
    
    data = request.json
    order.status = data['status']
    order.updated_at = datetime.utcnow()
    
    if data['status'] == 'delivered':
        order.completed_at = datetime.utcnow()
        partner.total_orders += 1
    
    db.session.commit()
    
    return jsonify({'message': 'Order status updated'})

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.route('/api/admin/partners', methods=['GET'])
def get_all_partners():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    partners = Partner.query.all()
    
    return jsonify([{
        'id': p.id,
        'business_name': p.business_name,
        'city': p.city,
        'status': p.status,
        'rating': p.rating,
        'total_orders': p.total_orders,
        'commission_rate': p.commission_rate,
        'created_at': p.created_at.isoformat()
    } for p in partners])

@app.route('/api/admin/partners/<int:partner_id>/approve', methods=['PUT'])
def approve_partner(partner_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    partner = Partner.query.get(partner_id)
    if not partner:
        return jsonify({'error': 'Partner not found'}), 404
    
    partner.status = 'approved'
    db.session.commit()
    
    return jsonify({'message': 'Partner approved'})

@app.route('/api/admin/orders', methods=['GET'])
def get_all_orders():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    status_filter = request.args.get('status')
    query = Order.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).limit(100).all()
    
    return jsonify([{
        'id': o.id,
        'order_number': o.order_number,
        'customer_name': o.customer.name,
        'service_name': o.service.name,
        'partner_name': o.partner.business_name if o.partner else None,
        'status': o.status,
        'total_price': o.total_price,
        'created_at': o.created_at.isoformat()
    } for o in orders])

@app.route('/api/admin/orders/<int:order_id>/assign', methods=['PUT'])
def assign_partner(order_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    order.partner_id = data['partner_id']
    order.status = 'assigned'
    db.session.commit()
    
    return jsonify({'message': 'Partner assigned successfully'})

@app.route('/api/admin/analytics', methods=['GET'])
def get_analytics():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_price)).scalar() or 0
    active_partners = Partner.query.filter_by(status='approved').count()
    pending_orders = Order.query.filter_by(status='pending').count()
    
    return jsonify({
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'active_partners': active_partners,
        'pending_orders': pending_orders
    })

# ============================================================================
# INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(phone='9999999999').first():
            admin = User(phone='9999999999', name='Admin User', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Create sample services
        if Service.query.count() == 0:
            services = [
                Service(name='Badminton Restringing', category='stringing', base_price=299, description='Professional badminton racquet restringing'),
                Service(name='Tennis Restringing', category='stringing', base_price=399, description='Professional tennis racquet restringing'),
                Service(name='Grip Replacement', category='grip', base_price=149, description='New grip installation'),
                Service(name='Full Racquet Service', category='repair', base_price=599, description='Complete racquet maintenance')
            ]
            db.session.add_all(services)
        
        # Create sample coupon
        if Coupon.query.count() == 0:
            coupon = Coupon(
                code='FIRST50',
                discount_type='percentage',
                discount_value=50,
                max_discount=200,
                valid_from=datetime.utcnow(),
                valid_until=datetime.utcnow() + timedelta(days=30),
                usage_limit=100
            )
            db.session.add(coupon)
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
    # Disable reloader to avoid Streamlit package detection issues
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)