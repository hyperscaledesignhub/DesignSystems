const API_BASE = {
  hotel: 'http://localhost:8001',
  room: 'http://localhost:8002',
  guest: 'http://localhost:8003',
  inventory: 'http://localhost:8004',
  reservation: 'http://localhost:8005',
  payment: 'http://localhost:8006'
};

class ApiService {
  async request(service, endpoint, options = {}) {
    const url = `${API_BASE[service]}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || `HTTP error! status: ${response.status}`);
      }
      
      return data;
    } catch (error) {
      console.error(`API Error (${service}${endpoint}):`, error);
      throw error;
    }
  }

  // Guest Service
  async registerGuest(guestData) {
    return this.request('guest', '/guests/register', {
      method: 'POST',
      body: JSON.stringify(guestData)
    });
  }

  async getGuest(guestId) {
    return this.request('guest', `/guests/${guestId}`);
  }

  // Hotel Service
  async getHotels() {
    return this.request('hotel', '/api/v1/hotels');
  }

  async getHotel(hotelId) {
    return this.request('hotel', `/api/v1/hotels/${hotelId}`);
  }

  async createHotel(hotelData) {
    return this.request('hotel', '/api/v1/hotels', {
      method: 'POST',
      body: JSON.stringify(hotelData)
    });
  }

  // Room Service
  async getRoomTypes(hotelId) {
    return this.request('room', `/api/v1/hotels/${hotelId}/room-types`);
  }

  async getRoomType(hotelId, roomTypeId) {
    return this.request('room', `/api/v1/hotels/${hotelId}/room-types/${roomTypeId}`);
  }

  async createRoomType(hotelId, roomData) {
    return this.request('room', `/api/v1/hotels/${hotelId}/room-types`, {
      method: 'POST',
      body: JSON.stringify(roomData)
    });
  }

  // Inventory Service
  async checkAvailability(roomTypeId, checkIn, checkOut, numRooms = 1) {
    const params = new URLSearchParams({
      room_type_id: roomTypeId,
      check_in: checkIn,
      check_out: checkOut,
      num_rooms: numRooms
    });
    return this.request('inventory', `/availability?${params}`);
  }

  async reserveRooms(hotelId, roomTypeId, checkIn, checkOut, numRooms) {
    const params = new URLSearchParams({
      hotel_id: hotelId,
      room_type_id: roomTypeId,
      check_in: checkIn,
      check_out: checkOut,
      num_rooms: numRooms
    });
    return this.request('inventory', `/reserve?${params}`, {
      method: 'POST'
    });
  }

  async releaseRooms(hotelId, roomTypeId, checkIn, checkOut, numRooms) {
    const params = new URLSearchParams({
      hotel_id: hotelId,
      room_type_id: roomTypeId,
      check_in: checkIn,
      check_out: checkOut,
      num_rooms: numRooms
    });
    return this.request('inventory', `/release?${params}`, {
      method: 'POST'
    });
  }

  // Reservation Service
  async createReservation(reservationData) {
    return this.request('reservation', '/reservations', {
      method: 'POST',
      body: JSON.stringify(reservationData)
    });
  }

  async getReservations(guestId) {
    const params = guestId ? `?guest_id=${guestId}` : '';
    return this.request('reservation', `/reservations${params}`);
  }

  async getReservation(reservationId) {
    return this.request('reservation', `/reservations/${reservationId}`);
  }

  async cancelReservation(reservationId) {
    return this.request('reservation', `/reservations/${reservationId}/cancel`, {
      method: 'POST'
    });
  }

  // Payment Service
  async processPayment(paymentData) {
    return this.request('payment', '/payments/process', {
      method: 'POST',
      body: JSON.stringify(paymentData)
    });
  }

  async getPayments(reservationId) {
    const params = reservationId ? `?reservation_id=${reservationId}` : '';
    return this.request('payment', `/payments${params}`);
  }

  async getPayment(paymentId) {
    return this.request('payment', `/payments/${paymentId}`);
  }

  // Utility methods
  formatDate(date) {
    return date.toISOString().split('T')[0];
  }

  formatDateTime(dateTime) {
    return new Date(dateTime).toLocaleString();
  }

  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }
}

export default new ApiService();