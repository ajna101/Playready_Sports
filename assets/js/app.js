// Plaready API Client
// Save this as: assets/js/api-client.js

const API_BASE_URL = window.location.origin + '/api';

// ============================================================================
// CORE API UTILITY
// ============================================================================

async function apiCall(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    credentials: 'include', // Important for session cookies
    headers: {
      'Content-Type': 'application/json'
    }
  };
  
  if (body) {
    options.body = JSON.stringify(body);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Request failed');
    }
    
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// ============================================================================
// AUTHENTICATION API
// ============================================================================

const AuthAPI = {
  async register(phone, password, name, email, role = 'customer') {
    return await apiCall('/auth/register', 'POST', {
      phone,
      password,
      name,
      email,
      role
    });
  },

  async login(phone, password) {
    return await apiCall('/auth/login', 'POST', { phone, password });
  },

  async logout() {
    return await apiCall('/auth/logout', 'POST');
  },

  async getCurrentUser() {
    return await apiCall('/auth/me');
  },

  // Check if user is logged in
  async isAuthenticated() {
    try {
      await this.getCurrentUser();
      return true;
    } catch {
      return false;
    }
  }
};

// ============================================================================
// SERVICES API
// ============================================================================

const ServicesAPI = {
  async getAll() {
    return await apiCall('/services');
  },

  async getById(serviceId) {
    const services = await this.getAll();
    return services.find(s => s.id === serviceId);
  }
};

// ============================================================================
// ORDERS API
// ============================================================================

const OrdersAPI = {
  async create(orderData) {
    // orderData should include:
    // {
    //   service_id, racquet_type, string_type, tension,
    //   pickup_address, pickup_slot, coupon_code (optional)
    // }
    return await apiCall('/orders', 'POST', orderData);
  },

  async getMyOrders() {
    return await apiCall('/orders/my');
  },

  async getOrderDetails(orderId) {
    return await apiCall(`/orders/${orderId}`);
  },

  // Format order for display
  formatOrder(order) {
    return {
      ...order,
      statusBadge: this.getStatusBadge(order.status),
      formattedDate: new Date(order.created_at).toLocaleDateString('en-IN'),
      formattedPrice: `₹${order.total_price.toFixed(2)}`
    };
  },

  getStatusBadge(status) {
    const badges = {
      'pending': { color: 'yellow', text: 'Pending' },
      'assigned': { color: 'blue', text: 'Assigned' },
      'pickup_scheduled': { color: 'purple', text: 'Pickup Scheduled' },
      'picked_up': { color: 'indigo', text: 'Picked Up' },
      'in_repair': { color: 'orange', text: 'In Repair' },
      'ready_for_delivery': { color: 'cyan', text: 'Ready' },
      'out_for_delivery': { color: 'blue', text: 'Out for Delivery' },
      'delivered': { color: 'green', text: 'Delivered' },
      'cancelled': { color: 'red', text: 'Cancelled' }
    };
    return badges[status] || { color: 'gray', text: status };
  }
};

// ============================================================================
// COUPONS API
// ============================================================================

const CouponsAPI = {
  async validate(code, orderValue) {
    return await apiCall('/coupons/validate', 'POST', {
      code,
      order_value: orderValue
    });
  },

  // Calculate discount amount
  calculateDiscount(couponData, orderValue) {
    if (!couponData.valid) return 0;
    
    if (couponData.discount_type === 'percentage') {
      let discount = orderValue * (couponData.discount_value / 100);
      if (couponData.max_discount) {
        discount = Math.min(discount, couponData.max_discount);
      }
      return discount;
    } else {
      return couponData.discount_value;
    }
  }
};

// ============================================================================
// PARTNER API
// ============================================================================

const PartnerAPI = {
  async register(partnerData) {
    // partnerData should include:
    // {
    //   business_name, address, city, pincode,
    //   gst_number, bank_account, ifsc_code
    // }
    return await apiCall('/partner/register', 'POST', partnerData);
  },

  async getOrders(status = null) {
    const endpoint = status ? `/partner/orders?status=${status}` : '/partner/orders';
    return await apiCall(endpoint);
  },

  async updateOrderStatus(orderId, status) {
    return await apiCall(`/partner/orders/${orderId}/status`, 'PUT', { status });
  }
};

// ============================================================================
// ADMIN API
// ============================================================================

const AdminAPI = {
  async getPartners() {
    return await apiCall('/admin/partners');
  },

  async approvePartner(partnerId) {
    return await apiCall(`/admin/partners/${partnerId}/approve`, 'PUT');
  },

  async getAllOrders(status = null) {
    const endpoint = status ? `/admin/orders?status=${status}` : '/admin/orders';
    return await apiCall(endpoint);
  },

  async assignPartner(orderId, partnerId) {
    return await apiCall(`/admin/orders/${orderId}/assign`, 'PUT', {
      partner_id: partnerId
    });
  },

  async getAnalytics() {
    return await apiCall('/admin/analytics');
  }
};

// ============================================================================
// UI HELPER FUNCTIONS
// ============================================================================

const UIHelpers = {
  // Show loading state
  showLoading(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
      el.innerHTML = '<div class="flex justify-center items-center p-8"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div></div>';
    }
  },

  // Show error message
  showError(message, elementId = null) {
    const errorHTML = `
      <div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        <p class="font-medium">Error</p>
        <p class="text-sm">${message}</p>
      </div>
    `;
    
    if (elementId) {
      document.getElementById(elementId).innerHTML = errorHTML;
    } else {
      alert(message);
    }
  },

  // Show success message
  showSuccess(message, elementId = null) {
    const successHTML = `
      <div class="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
        <p class="font-medium">Success</p>
        <p class="text-sm">${message}</p>
      </div>
    `;
    
    if (elementId) {
      document.getElementById(elementId).innerHTML = successHTML;
    } else {
      alert(message);
    }
  },

  // Format currency
  formatCurrency(amount) {
    return `₹${parseFloat(amount).toFixed(2)}`;
  },

  // Format date
  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  },

  // Format date and time
  formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};

// ============================================================================
// LOCAL STORAGE HELPERS
// ============================================================================

const Storage = {
  set(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  },

  get(key) {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  },

  remove(key) {
    localStorage.removeItem(key);
  },

  clear() {
    localStorage.clear();
  }
};

// ============================================================================
// EXPORT FOR USE
// ============================================================================

// Make APIs available globally
window.PlareadyAPI = {
  Auth: AuthAPI,
  Services: ServicesAPI,
  Orders: OrdersAPI,
  Coupons: CouponsAPI,
  Partner: PartnerAPI,
  Admin: AdminAPI,
  UI: UIHelpers,
  Storage: Storage
};

console.log('✅ Plaready API Client loaded successfully!');