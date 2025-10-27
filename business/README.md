# Business App for WozapAuto

This module provides comprehensive business management with AI-powered WhatsApp bot integration using LangChain v3 tools.

## 🏢 Supported Business Types

- **E-commerce Store** - Online retail with products, variants, and inventory
- **Restaurant/Food Service** - Menu items, reservations, and delivery
- **Retail Store** - Physical products with variants and inventory
- **Professional Services** - Consulting, legal, accounting services
- **Appointment Booking** - Salons, clinics, consultants with scheduling
- **Subscription Service** - Recurring services and memberships
- **Marketplace** - Multi-vendor platforms
- **Consultation Services** - Advisory and consultation services
- **Education/Training** - Courses, classes, and educational services
- **Healthcare Services** - Medical appointments and health services
- **Beauty & Wellness** - Salons, spas, fitness studios
- **Automotive Services** - Auto repair, dealerships, services
- **Real Estate** - Property listings and viewings
- **Travel & Tourism** - Travel agencies and tour services
- **Entertainment** - Events, venues, entertainment services
- **Fitness & Sports** - Gyms, personal training, sports
- **Logistics & Delivery** - Shipping and delivery services
- **Financial Services** - Banking, insurance, financial advice

## 📊 Core Models

### BusinessProfile
The main business entity that links to WhatsApp bots.

**Key Features:**
- UUID primary key for security
- Business type classification
- Contact information (phone, email, website, address)
- WhatsApp bot settings
- Multi-language and currency support
- Timezone configuration

### Product
Enhanced product model for various business types.

**Key Features:**
- Flexible pricing (base price, compare price, cost price)
- Inventory tracking with low stock alerts
- Product variants (size, color, etc.)
- Digital/physical product support
- SEO fields (meta title, description, slug)
- Multiple images support
- Featured product flagging

### Service
Services offered by businesses.

**Key Features:**
- Flexible pricing types (fixed, hourly, per person, custom)
- Appointment requirement flags
- Online service support
- Service duration tracking
- Featured service flagging

### Category
Hierarchical category system for products and services.

**Key Features:**
- Parent-child relationships
- Business-specific categories
- Sort ordering
- Image support
- Active/inactive status

## 🤖 AI Engine Integration

### BusinessService
Core service class for business operations:

```python
from business.services import BusinessService

# Initialize with business ID
service = BusinessService(business_id="your-business-uuid")

# Get business information
info = service.get_business_info()

# Search products
products = service.search_products("laptop", limit=5)

# Search services
services = service.search_services("consultation", limit=5)

# Get categories
categories = service.get_categories()

# Check business hours
is_open, message = service.is_business_open()
```

### Business Tools (LangChain v3)
AI-powered business tools for WhatsApp bot integration:

```python
from business.tools import BusinessTool

# Initialize business tool
business_tool = BusinessTool(user=user, business_id="your-business-uuid")

# Get available tools
tools = business_tool.get_tools()

# Tools include:
# - search_products: Search for products by name, description, or category
# - search_services: Search for services and offerings
# - get_business_info: Get business contact details and information
# - check_business_hours: Check if business is open and get operating hours
# - check_appointment_availability: Check available appointment slots
# - get_featured_items: Get featured products and services
# - get_business_summary: Get comprehensive business overview
```

### Web Interface
The business app includes comprehensive web pages for managing:

- **Business Profiles**: Create, edit, and manage business information
- **Products**: Full CRUD operations for product catalog
- **Services**: Service management with appointment scheduling
- **Appointments**: View and manage appointment slots
- **Categories**: Organize products and services
- **Business Hours**: Configure operating hours
- **Locations**: Manage multiple business locations

## 🛠️ Management Commands

### Populate Business Types
```bash
python manage.py populate_business_types
```

This command creates all supported business types with descriptions and icons.

### Test Business Tools
```bash
python manage.py test_business_tools
```

Test the business tools functionality:
```bash
# Test with specific user and business
python manage.py test_business_tools --user admin --business-id your-business-uuid

# Run all tests
python manage.py test_business_tools --test-all
```

## 📱 WhatsApp Bot Features

### Automatic Responses
- **Welcome Messages**: Personalized based on business type
- **Auto-reply**: When business is closed
- **Business Hours**: Real-time open/closed status

