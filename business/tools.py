"""
Business Tools for LangChain v3 Agent Integration.
"""
from typing import Optional, Dict, Any, List, Union
from langchain_core.tools import tool
import logging
import re

from .services import BusinessService
from .models import BusinessProfile, Cart, CartItem, AppointmentBooking, Product, Service, AppointmentSlot, ProductVariant

logger = logging.getLogger("business.tools")


class BusinessTool:
    """Business tool for LangChain agents with comprehensive business operations."""
    
    def __init__(self, user, thread=None, callback=None):
        """
        Initialize business tool for a specific user.
        
        Args:
            user: Django User instance (business owner)
            thread: Optional ConversationThread instance for cart/appointment tracking
            callback: Optional callback function to track tool usage
        """
        self.user = user
        self.thread = thread
        self.callback = callback
        
        # Get user's business profile
        try:
            self.business = user.business_profile
            self.business_id = str(self.business.id)
            self.business_service = BusinessService(self.business_id)
        except:
            self.business = None
            self.business_id = None
            self.business_service = None
        
        logger.info(f"Initialized BusinessTool for user: {user.username}, business: {self.business.name if self.business else 'None'}, thread: {thread}")
    
    def _validate_and_convert_id(self, id_value: Union[str, int], model_class, field_name: str = "id") -> Optional[int]:
        """
        Validate and convert ID values to proper format for Django models.
        
        Args:
            id_value: The ID value to validate (can be string, int, or name)
            model_class: The Django model class to validate against
            field_name: The field name to search by (default: 'id')
            
        Returns:
            Valid integer ID or None if not found
        """
        if not id_value:
            return None
            
        # If it's already an integer, validate it exists
        if isinstance(id_value, int):
            try:
                if model_class == ProductVariant:
                    # ProductVariant doesn't have business_id, filter through product
                    model_class.objects.get(**{field_name: id_value}, product__business_id=self.business_id)
                else:
                    model_class.objects.get(**{field_name: id_value}, business_id=self.business_id)
                return id_value
            except model_class.DoesNotExist:
                return None
        
        # Convert string to integer if possible
        if isinstance(id_value, str):
            # Try to convert to integer first
            try:
                int_id = int(id_value)
                if model_class == ProductVariant:
                    # ProductVariant doesn't have business_id, filter through product
                    model_class.objects.get(**{field_name: int_id}, product__business_id=self.business_id)
                else:
                    model_class.objects.get(**{field_name: int_id}, business_id=self.business_id)
                return int_id
            except (ValueError, model_class.DoesNotExist):
                pass
            
            # If it looks like a MongoDB ObjectId, try to find by name instead
            if re.match(r'^[a-f0-9]{24}$', id_value):
                logger.warning(f"MongoDB-style ObjectId detected: {id_value}. Searching by name instead.")
                return None
            
            # Try to find by name (for products/services)
            if field_name == "id" and hasattr(model_class, 'name'):
                try:
                    obj = model_class.objects.get(name__icontains=id_value, business_id=self.business_id)
                    return obj.id
                except model_class.DoesNotExist:
                    pass
                except model_class.MultipleObjectsReturned:
                    # If multiple objects found, return the first one
                    obj = model_class.objects.filter(name__icontains=id_value, business_id=self.business_id).first()
                    if obj:
                        return obj.id
        
        return None
    
    def _find_product_by_name_or_id(self, identifier: Union[str, int]) -> Optional[Product]:
        """
        Find a product by name or ID.
        
        Args:
            identifier: Product name or ID
            
        Returns:
            Product instance or None
        """
        if not identifier:
            return None
            
        # Try by ID first
        product_id = self._validate_and_convert_id(identifier, Product)
        if product_id:
            try:
                return Product.objects.get(id=product_id, business_id=self.business_id)
            except Product.DoesNotExist:
                pass
        
        # Try by name
        if isinstance(identifier, str):
            try:
                return Product.objects.get(name__icontains=identifier, business_id=self.business_id)
            except Product.DoesNotExist:
                pass
            except Product.MultipleObjectsReturned:
                # Return the first match
                return Product.objects.filter(name__icontains=identifier, business_id=self.business_id).first()
        
        return None
    
    def _find_service_by_name_or_id(self, identifier: Union[str, int]) -> Optional[Service]:
        """
        Find a service by name or ID.
        
        Args:
            identifier: Service name or ID
            
        Returns:
            Service instance or None
        """
        if not identifier:
            return None
            
        # Try by ID first
        service_id = self._validate_and_convert_id(identifier, Service)
        if service_id:
            try:
                return Service.objects.get(id=service_id, business_id=self.business_id)
            except Service.DoesNotExist:
                pass
        
        # Try by name
        if isinstance(identifier, str):
            try:
                return Service.objects.get(name__icontains=identifier, business_id=self.business_id)
            except Service.DoesNotExist:
                pass
            except Service.MultipleObjectsReturned:
                # Return the first match
                return Service.objects.filter(name__icontains=identifier, business_id=self.business_id).first()
        
        return None
    
    def search_products(self, query: str, category_id: str = None, limit: int = 10) -> str:
        """
        Search business products. Use when user asks about products, items, or inventory.
        
        This tool searches through the business's product catalog to find items matching
        the user's query. It can search by name, description, SKU, or category.
        
        Args:
            query: The search query to find relevant products
            category_id: Optional category ID to filter by specific category
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            String containing formatted product information
        """
        try:
            logger.info(f"Business Tool - Product search called with query: {query}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for product search."
            
            # Search products
            products = self.business_service.search_products(query, category_id, limit)
            
            if not products:
                return f"No products found matching '{query}'. Try different keywords or browse our categories."
            
            # Format results for LLM consumption
            result_parts = [f"Found {len(products)} products matching '{query}':\n"]
            
            for i, product in enumerate(products, 1):
                stock_info = ""
                if product.get('stock_status'):
                    stock_info = f" ({product['stock_status']})"
                
                price_info = f"{self.business.get_currency_symbol()}{product['price']}"
                if product.get('variants'):
                    price_info += f" (variants available)"
                
                result_parts.append(
                    f"{i}. **{product['name']}** - {price_info}{stock_info}\n"
                    f"   Category: {product['category']}\n"
                    f"   Description: {product['description']}\n"
                )
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Business product search completed: {len(products)} results found")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in business product search: {e}")
            return f"Error searching products: {str(e)}"
    
    def search_services(self, query: str, category_id: str = None, limit: int = 10) -> str:
        """
        Search business services. Use when user asks about services or offerings.
        
        This tool searches through the business's service catalog to find services
        matching the user's query. It can search by name, description, or category.
        
        Args:
            query: The search query to find relevant services
            category_id: Optional category ID to filter by specific category
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            String containing formatted service information
        """
        try:
            logger.info(f"Business Tool - Service search called with query: {query}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for service search."
            
            # Search services
            services = self.business_service.search_services(query, category_id, limit)
            
            if not services:
                return f"No services found matching '{query}'. Try different keywords or browse our service categories."
            
            # Format results for LLM consumption
            result_parts = [f"Found {len(services)} services matching '{query}':\n"]
            
            for i, service in enumerate(services, 1):
                duration_info = ""
                if service.get('duration'):
                    duration_info = f" ({service['duration']})"
                
                appointment_info = ""
                if service.get('requires_appointment'):
                    appointment_info = " [Appointment Required]"
                
                online_info = ""
                if service.get('is_online'):
                    online_info = " [Available Online]"
                
                result_parts.append(
                    f"{i}. **{service['name']}** - {self.business.get_currency_symbol()}{service['price']} ({service['price_type']}){duration_info}{appointment_info}{online_info}\n"
                    f"   Category: {service['category']}\n"
                    f"   Description: {service['description']}\n"
                )
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Business service search completed: {len(services)} results found")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in business service search: {e}")
            return f"Error searching services: {str(e)}"
    
    def get_business_info(self) -> str:
        """
        Get business profile information including contact details and hours.
        
        Use this tool when the user asks about business information, contact details,
        or general business information.
        
        Returns:
            String containing comprehensive business information
        """
        try:
            logger.info("Business Tool - Business info called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available."
            
            # Get business information
            business_info = self.business_service.get_business_info()
            
            if not business_info:
                return "Business information not available."
            
            # Format business information for LLM consumption
            result_parts = [f"**{business_info['name']}** ({business_info['business_type']})\n"]
            
            if business_info.get('description'):
                result_parts.append(f"Description: {business_info['description']}\n")
            
            # Contact information
            contact = business_info.get('contact', {})
            if any(contact.values()):
                result_parts.append("**Contact Information:**")
                if contact.get('phone'):
                    result_parts.append(f"- Phone: {contact['phone']}")
                if contact.get('email'):
                    result_parts.append(f"- Email: {contact['email']}")
                if contact.get('website'):
                    result_parts.append(f"- Website: {contact['website']}")
                if contact.get('whatsapp'):
                    result_parts.append(f"- WhatsApp: {contact['whatsapp']}")
                result_parts.append("")
            
            # Business hours
            hours = business_info.get('business_hours', {})
            if hours:
                result_parts.append("**Business Hours:**")
                for day, hours_info in hours.items():
                    result_parts.append(f"- {day}: {hours_info}")
                result_parts.append("")
            
            # Locations
            locations = business_info.get('locations', [])
            if locations:
                result_parts.append("**Locations:**")
                for location in locations:
                    result_parts.append(f"- {location['name']}: {location['address']}")
                result_parts.append("")
            
            formatted_results = "\n".join(result_parts)
            logger.info("Business info retrieval completed")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting business info: {e}")
            return f"Error retrieving business information: {str(e)}"
    
    def check_business_hours(self) -> str:
        """
        Check if business is currently open and get operating hours.
        
        Use this tool when the user asks about business hours, whether the business
        is open, or when they can visit/contact the business.
        
        Returns:
            String containing current business status and hours
        """
        try:
            logger.info("Business Tool - Business hours check called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for hours check."
            
            # Check if business is open
            is_open, hours_message = self.business_service.is_business_open()
            
            # Get business info for hours details
            business_info = self.business_service.get_business_info()
            hours = business_info.get('business_hours', {})
            
            # Format response
            status_emoji = "🟢" if is_open else "🔴"
            status_text = "OPEN" if is_open else "CLOSED"
            
            result_parts = [
                f"{status_emoji} **Business Status: {status_text}**",
                f"Status: {hours_message}",
                ""
            ]
            
            if hours:
                result_parts.append("**Operating Hours:**")
                for day, hours_info in hours.items():
                    result_parts.append(f"- {day}: {hours_info}")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Business hours check completed: {status_text}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error checking business hours: {e}")
            return f"Error checking business hours: {str(e)}"
    
    def check_appointment_availability(self, service_identifier: str, date: str = None) -> str:
        """
        Check available appointment slots for a service using dynamic scheduling.
        
        Use this tool when the user wants to book appointments, check availability,
        or see available time slots for a specific service.
        
        Args:
            service_identifier: The ID or name of the service to check availability for
            date: Optional date to check availability for (YYYY-MM-DD format)
            
        Returns:
            String containing available appointment slots
        """
        try:
            logger.info(f"Business Tool - Appointment availability called for service: {service_identifier}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for appointment booking."
            
            # Find service by name or ID
            service = self._find_service_by_name_or_id(service_identifier)
            if not service:
                return f"Service '{service_identifier}' not found. Please check the service name or ID."
            
            # Convert date string to date object if provided
            date_obj = None
            if date:
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                except ValueError:
                    return "Invalid date format. Please use YYYY-MM-DD format."
            
            # Get available time slots using dynamic scheduling
            time_slots = self.business_service.get_available_time_slots(str(service.id), date_obj)
            
            if not time_slots:
                if date_obj:
                    return f"No available appointments found for {service.name} on {date}. Please try a different date or contact us directly."
                else:
                    return f"No available appointments found for {service.name}. Please contact us directly for availability."
            
            # Format time slots
            result_parts = [f"**Available Time Slots for {service.name}:**\n"]
            
            if date_obj:
                result_parts.append(f"**Date: {date_obj.strftime('%A, %B %d, %Y')}**\n")
            else:
                result_parts.append(f"**Date: {time_slots[0]['date']}**\n")
            
            # Group slots by hour for better readability
            slots_by_hour = {}
            for slot in time_slots:
                hour = slot['start_time'].split(':')[0]
                if hour not in slots_by_hour:
                    slots_by_hour[hour] = []
                slots_by_hour[hour].append(slot)
            
            for hour, slots in sorted(slots_by_hour.items()):
                result_parts.append(f"**{hour}:00 - {int(hour)+1}:00:**")
                for slot in slots:
                    duration_text = f" ({slot['duration_minutes']} min)" if slot.get('duration_minutes') else ""
                    result_parts.append(
                        f"- {slot['start_time']} - {slot['end_time']}{duration_text}"
                    )
                result_parts.append("")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Appointment availability check completed: {len(time_slots)} slots found")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error checking appointment availability: {e}")
            return f"Error checking appointment availability: {str(e)}"
    
    def get_featured_items(self, item_type: str = 'both') -> str:
        """
        Get featured products and services.
        
        Use this tool when the user asks about featured items, recommendations,
        or what's popular/special at the business.
        
        Args:
            item_type: Type of items to get ('products', 'services', or 'both')
            
        Returns:
            String containing featured items information
        """
        try:
            logger.info(f"Business Tool - Featured items called for type: {item_type}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for featured items."
            
            # Get featured items
            featured = self.business_service.get_featured_items(item_type)
            
            if not featured or (not featured.get('products') and not featured.get('services')):
                return "No featured items available at this time."
            
            result_parts = ["**Featured Items:**\n"]
            
            # Featured products
            if featured.get('products'):
                result_parts.append("**Featured Products:**")
                for product in featured['products']:
                    result_parts.append(
                        f"- **{product['name']}** - {self.business.get_currency_symbol()}{product['price']} "
                        f"({product['category']})"
                    )
                result_parts.append("")
            
            # Featured services
            if featured.get('services'):
                result_parts.append("**Featured Services:**")
                for service in featured['services']:
                    result_parts.append(
                        f"- **{service['name']}** - {self.business.get_currency_symbol()}{service['price']} "
                        f"({service['category']})"
                    )
                result_parts.append("")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Featured items retrieval completed: {len(featured.get('products', []))} products, {len(featured.get('services', []))} services")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting featured items: {e}")
            return f"Error retrieving featured items: {str(e)}"
    
    def get_business_summary(self) -> str:
        """
        Get a comprehensive business summary including stats and overview.
        
        Use this tool when the user asks for a business overview, summary,
        or general information about the business.
        
        Returns:
            String containing business summary
        """
        try:
            logger.info("Business Tool - Business summary called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for summary."
            
            # Get business summary
            summary = self.business_service.get_business_summary()
            
            if not summary:
                return "Business summary not available."
            
            # Format summary
            result_parts = [
                f"**{summary['name']}** ({summary['type']})",
                ""
            ]
            
            # Business status
            status_emoji = "🟢" if summary.get('is_open') else "🔴"
            result_parts.append(f"{status_emoji} Status: {summary.get('hours_message', 'Unknown')}")
            result_parts.append("")
            
            # Stats
            stats = summary.get('stats', {})
            if stats:
                result_parts.append("**Business Overview:**")
                result_parts.append(f"- Products: {stats.get('products', 0)}")
                result_parts.append(f"- Services: {stats.get('services', 0)}")
                result_parts.append(f"- Categories: {stats.get('categories', 0)}")
                result_parts.append("")
            
            # Contact info
            contact = summary.get('contact', {})
            if contact:
                result_parts.append("**Contact Information:**")
                if contact.get('phone'):
                    result_parts.append(f"- Phone: {contact['phone']}")
                if contact.get('whatsapp'):
                    result_parts.append(f"- WhatsApp: {contact['whatsapp']}")
            
            formatted_results = "\n".join(result_parts)
            logger.info("Business summary retrieval completed")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting business summary: {e}")
            return f"Error retrieving business summary: {str(e)}"
    
    def list_available_products(self, limit: int = 20) -> str:
        """
        List all available products with their IDs and names for the agent's reference.
        
        Use this tool when the user asks about available products or when you need to
        see what products are available before adding to cart.
        
        Args:
            limit: Maximum number of products to list (default: 20)
            
        Returns:
            String containing formatted list of available products
        """
        try:
            logger.info("Business Tool - List available products called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for product listing."
            
            # Get all active products
            products = Product.objects.filter(
                business_id=self.business_id,
                is_active=True
            ).select_related('category')[:limit]
            
            if not products:
                return "No products are currently available."
            
            # Format product list
            result_parts = [f"**Available Products ({len(products)}):**\n"]
            
            for i, product in enumerate(products, 1):
                stock_info = ""
                if product.track_inventory:
                    if product.quantity <= 0:
                        stock_info = " (Out of Stock)"
                    elif product.is_low_stock:
                        stock_info = f" (Low Stock: {product.quantity} left)"
                    else:
                        stock_info = f" (In Stock: {product.quantity})"
                
                result_parts.append(
                    f"{i}. **{product.name}** (ID: {product.id})\n"
                    f"   Price: {self.business.get_currency_symbol()}{product.price:.2f}\n"
                    f"   Category: {product.category.name}{stock_info}\n"
                )
            
            result_parts.append("\n💡 **Tip:** You can add products to cart using either the product name or ID.")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Available products listed: {len(products)} products")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error listing available products: {e}")
            return f"Error listing available products: {str(e)}"
    
    def list_available_services(self, limit: int = 20) -> str:
        """
        List all available services with their IDs and names for the agent's reference.
        
        Use this tool when the user asks about available services or when you need to
        see what services are available before booking appointments.
        
        Args:
            limit: Maximum number of services to list (default: 20)
            
        Returns:
            String containing formatted list of available services
        """
        try:
            logger.info("Business Tool - List available services called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service:
                return "No business context available for service listing."
            
            # Get all active services
            services = Service.objects.filter(
                business_id=self.business_id,
                is_active=True
            ).select_related('category')[:limit]
            
            if not services:
                return "No services are currently available."
            
            # Format service list
            result_parts = [f"**Available Services ({len(services)}):**\n"]
            
            for i, service in enumerate(services, 1):
                appointment_info = " (Appointment Required)" if service.is_appointment_required else ""
                online_info = " (Available Online)" if service.is_online_service else ""
                duration_info = f" ({service.get_duration_display()})" if service.duration_minutes else ""
                
                result_parts.append(
                    f"{i}. **{service.name}** (ID: {service.id})\n"
                    f"   Price: {self.business.get_currency_symbol()}{service.price:.2f} ({service.get_price_type_display()}){duration_info}\n"
                    f"   Category: {service.category.name}{appointment_info}{online_info}\n"
                )
            
            result_parts.append("\n💡 **Tip:** You can book appointments using either the service name or ID.")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Available services listed: {len(services)} services")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error listing available services: {e}")
            return f"Error listing available services: {str(e)}"
    
    def add_to_cart(self, product_identifier: str, quantity: int = 1, variant_id: str = None) -> str:
        """
        Add a product to the customer's cart.
        
        Use this tool when the user wants to add items to their cart or purchase products.
        
        Args:
            product_identifier: The ID or name of the product to add
            quantity: Number of items to add (default: 1)
            variant_id: Optional product variant ID
            
        Returns:
            String containing cart status and confirmation
        """
        try:
            logger.info(f"Business Tool - Add to cart called for product: {product_identifier}, quantity: {quantity}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service or not self.thread:
                return "Cart functionality requires business context and conversation thread."
            
            # Find product by name or ID
            product = self._find_product_by_name_or_id(product_identifier)
            if not product:
                return f"Product '{product_identifier}' not found. Please check the product name or ID."
            
            # Get or create cart - scoped to business user and customer
            cart, created = Cart.objects.get_or_create(
                thread=self.thread,
                business_id=self.business_id,
                defaults={
                    'status': 'active'
                }
            )
            
            # Get variant if specified
            variant = None
            if variant_id:
                try:
                    variant_id_int = self._validate_and_convert_id(variant_id, ProductVariant)
                    if variant_id_int:
                        variant = product.variants.get(id=variant_id_int)
                    else:
                        return f"Product variant '{variant_id}' not found."
                except ProductVariant.DoesNotExist:
                    return f"Product variant '{variant_id}' not found."
            
            # Check stock availability
            if product.track_inventory and product.quantity < quantity:
                return f"Insufficient stock. Only {product.quantity} items available."
            
            # Get current price
            current_price = variant.final_price if variant else product.price
            
            # Add or update cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={
                    'quantity': quantity,
                    'unit_price': current_price
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.unit_price = current_price  # Update to current price
                cart_item.save()
            
            # Update cart
            cart.updated_at = cart.updated_at
            cart.save()
            
            # Format response
            variant_info = f" ({variant.name})" if variant else ""
            result = f"✅ Added {quantity}x {product.name}{variant_info} to your cart.\n"
            result += f"**Cart Summary:**\n"
            result += f"- Total Items: {cart.total_items}\n"
            result += f"- Total Amount: {self.business.get_currency_symbol()}{cart.total_amount:.2f}\n"
            
            if cart.notes:
                result += f"- Notes: {cart.notes}\n"
            
            # Add call reachability note
            result += "\n📱 **Note:** We'll use your WhatsApp number for order confirmations. Please ensure this number is reachable by phone call for delivery updates."
            
            logger.info(f"Product added to cart successfully: {product.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return f"Error adding item to cart: {str(e)}"
    
    def get_cart_contents(self) -> str:
        """
        Get the contents of the customer's cart.
        
        Use this tool when the user asks about their cart, wants to review items, or check cart status.
        
        Returns:
            String containing detailed cart information
        """
        try:
            logger.info("Business Tool - Get cart contents called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.thread:
                return "Cart functionality requires conversation thread context."
            
            # Get cart - scoped to business user and customer
            try:
                cart = Cart.objects.get(thread=self.thread, business_id=self.business_id)
            except Cart.DoesNotExist:
                return "Your cart is empty. Add some products to get started!"
            
            if cart.is_empty:
                return "Your cart is empty. Browse our products and add items you'd like to purchase."
            
            # Format cart contents
            result_parts = [f"🛒 **Your Cart ({cart.status.title()})**\n"]
            
            # Customer info
            customer_info = cart.get_customer_info()
            if customer_info != "Anonymous":
                result_parts.append(f"**Customer:** {customer_info}\n")
            
            # Cart items
            result_parts.append("**Items in Cart:**\n")
            for item in cart.items.all():
                variant_info = f" - {item.variant.name}" if item.variant else ""
                result_parts.append(
                    f"- {item.quantity}x {item.product.name}{variant_info}\n"
                    f"  Price: {self.business.get_currency_symbol()}{item.unit_price:.2f} each | Total: {self.business.get_currency_symbol()}{item.total_price:.2f}\n"
                )
            
            # Cart summary
            result_parts.append(f"\n**Cart Summary:**")
            result_parts.append(f"- Total Items: {cart.total_items}")
            result_parts.append(f"- Total Amount: {self.business.get_currency_symbol()}{cart.total_amount:.2f}")
            
            if cart.notes:
                result_parts.append(f"- Special Instructions: {cart.notes}")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Cart contents retrieved: {cart.total_items} items, {self.business.get_currency_symbol()}{cart.total_amount}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting cart contents: {e}")
            return f"Error retrieving cart contents: {str(e)}"
    
    def remove_from_cart(self, product_identifier: str, quantity: int = None, variant_id: str = None) -> str:
        """
        Remove items from the customer's cart.
        
        Use this tool when the user wants to remove items from their cart.
        
        Args:
            product_identifier: The ID or name of the product to remove
            quantity: Number of items to remove (if None, removes all)
            variant_id: Optional product variant ID
            
        Returns:
            String containing removal confirmation
        """
        try:
            logger.info(f"Business Tool - Remove from cart called for product: {product_identifier}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.thread:
                return "Cart functionality requires conversation thread context."
            
            # Get cart - scoped to business user and customer
            try:
                cart = Cart.objects.get(thread=self.thread, business_id=self.business_id)
            except Cart.DoesNotExist:
                return "Your cart is empty."
            
            # Find product by name or ID
            product = self._find_product_by_name_or_id(product_identifier)
            if not product:
                return f"Product '{product_identifier}' not found. Please check the product name or ID."
            
            # Get variant if specified
            variant = None
            if variant_id:
                try:
                    variant = product.variants.get(id=variant_id)
                except:
                    return f"Product variant with ID {variant_id} not found."
            
            # Get cart item
            try:
                cart_item = CartItem.objects.get(cart=cart, product=product, variant=variant)
            except CartItem.DoesNotExist:
                return f"{product.name} is not in your cart."
            
            # Remove items
            if quantity is None or quantity >= cart_item.quantity:
                # Remove all items
                product_name = cart_item.product_display_name
                cart_item.delete()
                result = f"✅ Removed all {product_name} from your cart."
            else:
                # Remove partial quantity
                cart_item.quantity -= quantity
                cart_item.save()
                result = f"✅ Removed {quantity}x {cart_item.product_display_name} from your cart."
            
            # Update cart
            cart.updated_at = cart.updated_at
            cart.save()
            
            # Add cart summary
            if cart.is_empty:
                result += "\nYour cart is now empty."
            else:
                result += f"\n**Updated Cart Summary:**\n"
                result += f"- Total Items: {cart.total_items}\n"
                result += f"- Total Amount: {self.business.get_currency_symbol()}{cart.total_amount:.2f}"
            
            logger.info(f"Product removed from cart: {product.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error removing from cart: {e}")
            return f"Error removing item from cart: {str(e)}"
    
    def book_appointment(self, service_identifier: str, customer_name: str, booking_date: str, booking_time: str, 
                        customer_phone: str = None, customer_email: str = None, notes: str = None) -> str:
        """
        Book an appointment for a service.
        
        Use this tool when the user wants to book an appointment or schedule a service.
        
        Args:
            service_identifier: The ID or name of the service to book
            customer_name: Customer's full name
            customer_phone: Customer's phone number (optional - will use WhatsApp number if not provided)
            booking_date: Date in YYYY-MM-DD format
            booking_time: Time in HH:MM format
            customer_email: Customer's email address (optional)
            notes: Special requests or notes (optional)
            
        Returns:
            String containing booking confirmation
        """
        try:
            logger.info(f"Business Tool - Book appointment called for service: {service_identifier}")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.business_service or not self.thread:
                return "Appointment booking requires business context and conversation thread."
            
            # Use customer's WhatsApp number if phone not provided
            if not customer_phone:
                customer_phone = self.thread.remote_jid
                # Extract phone number from WhatsApp JID (remove @s.whatsapp.net suffix)
                if '@' in customer_phone:
                    customer_phone = customer_phone.split('@')[0]
                phone_note = f" (using your WhatsApp number: {customer_phone})"
            else:
                phone_note = ""
            
            # Find service by name or ID
            service = self._find_service_by_name_or_id(service_identifier)
            if not service:
                return f"Service '{service_identifier}' not found. Please check the service name or ID."
            
            # Parse date and time
            from datetime import datetime, date, time
            try:
                booking_date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
                booking_time_obj = datetime.strptime(booking_time, '%H:%M').time()
            except ValueError:
                return "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time."
            
            # Check if service requires appointment
            if not service.is_appointment_required:
                return f"{service.name} does not require an appointment. Please contact us directly."
            
            # Validate the requested time slot using dynamic scheduling
            available_slots = self.business_service.get_available_time_slots(str(service.id), booking_date_obj)
            
            # Check if the requested time slot is available
            requested_slot_available = False
            for slot in available_slots:
                if slot['start_time'] == booking_time:
                    requested_slot_available = True
                    break
            
            if not requested_slot_available:
                return f"The requested time slot {booking_time} is not available for {booking_date}. Please check available times or choose a different slot."
            
            # Calculate total price
            total_price = service.price
            if service.price_type == 'hourly':
                # Assume 1 hour duration for hourly services
                total_price = service.price
            elif service.price_type == 'per_person':
                # Assume 1 person for per_person services
                total_price = service.price
            
            # Create appointment booking without requiring AppointmentSlot
            booking = AppointmentBooking.objects.create(
                thread=self.thread,
                business_id=self.business_id,
                service=service,
                appointment_slot=None,  # No longer required with dynamic scheduling
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                booking_date=booking_date_obj,
                booking_time=booking_time_obj,
                duration_minutes=service.duration_minutes or 60,
                total_price=total_price,
                notes=notes,
                status='pending'
            )
            
            # Format confirmation
            result_parts = [
                f"✅ **Appointment Booked Successfully!**\n",
                f"**Booking Details:**",
                f"- Service: {service.name}",
                f"- Date: {booking_date}",
                f"- Time: {booking_time}",
                f"- Duration: {service.duration_minutes or 60} minutes",
                f"- Price: {self.business.get_currency_symbol()}{total_price:.2f}",
                f"- Status: Pending Confirmation",
                "",
                f"**Customer Information:**",
                f"- Name: {customer_name}",
                f"- Phone: {customer_phone}{phone_note}",
            ]
            
            if customer_email:
                result_parts.append(f"- Email: {customer_email}")
            
            if notes:
                result_parts.append(f"- Special Requests: {notes}")
            
            result_parts.extend([
                "",
                "📞 We'll contact you shortly to confirm your appointment.",
                f"Booking ID: {booking.id}"
            ])
            
            # Add call reachability note if using WhatsApp number
            if not customer_phone or customer_phone == self.thread.remote_jid:
                result_parts.append("")
                result_parts.append("📱 **Important:** We'll use your WhatsApp number for confirmation. Please ensure this number is reachable by phone call for appointment confirmations.")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Appointment booked successfully: {service.name} for {customer_name}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return f"Error booking appointment: {str(e)}"
    
    def get_appointment_bookings(self) -> str:
        """
        Get all appointment bookings for the current conversation thread.
        
        Use this tool when the user asks about their appointments or booking history.
        
        Returns:
            String containing appointment booking information
        """
        try:
            logger.info("Business Tool - Get appointment bookings called")
            
            # Set flag if callback provided
            if self.callback:
                self.callback('business_tool_used', True)
            
            if not self.thread:
                return "Appointment functionality requires conversation thread context."
            
            # Get bookings - scoped to business user and customer
            bookings = AppointmentBooking.objects.filter(
                thread=self.thread,
                business_id=self.business_id
            ).order_by('booking_date', 'booking_time')
            
            if not bookings.exists():
                return "You have no appointment bookings. Use the book_appointment tool to schedule an appointment."
            
            # Format bookings
            result_parts = [f"📅 **Your Appointment Bookings**\n"]
            
            for booking in bookings:
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'completed': '✅',
                    'cancelled': '❌',
                    'no_show': '❌'
                }.get(booking.status, '❓')
                
                result_parts.append(
                    f"{status_emoji} **{booking.service.name}**\n"
                    f"- Date: {booking.booking_date}\n"
                    f"- Time: {booking.booking_time}\n"
                    f"- Duration: {booking.duration_minutes} minutes\n"
                    f"- Price: {self.business.get_currency_symbol()}{booking.total_price:.2f}\n"
                    f"- Status: {booking.status.title()}\n"
                    f"- Customer: {booking.customer_name} ({booking.customer_phone})\n"
                )
                
                if booking.notes:
                    result_parts.append(f"- Notes: {booking.notes}\n")
                
                result_parts.append("")
            
            formatted_results = "\n".join(result_parts)
            logger.info(f"Appointment bookings retrieved: {bookings.count()} bookings")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting appointment bookings: {e}")
            return f"Error retrieving appointment bookings: {str(e)}"
    
    def get_tools(self):
        """Return list of LangChain tool instances."""
        return [
            tool(self.search_products),
            tool(self.search_services),
            tool(self.get_business_info),
            tool(self.check_business_hours),
            tool(self.check_appointment_availability),
            tool(self.get_featured_items),
            tool(self.get_business_summary),
            tool(self.list_available_products),
            tool(self.list_available_services),
            tool(self.add_to_cart),
            tool(self.get_cart_contents),
            tool(self.remove_from_cart),
            tool(self.book_appointment),
            tool(self.get_appointment_bookings),
        ]