### Product & Service Search
- **Smart Search**: Name, description, SKU matching
- **Category Filtering**: Browse by categories
- **Stock Status**: Real-time inventory information
- **Featured Items**: Highlighted products/services

### Appointment Booking
- **Service Scheduling**: For appointment-based businesses
- **Availability Checking**: Real-time slot availability
- **Multi-day Booking**: Up to 30 days in advance

### Business Information
- **Contact Details**: Phone, email, WhatsApp
- **Locations**: Multiple business locations
- **Business Hours**: Day-by-day operating hours
- **Featured Items**: Highlighted products/services

## 🎯 Use Cases

### E-commerce Store
```python
# Product catalog with variants
products = service.search_products("smartphone")
# Returns: products with variants, pricing, stock status

# Featured products
featured = service.get_featured_items(item_type="products")
```

### Restaurant
```python
# Menu items (as products)
menu_items = service.search_products("pizza")
# Returns: menu items with pricing, descriptions

# Service bookings
appointments = service.get_available_appointments(service_id)
# Returns: available time slots for reservations
```

### Professional Services
```python
# Service catalog
services = service.search_services("consultation")
# Returns: services with pricing, duration, appointment requirements

# Appointment booking
slots = service.get_available_appointments(service_id)
# Returns: available consultation slots
```

### Healthcare
```python
# Medical services
services = service.search_services("checkup")
# Returns: medical services with pricing, duration

# Appointment scheduling
appointments = service.get_available_appointments(service_id)
# Returns: available appointment slots
```

## 🔧 Configuration

### Business Settings
Each business can have custom settings:

- **WhatsApp Bot Messages**: Welcome, auto-reply, business hours
- **Order/Booking Settings**: Customer info requirements, minimum orders
- **Payment Settings**: Accepted methods, payment instructions
- **Notification Settings**: Email/SMS preferences
- **Custom Fields**: Business-specific data

### Business Hours
Flexible business hours configuration:

- **Day-by-day**: Different hours for each day
- **24-hour Support**: Round-the-clock businesses
- **Closed Days**: Specific days when closed
- **Multiple Locations**: Different hours per location

## 📈 Performance Features

### Database Optimization
- **Indexes**: Optimized queries for business, category, SKU
- **Select Related**: Efficient joins for related objects
- **Pagination**: Large dataset handling

### Caching
- **Business Info**: Cached business information
- **Categories**: Cached category trees
- **Featured Items**: Cached featured products/services

## 🚀 Getting Started

1. **Create Business Types**:
   ```bash
   python manage.py populate_business_types
   ```

2. **Create Business Profile**:
   ```python
   from business.models import BusinessProfile, BusinessType
   
   business_type = BusinessType.objects.get(name='ecommerce')
   business = BusinessProfile.objects.create(
       name="My Store",
       business_type=business_type,
       phone="+1234567890",
       whatsapp_number="+1234567890"
   )
   ```

3. **Add Products/Services**:
   ```python
   from business.models import Product, Category
   
   category = Category.objects.create(
       business=business,
       name="Electronics"
   )
   
   product = Product.objects.create(
       business=business,
       category=category,
       name="Smartphone",
       price=599.99,
       sku="SMART001"
   )
   ```

4. **Initialize Business Tools**:
   ```python
   from business.tools import BusinessTool
   
   business_tool = BusinessTool(user=user, business_id=str(business.id))
   tools = business_tool.get_tools()
   ```

## 🔗 Integration with AI Engine

The business models integrate seamlessly with the AI engine through LangChain v3 tools:

- **Context Injection**: Business info added to AI context
- **Product/Service Search**: AI can search and recommend items using business tools
- **Appointment Booking**: AI can handle booking requests with availability checking
- **Business Hours**: AI knows when business is open/closed in real-time
- **Contact Information**: AI can provide accurate contact details
- **Featured Items**: AI can highlight popular products and services

### AI Tool Integration
The business tools are automatically integrated into the AI engine:

```python
# In aiengine/service.py
from business.tools import BusinessTool

# Business tools are automatically added to the agent
business_tool = BusinessTool(user=user, callback=self._tool_callback)
tools.extend(business_tool.get_tools())
```

This creates a powerful combination of AI intelligence with comprehensive business data for WhatsApp bot interactions.
